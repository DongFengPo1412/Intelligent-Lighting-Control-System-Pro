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
class Resampler16kTo24k {
public:
    int16_t last_sample_ = 0;
    bool has_history_ = false;

    void Reset() {
        last_sample_ = 0;
        has_history_ = false;
    }

    size_t Process(const int16_t* source, size_t count_16k, uint32_t factor, int32_t* output) {
        if (!source || count_16k == 0 || !output) return 0;
        size_t out_idx = 0;

        auto scale = [factor](int64_t s) -> int32_t {
            int64_t scaled = s * factor;
            return scaled > INT32_MAX ? INT32_MAX : scaled < INT32_MIN ? INT32_MIN : int32_t(scaled);
        };

        size_t i = 0;
        for (; i + 1 < count_16k; i += 2) {
            int64_t x0 = source[i];
            int64_t x1 = source[i + 1];
            int64_t x2 = (i + 2 < count_16k) ? int64_t(source[i + 2]) : x1;

            int64_t y0 = x0;
            int64_t y1 = (x0 + 2 * x1 + 1) / 3;
            int64_t y2 = (2 * x1 + x2 + 1) / 3;

            output[out_idx++] = scale(y0);
            output[out_idx++] = scale(y1);
            output[out_idx++] = scale(y2);
        }

        if (i < count_16k) {
            int64_t x0 = source[i];
            output[out_idx++] = scale(x0);
            last_sample_ = source[i];
            has_history_ = true;
        } else if (count_16k > 0) {
            last_sample_ = source[count_16k - 1];
            has_history_ = true;
        }

        return out_idx;
    }
};

inline size_t PackMono16kTo24k(const int16_t* source, size_t count_16k, uint32_t factor, int32_t* output) {
    static Resampler16kTo24k s_resampler;
    return s_resampler.Process(source, count_16k, factor, output);
}
}
