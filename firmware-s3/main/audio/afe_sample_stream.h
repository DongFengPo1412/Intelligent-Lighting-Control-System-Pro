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
    void Reset() {
        in_buf_.clear();
        out_buf_.clear();
        primed_raw_samples_ = 0;
    }

    size_t InBufferSize() const { return in_buf_.size(); }
    size_t OutBufferSize() const { return out_buf_.size(); }
    size_t PrimedRawSamples() const { return primed_raw_samples_; }

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
     * Consumes fetched samples from AFE. If cold-start raw samples were already
     * emitted, discards the matching delayed AFE output so the same audio interval
     * is not emitted twice, preventing temporal reversal or stuttering.
     */
    void PushFetched(const int16_t* samples, size_t count) {
        if (!samples || count == 0) return;
        const int16_t* ptr = samples;
        size_t available = count;
        if (primed_raw_samples_ > 0) {
            size_t discard = (std::min)(primed_raw_samples_, available);
            ptr += discard;
            available -= discard;
            primed_raw_samples_ -= discard;
        }
        if (available > 0) {
            out_buf_.insert(out_buf_.end(), ptr, ptr + available);
        }
    }

    /**
     * Pops `count` samples into `dest_buf`.
     * If out_buf_ has >= count samples, copies them from out_buf_.
     * If not enough (cold start priming), passes raw `fallback_raw` samples
     * and tracks `primed_raw_samples_` so delayed filtered equivalents are discarded later.
     * Returns true if samples were taken from AFE filtered output, false if fallback was used.
     */
    bool Emit(int16_t* dest_buf, const int16_t* fallback_raw, size_t count) {
        if (!dest_buf || count == 0) return false;
        if (out_buf_.size() >= count) {
            std::memcpy(dest_buf, out_buf_.data(), count * sizeof(int16_t));
            out_buf_.erase(out_buf_.begin(), out_buf_.begin() + count);
            return true;
        }
        // Priming fallback
        if (fallback_raw) {
            std::memcpy(dest_buf, fallback_raw, count * sizeof(int16_t));
            primed_raw_samples_ += count;
        }
        return false;
    }

private:
    std::vector<int16_t> in_buf_;
    std::vector<int16_t> out_buf_;
    size_t primed_raw_samples_ = 0;
};

} // namespace audio_afe
