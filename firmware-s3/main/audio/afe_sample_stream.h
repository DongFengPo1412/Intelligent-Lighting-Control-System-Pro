#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

namespace audio_afe {

/**
 * Manages AFE cross-chunk input feeding, fetch buffering,
 * timeline alignment, bounded warmup, and duplicate output discard to preserve
 * strict temporal sample ordering without skips or duplicate emissions.
 */
class AfeSampleStream {
public:
    enum class WarmupMode {
        SilencePlaceholder, // Default: zero-filled silence during warmup to preserve cadence without duplicating audio
        RawPassthrough      // Pass raw samples immediately during warmup
    };

    static constexpr size_t kDefaultMaxWarmupBlocks = 5; // ~75ms at 15ms/240 samples per block
    static constexpr size_t kMaxRawHistorySamples = 4800; // ~300ms at 16kHz

    void Reset() {
        in_buf_.clear();
        raw_history_.clear();
        out_buf_.clear();
        raw_history_start_idx_ = 0;
        total_raw_pushed_ = 0;
        total_afe_fetched_ = 0;
        emitted_source_samples_ = 0;
        silence_warmup_samples_ = 0;
        warmup_blocks_emitted_ = 0;
        warmed_up_ = false;
        warmup_timed_out_ = false;
        degraded_to_raw_ = false;
        generation_++;
    }

    void SetWarmupMode(WarmupMode mode) { warmup_mode_ = mode; }
    WarmupMode GetWarmupMode() const { return warmup_mode_; }
    void SetMaxWarmupBlocks(size_t max_blocks) { max_warmup_blocks_ = max_blocks; }
    size_t GetMaxWarmupBlocks() const { return max_warmup_blocks_; }

    size_t InBufferSize() const { return in_buf_.size(); }
    size_t OutBufferSize() const { return out_buf_.size(); }
    size_t DiscardPending() const {
        if (emitted_source_samples_ > total_afe_fetched_) {
            return emitted_source_samples_ - total_afe_fetched_;
        }
        return 0;
    }
    bool IsWarmedUp() const { return warmed_up_; }
    bool IsWarmupTimedOut() const { return warmup_timed_out_; }
    bool IsDegradedToRaw() const { return degraded_to_raw_; }
    size_t WarmupBlocksEmitted() const { return warmup_blocks_emitted_; }
    size_t EmittedSourceSamples() const { return emitted_source_samples_; }
    size_t TotalRawPushed() const { return total_raw_pushed_; }
    size_t TotalAfeFetched() const { return total_afe_fetched_; }
    size_t PrimedRawSamples() const { return DiscardPending(); }
    uint32_t Generation() const { return generation_; }

