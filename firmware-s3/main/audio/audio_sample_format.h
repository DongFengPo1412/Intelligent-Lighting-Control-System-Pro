#pragma once
#include <cstddef>
#include <cstdint>
#include <climits>
#include <algorithm>

namespace audio_pcm {
constexpr unsigned kI2sBytesPerSample = sizeof(int32_t); // Mid: mono, 32-bit left slot.
inline uint32_t VolumeFactor(int percent) {
    const double ratio = double(percent) / 100.0;
    return uint32_t(ratio * ratio * 65536.0);
}
inline void PackMono(const int16_t* source, size_t count, uint32_t factor, int32_t* output) {
    for (size_t i = 0; i < count; ++i) {
        const int64_t sample = int64_t(source[i]) * factor;
        output[i] = sample > INT32_MAX ? INT32_MAX : sample < INT32_MIN ? INT32_MIN : int32_t(sample);
    }
}

// 2:3 Continuous Linear Resampler with Uniform Sampling Intervals
// Converts 16kHz mono PCM16 to 24kHz mono 32-bit I2S output with volume scaling.
// Ratio 16k:24k = 2:3. Every 2 input samples map to exactly 3 output samples:
//   y_0 = x_0
//   y_1 = (1/3)*x_0 + (2/3)*x_1
//   y_2 = (2/3)*x_1 + (1/3)*x_2
// Uniform output time interval: dt = 2/3 of input sample period.
// Maintains cross-chunk phase, history and pending outputs invariant of chunk slicing.
class Resampler16kTo24k {
public:
    int16_t last_sample_ = 0;
    bool has_history_ = false;
    uint8_t phase_ = 0; // 0: even sample next, 1: odd sample next

    void Reset() {
        last_sample_ = 0;
        has_history_ = false;
        phase_ = 0;
    }

    size_t Process(const int16_t* source, size_t count_16k, uint32_t factor, int32_t* output, bool flush = false) {
        if (!output) return 0;
        size_t out_idx = 0;

        auto scale = [factor](int64_t s) -> int32_t {
            int64_t scaled = s * factor;
            return scaled > INT32_MAX ? INT32_MAX : scaled < INT32_MIN ? INT32_MIN : int32_t(scaled);
        };

        if (source && count_16k > 0) {
            for (size_t i = 0; i < count_16k; ++i) {
                int64_t curr = source[i];
                if (!has_history_) {
                    // First sample of stream: y_0 = x_0
                    output[out_idx++] = scale(curr);
                    last_sample_ = source[i];
                    has_history_ = true;
                    phase_ = 0;
                } else if (phase_ == 0) {
                    // Previous was even (x_{2k}), current is odd (x_{2k+1}):
                    // y_1 = (x_{2k} + 2*x_{2k+1} + 1) / 3
                    int64_t y1 = (last_sample_ + 2 * curr + 1) / 3;
                    output[out_idx++] = scale(y1);
                    last_sample_ = source[i];
                    phase_ = 1;
                } else {
                    // Previous was odd (x_{2k+1}), current is even (x_{2k+2}):
                    // y_2 = (2*x_{2k+1} + x_{2k+2} + 1) / 3
                    // y_3 = x_{2k+2}
                    int64_t y2 = (2 * last_sample_ + curr + 1) / 3;
                    int64_t y3 = curr;
                    output[out_idx++] = scale(y2);
                    output[out_idx++] = scale(y3);
                    last_sample_ = source[i];
                    phase_ = 0;
                }
            }
        }

        if (flush && has_history_) {
            if (phase_ == 1) {
                // End of stream at odd sample x_{2k+1}: extrapolate end sample as last_sample_
                output[out_idx++] = scale(last_sample_);
            }
            Reset();
        }

        return out_idx;
    }

    size_t Flush(uint32_t factor, int32_t* output) {
        return Process(nullptr, 0, factor, output, true);
    }
};

inline size_t PackMono16kTo24k(const int16_t* source, size_t count_16k, uint32_t factor, int32_t* output, bool flush = false) {
    static Resampler16kTo24k s_resampler;
    return s_resampler.Process(source, count_16k, factor, output, flush);
}
}
