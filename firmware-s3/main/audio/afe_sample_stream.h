#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

namespace audio_afe {

/**
 * Manages AFE cross-chunk input feeding, fetch buffering,
 * cold-start priming fallback, and duplicate output discard to preserve
 * strict temporal sample ordering.
 */
class AfeSampleStream {
public:
    enum class WarmupMode {
        SilencePlaceholder, // Default: zero-filled silence during warmup to preserve cadence without duplicating audio
        RawPassthrough      // Pass raw samples immediately during warmup
    };

    void Reset() {
        in_buf_.clear();
        out_buf_.clear();
        discard_pending_ = 0;
        warmed_up_ = false;
        warmup_blocks_emitted_ = 0;
        generation_++;
    }

    void SetWarmupMode(WarmupMode mode) { warmup_mode_ = mode; }
    WarmupMode GetWarmupMode() const { return warmup_mode_; }

    size_t InBufferSize() const { return in_buf_.size(); }
    size_t OutBufferSize() const { return out_buf_.size(); }
    size_t DiscardPending() const { return discard_pending_; }
    bool IsWarmedUp() const { return warmed_up_; }
    size_t WarmupBlocksEmitted() const { return warmup_blocks_emitted_; }
    size_t PrimedRawSamples() const { return discard_pending_; }
    uint32_t Generation() const { return generation_; }

    /**
     * Appends newly read raw samples (from I2S) into the input accumulation buffer.
     */
    void PushInput(const int16_t* samples, size_t count) {
        if (!samples || count == 0) return;
        in_buf_.insert(in_buf_.end(), samples, samples + count);
    }

    /**
     * Checks if enough samples are ready for AFE feed.
     */
    bool CanFeed(int feed_chunk) const {
        return feed_chunk > 0 && in_buf_.size() >= static_cast<size_t>(feed_chunk);
    }

    /**
     * Retrieves pointer to feed chunk data and pops it from in_buf_.
     */
    const int16_t* FeedChunk(int feed_chunk, std::vector<int16_t>& scratch_chunk) {
        if (!CanFeed(feed_chunk)) return nullptr;
        scratch_chunk.assign(in_buf_.begin(), in_buf_.begin() + feed_chunk);
        in_buf_.erase(in_buf_.begin(), in_buf_.begin() + feed_chunk);
        return scratch_chunk.data();
    }

    /**
     * Consumes fetched samples from AFE. If partial fallback was used, discards
     * the matching delayed AFE output so the same audio interval is not emitted twice,
     * preventing temporal reversal or stuttering.
     */
    void PushFetched(const int16_t* samples, size_t count) {
        if (!samples || count == 0) return;
        if (discard_pending_ > 0) {
            size_t discard = (std::min)(count, discard_pending_);
            samples += discard;
            count -= discard;
            discard_pending_ -= discard;
        }
        if (count > 0) {
            out_buf_.insert(out_buf_.end(), samples, samples + count);
        }
    }

    /**
     * Pops `count` samples into `dest_buf`.
     * If out_buf_ has >= count samples, copies them from out_buf_ and returns true (filtered).
     * If out_buf_ does not yet have count samples:
     *   - If not yet warmed up (!warmed_up_):
     *       If warmup_mode_ == SilencePlaceholder: fills dest_buf with silence (0) to preserve
     *       cadence without prematurely transmitting raw samples that would later be duplicated.
     *       If warmup_mode_ == RawPassthrough: fills dest_buf with fallback_raw.
     *       Tracks warmup_blocks_emitted_++.
     *       Returns false.
     *   - If already warmed up (steady-state underflow / glitch):
     *       Fills dest_buf with fallback_raw so audio does not stall.
     *       Marks discard_pending_ += (count - out_buf_.size()) and clears out_buf_ so matching
     *       delayed AFE samples are dropped when AFE catches up.
     *       Returns false.
     */
    bool Emit(int16_t* dest_buf, const int16_t* fallback_raw, size_t count) {
        if (!dest_buf || count == 0) return false;
        if (out_buf_.size() >= count) {
            std::memcpy(dest_buf, out_buf_.data(), count * sizeof(int16_t));
            out_buf_.erase(out_buf_.begin(), out_buf_.begin() + count);
            warmed_up_ = true;
            return true;
        }

        if (!warmed_up_) {
            // Cold-start warmup phase: AFE algorithmic pipeline delay is filling.
            if (warmup_mode_ == WarmupMode::SilencePlaceholder) {
                std::memset(dest_buf, 0, count * sizeof(int16_t));
            } else {
                if (fallback_raw) {
                    std::memcpy(dest_buf, fallback_raw, count * sizeof(int16_t));
                }
                size_t partial = out_buf_.size();
                discard_pending_ += (count > partial ? count - partial : 0);
                out_buf_.clear();
            }
            warmup_blocks_emitted_++;
            return false;
        }

        // Steady-state underflow / glitch fallback:
        // AFE was running but temporarily ran short of samples.
        // Transparently pass raw samples so audio output does not glitch/freeze.
        if (fallback_raw) {
            std::memcpy(dest_buf, fallback_raw, count * sizeof(int16_t));
        }
        size_t partial = out_buf_.size();
        discard_pending_ += (count > partial ? count - partial : 0);
        out_buf_.clear();
        return false;
    }

private:
    std::vector<int16_t> in_buf_;
    std::vector<int16_t> out_buf_;
    size_t discard_pending_ = 0;
    bool warmed_up_ = false;
    size_t warmup_blocks_emitted_ = 0;
    WarmupMode warmup_mode_ = WarmupMode::SilencePlaceholder;
    uint32_t generation_ = 0;
};

} // namespace audio_afe