    /**
     * Appends newly read raw samples (from I2S) into the input accumulation buffer
     * and into the raw timeline history buffer.
     */
    void PushInput(const int16_t* samples, size_t count) {
        if (!samples || count == 0) return;
        in_buf_.insert(in_buf_.end(), samples, samples + count);
        raw_history_.insert(raw_history_.end(), samples, samples + count);
        total_raw_pushed_ += count;
        PruneRawHistory();
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
     * Consumes fetched samples from AFE.
     * Maps them along the timeline:
     * Samples with source timeline index < emitted_source_samples_ correspond to audio
     * intervals that were already emitted (e.g. as raw fallback or early passthrough).
     * Those samples are discarded to prevent duplicate emissions.
     * The remaining samples are enqueued into out_buf_.
     */
    void PushFetched(const int16_t* samples, size_t count) {
        if (!samples || count == 0) return;
        size_t chunk_start = total_afe_fetched_;
        total_afe_fetched_ += count;

        size_t needed_start = emitted_source_samples_;
        if (chunk_start < needed_start) {
            size_t discard = (std::min)(count, needed_start - chunk_start);
            samples += discard;
            count -= discard;
        }

        if (count > 0) {
            out_buf_.insert(out_buf_.end(), samples, samples + count);
        }
    }

    /**
     * Pops `count` samples into `dest_buf`.
     * If out_buf_ has >= count samples, copies them and returns true (filtered steady state).
     * If out_buf_ does not have count samples:
     *   - If not yet warmed up and not timed out:
     *       If warmup_blocks_emitted_ < max_warmup_blocks_:
     *           If SilencePlaceholder: fills dest_buf with zeros (preserves cadence).
     *           If RawPassthrough: fills dest_buf with raw samples starting at emitted_source_samples_.
     *           Returns false.
     *       Else (warmup timed out):
     *           warmup_timed_out_ = true; degraded_to_raw_ = true;
     *   - If already warmed up OR warmup timed out (steady-state underflow / stall):
     *       Fills dest_buf with the exact raw samples corresponding to emitted_source_samples_
     *       from raw_history_ (or fallback_raw if history is unavailable).
     *       Advances emitted_source_samples_ by count on the exact same timeline.
     *       Drops any obsolete partial AFE samples in out_buf_ that overlap the emitted window.
     *       Returns false (degraded/fallback).
     */
    bool Emit(int16_t* dest_buf, const int16_t* fallback_raw, size_t count) {
        if (!dest_buf || count == 0) return false;

        // 1. AFE has sufficient filtered samples: steady-state filtered emission
        if (out_buf_.size() >= count) {
            std::memcpy(dest_buf, out_buf_.data(), count * sizeof(int16_t));
            out_buf_.erase(out_buf_.begin(), out_buf_.begin() + count);
            emitted_source_samples_ += count;
            warmed_up_ = true;
            degraded_to_raw_ = false;
            PruneRawHistory();
            return true;
        }

        // 2. Cold-start warmup phase
        if (!warmed_up_ && !warmup_timed_out_) {
            if (warmup_blocks_emitted_ < max_warmup_blocks_) {
                warmup_blocks_emitted_++;
                if (warmup_mode_ == WarmupMode::SilencePlaceholder) {
                    std::memset(dest_buf, 0, count * sizeof(int16_t));
                    silence_warmup_samples_ += count;
                    return false;
                } else {
                    CopyRawToDest(dest_buf, fallback_raw, count);
                    emitted_source_samples_ += count;
                    out_buf_.clear();
                    PruneRawHistory();
                    return false;
                }
            } else {
                warmup_timed_out_ = true;
                degraded_to_raw_ = true;
            }
        }

        // 3. Steady-state underflow / glitch OR warmup timeout:
        CopyRawToDest(dest_buf, fallback_raw, count);
        emitted_source_samples_ += count;
        out_buf_.clear();
        PruneRawHistory();
        return false;
    }

private:
    void CopyRawToDest(int16_t* dest_buf, const int16_t* fallback_raw, size_t count) {
        if (emitted_source_samples_ >= raw_history_start_idx_) {
            size_t local_idx = emitted_source_samples_ - raw_history_start_idx_;
            if (local_idx + count <= raw_history_.size()) {
                std::memcpy(dest_buf, raw_history_.data() + local_idx, count * sizeof(int16_t));
                return;
            } else if (local_idx < raw_history_.size()) {
                size_t avail = raw_history_.size() - local_idx;
                std::memcpy(dest_buf, raw_history_.data() + local_idx, avail * sizeof(int16_t));
                if (fallback_raw) {
                    std::memcpy(dest_buf + avail, fallback_raw + avail, (count - avail) * sizeof(int16_t));
                } else {
                    std::memset(dest_buf + avail, 0, (count - avail) * sizeof(int16_t));
                }
                return;
            }
        }
        if (fallback_raw) {
            std::memcpy(dest_buf, fallback_raw, count * sizeof(int16_t));
        } else {
            std::memset(dest_buf, 0, count * sizeof(int16_t));
        }
    }

    void PruneRawHistory() {
        size_t safe_keep_from = (std::min)(emitted_source_samples_, total_afe_fetched_);
        if (safe_keep_from > raw_history_start_idx_) {
            size_t to_drop = safe_keep_from - raw_history_start_idx_;
            if (to_drop >= 480) {
                if (to_drop >= raw_history_.size()) {
                    raw_history_start_idx_ += raw_history_.size();
                    raw_history_.clear();
                } else {
                    raw_history_.erase(raw_history_.begin(), raw_history_.begin() + to_drop);
                    raw_history_start_idx_ += to_drop;
                }
            }
        }
        if (raw_history_.size() > kMaxRawHistorySamples) {
            size_t excess = raw_history_.size() - kMaxRawHistorySamples;
            raw_history_.erase(raw_history_.begin(), raw_history_.begin() + excess);
            raw_history_start_idx_ += excess;
        }
    }

    std::vector<int16_t> in_buf_;
    std::vector<int16_t> raw_history_;
    std::vector<int16_t> out_buf_;
    size_t raw_history_start_idx_ = 0;
    size_t total_raw_pushed_ = 0;
    size_t total_afe_fetched_ = 0;
    size_t emitted_source_samples_ = 0;
    size_t silence_warmup_samples_ = 0;
    size_t warmup_blocks_emitted_ = 0;
    size_t max_warmup_blocks_ = kDefaultMaxWarmupBlocks;
    bool warmed_up_ = false;
    bool warmup_timed_out_ = false;
    bool degraded_to_raw_ = false;
    WarmupMode warmup_mode_ = WarmupMode::SilencePlaceholder;
    uint32_t generation_ = 0;
};

} // namespace audio_afe
