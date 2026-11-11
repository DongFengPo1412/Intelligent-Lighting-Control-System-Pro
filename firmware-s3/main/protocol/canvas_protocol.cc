#include "canvas_protocol.h"
#if !defined(HOST_TEST)
#include "display_manager.h"
#endif
#include <string.h>

#if !defined(ESP_PLATFORM)
#include <stdio.h>
#endif

namespace canvas {

uint16_t CalculateCrc16(const uint8_t* data, size_t len) {
    if (!data || len == 0) return 0;
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; ++b) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}

CanvasAssembler& CanvasAssembler::GetInstance() {
    static CanvasAssembler instance;
    return instance;
}

CanvasAssembler::CanvasAssembler() {
    Reset();
}

void CanvasAssembler::Reset() {
    memset(frame_buffer_, 0, sizeof(frame_buffer_));
    memset(byte_bitmap_, 0, sizeof(byte_bitmap_));
    current_frame_id_ = 0;
    bytes_received_ = 0;
    frame_start_time_ms_ = 0;
    frame_in_progress_ = false;
}

void CanvasAssembler::MarkBytes(uint16_t offset, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        uint16_t idx = offset + (uint16_t)i;
        if (idx < kFrameSizeBytes) {
            uint16_t byte_idx = idx / 8;
            uint8_t bit_mask = 1 << (idx % 8);
            if (!(byte_bitmap_[byte_idx] & bit_mask)) {
                byte_bitmap_[byte_idx] |= bit_mask;
                bytes_received_++;
            }
        }
    }
}

bool CanvasAssembler::IsBitmapFullyCovered() const {
    for (size_t i = 0; i < sizeof(byte_bitmap_); ++i) {
        if (byte_bitmap_[i] != 0xFF) return false;
    }
    return true;
}

bool CanvasAssembler::IsFrameComplete() const {
    return (bytes_received_ >= kFrameSizeBytes) && IsBitmapFullyCovered();
}

void CanvasAssembler::ResetSequence(uint16_t initial_seq) {
    Reset();
    last_committed_frame_id_ = initial_seq;
    has_committed_any_frame_ = false;
}

void CanvasAssembler::CommitFrame(bool auto_mode) {
    DisplayManager& dm = DisplayManager::GetInstance();
    bool manual_active = dm.IsManualOverrideActive();

    // Human user control priority: When manual override is active, Jetson cannot switch mode,
    // take canvas ownership, or overwrite the active canvas buffer.
    if (!manual_active) {
        if (auto_mode && dm.GetMode() != DisplayMode::PIXEL_CANVAS) {
            dm.SetMode(static_cast<uint8_t>(DisplayMode::PIXEL_CANVAS));
        }
        dm.SetCanvasSource(DisplayManager::CanvasSource::JETSON);

        ColorRGB colors[kPixelCount];
        for (size_t i = 0; i < kPixelCount; ++i) {
            size_t b_idx = i * 3;
            colors[i] = ColorRGB(frame_buffer_[b_idx], frame_buffer_[b_idx + 1], frame_buffer_[b_idx + 2]);
        }
        dm.SetCanvasFrame(colors);
    }

    committed_frames_++;
    last_committed_frame_id_ = current_frame_id_;
    has_committed_any_frame_ = true;
    Reset();
}

