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
        afe_fetched_pos_ = 0;
        emitted_pos_ = 0;
    }

    size_t InBufferSize() const { return in_buf_.size(); }
    size_t OutBufferSize() const { return out_buf_.size(); }
    uint64_t FetchedPosition() const { return afe_fetched_pos_; }
    uint64_t EmittedPosition() const { return emitted_pos_; }
    size_t PrimedRawSamples() const {
        return emitted_pos_ > afe_fetched_pos_ ? static_cast<size_t>(emitted_pos_ - afe_fetched_pos_) : 0;
    }

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
        uint64_t start_pos = afe_fetched_pos_;
        afe_fetched_pos_ += count;
        if (start_pos < emitted_pos_) {
            uint64_t overlap = emitted_pos_ - start_pos;
            size_t discard = static_cast<size_t>((std::min)(static_cast<uint64_t>(count), overlap));
            samples += discard;
            count -= discard;
        }
        if (count > 0) {
            out_buf_.insert(out_buf_.end(), samples, samples + count);
        }
    }

    /**
     * Pops `count` samples into `dest_buf`.
     * If out_buf_ has >= count samples, copies them from out_buf_.
     * If not enough (cold start priming), passes raw `fallback_raw` samples
     * and advances emitted_pos_ so delayed filtered equivalents are discarded later.
     * Partial un-emitted samples in out_buf_ are cleared to avoid duplication.
     * Returns true if samples were taken from AFE filtered output, false if fallback was used.
     */
    bool Emit(int16_t* dest_buf, const int16_t* fallback_raw, size_t count) {
        if (!dest_buf || count == 0) return false;
        if (out_buf_.size() >= count) {
            std::memcpy(dest_buf, out_buf_.data(), count * sizeof(int16_t));
            out_buf_.erase(out_buf_.begin(), out_buf_.begin() + count);
            emitted_pos_ += count;
            return true;
        }
        // Priming fallback: out_buf_ does not yet have a full block of filtered samples.
        // Transparently emit fallback_raw so audio does not underflow.
        if (fallback_raw) {
            std::memcpy(dest_buf, fallback_raw, count * sizeof(int16_t));
        }
        emitted_pos_ += count;
        // Any partial samples in out_buf_ correspond to positions < emitted_pos_,
        // which were just covered by fallback_raw. Clear out_buf_ to avoid duplicate emission.
        out_buf_.clear();
        return false;
    }

private:
    std::vector<int16_t> in_buf_;
    std::vector<int16_t> out_buf_;
    uint64_t afe_fetched_pos_ = 0;
    uint64_t emitted_pos_ = 0;
};

} // namespace audio_afe
