#pragma once
#include "arcade_sound.h"
#include <algorithm>
#include <cstddef>

namespace arcade {
enum class AudioWriteState { Ready, Busy, Preempted, Fault };
struct AudioWriteResult {
    unsigned samples;
    AudioWriteState state;
};
inline AudioWriteResult GameWriteFromBytes(unsigned requested, size_t bytes,
                                           AudioWriteState state, unsigned frame_bytes = 8) {
    if ((frame_bytes != 4 && frame_bytes != 8) || bytes / frame_bytes > requested || bytes % frame_bytes)
        return {0, AudioWriteState::Fault};
    return {unsigned(bytes / frame_bytes), state}; // Mono or legacy stereo int32 I2S.
}
// One nonblocking write per Poll. Accepted prefixes are never replayed. Scheduling
// follows the original sample clock, not "write duration + sleep duration".
class GameAudioStream {
  public:
    explicit GameAudioStream(SoundBus &bus) : bus_(bus) {}
    bool Active() const { return active_; }
    unsigned Offset() const { return offset_; }
    template <class Writer> void Poll(uint32_t now, Writer write) {
        if (!active_) {
            if (!bus_.Pop(event_))
                return;
            offset_ = 0;
            start_ = last_progress_ = now;
            active_ = true;
        }
        if (!bus_.Enabled() || !bus_.Volume() || bus_.Generation() != event_.generation) {
            active_ = false;
            return;
        }
        const unsigned total = ToneFor(event_).duration_ms * 16;
        if (uint32_t(now - start_) > ToneFor(event_).duration_ms + 40 ||
            uint32_t(now - last_progress_) > 25) {
            ++bus_.late;
            active_ = false;
            return;
        }
        if (uint32_t(now - start_) * 16 < offset_)
            return;
        int16_t pcm[160];
        unsigned count = std::min(160u, total - offset_);
        for (unsigned i = 0; i < count; ++i)
            pcm[i] = SoundSample(event_, offset_ + i, bus_.Volume());
        auto result = write(pcm, count);
        if (result.samples > count) {
            ++bus_.faults;
            active_ = false;
            return;
        }
        if (result.samples < count)
            ++bus_.short_writes;
        offset_ += result.samples;
        if (result.samples)
            last_progress_ = now;
        if (result.state == AudioWriteState::Preempted) {
            ++bus_.preempted;
            active_ = false;
            return;
        }
        if (result.state == AudioWriteState::Fault) {
            ++bus_.faults;
            active_ = false;
            return;
        }
        if (result.state == AudioWriteState::Busy || !result.samples)
            ++bus_.busy;
        if (offset_ == total) {
            ++bus_.played;
            active_ = false;
        }
    }

  private:
    SoundBus &bus_;
    SoundEvent event_{};
    bool active_ = false;
    uint32_t start_ = 0, last_progress_ = 0;
    unsigned offset_ = 0;
};
} // namespace arcade