FeedResult CanvasAssembler::FeedChunk(uint16_t frame_id, uint16_t chunk_idx, uint16_t total_chunks,
                                      uint16_t offset, const uint8_t* data, size_t len,
                                      uint16_t expected_crc, bool commit_now, bool auto_mode) {
    if (!data || len == 0) {
        return {false, false, frame_id, bytes_received_, "empty_chunk"};
    }

    // 1. Chunk boundary and parameters validation:
    // Chunks must be <= 384 bytes. As a compatibility fallback, an atomic 768-byte full frame
    // (total_chunks == 1, chunk_idx == 0, offset == 0, len == kFrameSizeBytes) is also permitted.
    bool is_atomic_full_frame = (total_chunks == 1 && chunk_idx == 0 && offset == 0 && len == kFrameSizeBytes);
    if (!is_atomic_full_frame && (len > 384 || offset + len > kFrameSizeBytes)) {
        bounds_errors_++;
        return {false, false, frame_id, bytes_received_, "chunk_bounds_overflow"};
    }

    if (total_chunks > 0 && chunk_idx >= total_chunks) {
        bounds_errors_++;
        return {false, false, frame_id, bytes_received_, "invalid_chunk_idx"};
    }

    // 2. Strict CRC16-CCITT check if provided
    if (expected_crc != 0) {
        uint16_t actual_crc = CalculateCrc16(data, len);
        if (actual_crc != expected_crc) {
            crc_errors_++;
            return {false, false, frame_id, bytes_received_, "crc_mismatch"};
        }
    }

    // 3. Stale & duplicate frame rejection with initial session allowance
    if (has_committed_any_frame_) {
        uint16_t delta_fwd = (uint16_t)(frame_id - last_committed_frame_id_);
        if (delta_fwd == 0) {
            return {false, false, frame_id, bytes_received_, "duplicate_frame_id"};
        }
        if (delta_fwd >= 32768) {
            return {false, false, frame_id, bytes_received_, "stale_frame_id"};
        }
    }

    uint32_t now = get_current_millis();

    if (!frame_in_progress_ || frame_id != current_frame_id_) {
        if (frame_in_progress_ && frame_id != current_frame_id_) {
            dropped_frames_++;
        }
        Reset();
        current_frame_id_ = frame_id;
        frame_start_time_ms_ = now;
        frame_in_progress_ = true;
    }

    memcpy(frame_buffer_ + offset, data, len);
    MarkBytes(offset, len);

    // 4. Strict completion requirement: never commit an incomplete frame to display
    if (commit_now && !IsFrameComplete()) {
        return {false, false, frame_id, bytes_received_, "incomplete_frame_premature_commit"};
    }

    if (IsFrameComplete()) {
        CommitFrame(auto_mode);
        return {true, true, frame_id, kFrameSizeBytes, nullptr};
    }

    return {true, false, frame_id, bytes_received_, nullptr};
}

FeedResult CanvasAssembler::FeedFullFrame(uint16_t frame_id, const uint8_t* data, size_t len,
                                          uint16_t expected_crc, bool auto_mode) {
    if (!data || len != kFrameSizeBytes) {
        bounds_errors_++;
        return {false, false, frame_id, 0, "invalid_full_frame_length"};
    }

    if (expected_crc != 0) {
        uint16_t actual_crc = CalculateCrc16(data, len);
        if (actual_crc != expected_crc) {
            crc_errors_++;
            return {false, false, frame_id, 0, "crc_mismatch"};
        }
    }

    // Stale & duplicate frame rejection with initial session allowance
    if (has_committed_any_frame_) {
        uint16_t delta_fwd = (uint16_t)(frame_id - last_committed_frame_id_);
        if (delta_fwd == 0) {
            return {false, false, frame_id, bytes_received_, "duplicate_frame_id"};
        }
        if (delta_fwd >= 32768) {
            return {false, false, frame_id, bytes_received_, "stale_frame_id"};
        }
    }

    Reset();
    current_frame_id_ = frame_id;
    frame_start_time_ms_ = get_current_millis();
    frame_in_progress_ = true;

    memcpy(frame_buffer_, data, kFrameSizeBytes);
    memset(byte_bitmap_, 0xFF, sizeof(byte_bitmap_));
    bytes_received_ = kFrameSizeBytes;

    CommitFrame(auto_mode);
    return {true, true, frame_id, kFrameSizeBytes, nullptr};
}

