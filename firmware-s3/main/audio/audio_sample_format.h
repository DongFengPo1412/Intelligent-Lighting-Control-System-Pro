#pragma once
#include <cstddef>
#include <cstdint>
#include <climits>

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
}