FeedResult CanvasAssembler::ProcessBinaryFrame(const BinaryHeader& header, const uint8_t* payload) {
    if (header.magic[0] != kMagic0 || header.magic[1] != kMagic1 ||
        header.magic[2] != kMagic2 || header.magic[3] != kMagic3) {
        return {false, false, header.frame_seq, 0, "invalid_magic"};
    }

    if (header.version != 1) {
        return {false, false, header.frame_seq, 0, "unsupported_binary_version"};
    }

    bool auto_mode = (header.flags & FLAG_AUTO_MODE) != 0;
    bool commit_now = (header.flags & FLAG_COMMIT_NOW) != 0;
    bool check_crc = !(header.flags & FLAG_SKIP_CRC);

    // Strict CRC validation across all frames with payload unless explicitly skipped via FLAG_SKIP_CRC
    if (check_crc && payload && header.payload_len > 0) {
        uint16_t actual_crc = CalculateCrc16(payload, header.payload_len);
        if (actual_crc != header.crc16) {
            crc_errors_++;
            return {false, false, header.frame_seq, 0, "crc_mismatch"};
        }
    }

    switch (header.type) {
        case BIN_FULL_FRAME: {
            if (header.payload_len != kFrameSizeBytes || header.offset != 0) {
                bounds_errors_++;
                return {false, false, header.frame_seq, 0, "invalid_full_frame_length"};
            }
            return FeedFullFrame(header.frame_seq, payload, header.payload_len, 0, auto_mode);
        }

        case BIN_CHUNK_FRAME: {
            if (header.payload_len > 384 || header.offset + header.payload_len > kFrameSizeBytes) {
                bounds_errors_++;
                return {false, false, header.frame_seq, 0, "chunk_bounds_overflow"};
            }
            return FeedChunk(header.frame_seq, 0, 0, header.offset, payload, header.payload_len, 0, commit_now, auto_mode);
        }

        case BIN_SINGLE_PIXEL: {
            if (header.payload_len != 5) {
                return {false, false, header.frame_seq, 0, "invalid_pixel_payload_length"};
            }
            uint8_t x = payload[0];
            uint8_t y = payload[1];
            uint8_t r = payload[2];
            uint8_t g = payload[3];
            uint8_t b = payload[4];
            return FeedPixel(x, y, r, g, b, auto_mode);
        }

        case BIN_CLEAR: {
            if (header.payload_len != 0 && header.payload_len != 3) {
                return {false, false, header.frame_seq, 0, "invalid_clear_payload_length"};
            }
            uint8_t r = (header.payload_len >= 3) ? payload[0] : 0;
            uint8_t g = (header.payload_len >= 3) ? payload[1] : 0;
            uint8_t b = (header.payload_len >= 3) ? payload[2] : 0;
            return Clear(r, g, b, auto_mode);
        }

        default:
            return {false, false, header.frame_seq, 0, "unsupported_binary_type"};
    }
}

FeedResult CanvasAssembler::FeedPixel(uint8_t x, uint8_t y, uint8_t r, uint8_t g, uint8_t b, bool auto_mode) {
    if (x >= kMatrixWidth || y >= kMatrixHeight) {
        bounds_errors_++;
        return {false, false, 0, 0, "pixel_out_of_bounds"};
    }

    DisplayManager& dm = DisplayManager::GetInstance();
    bool manual_active = dm.IsManualOverrideActive();
    if (!manual_active) {
        if (auto_mode && dm.GetMode() != DisplayMode::PIXEL_CANVAS) {
            dm.SetMode(static_cast<uint8_t>(DisplayMode::PIXEL_CANVAS));
        }
        dm.SetCanvasSource(DisplayManager::CanvasSource::JETSON);
        dm.SetCanvasPixel(x, y, ColorRGB(r, g, b));
    }

    return {true, !manual_active, 0, 3, nullptr};
}

FeedResult CanvasAssembler::Clear(uint8_t r, uint8_t g, uint8_t b, bool auto_mode) {
    DisplayManager& dm = DisplayManager::GetInstance();
    bool manual_active = dm.IsManualOverrideActive();
    if (!manual_active) {
        if (auto_mode && dm.GetMode() != DisplayMode::PIXEL_CANVAS) {
            dm.SetMode(static_cast<uint8_t>(DisplayMode::PIXEL_CANVAS));
        }
        dm.SetCanvasSource(DisplayManager::CanvasSource::JETSON);

        if (r == 0 && g == 0 && b == 0) {
            dm.ClearCanvas();
        } else {
            ColorRGB colors[kPixelCount];
            ColorRGB c(r, g, b);
            for (size_t i = 0; i < kPixelCount; ++i) colors[i] = c;
            dm.SetCanvasFrame(colors);
        }
    }
    Reset();
    return {true, !manual_active, 0, 0, nullptr};
}

void CanvasAssembler::CheckTimeout(uint32_t now_ms, uint32_t timeout_ms) {
    if (frame_in_progress_ && (now_ms - frame_start_time_ms_ > timeout_ms)) {
        dropped_frames_++;
        Reset();
    }
}

} // namespace canvas
