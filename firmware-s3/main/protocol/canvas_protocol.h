#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#if !defined(ESP_PLATFORM) && defined(_WIN32)
#include <string.h>
#include <chrono>
static inline uint32_t get_current_millis() {
    using namespace std::chrono;
    static auto start_time = steady_clock::now();
    uint32_t ms = (uint32_t)duration_cast<milliseconds>(steady_clock::now() - start_time).count();
    return ms == 0 ? 1 : ms;
}
#else
#include <esp_err.h>
#include <esp_log.h>
#include <esp_timer.h>
static inline uint32_t get_current_millis() {
    return (uint32_t)(esp_timer_get_time() / 1000ULL);
}
#endif

namespace canvas {

static constexpr size_t kMatrixWidth = 16;
static constexpr size_t kMatrixHeight = 16;
static constexpr size_t kPixelCount = kMatrixWidth * kMatrixHeight; // 256
static constexpr size_t kBytesPerPixel = 3;                         // RGB888
static constexpr size_t kFrameSizeBytes = kPixelCount * kBytesPerPixel; // 768 bytes

// Binary Frame Protocol Magic Bytes (Unambiguous sync: 'U', 0xAA, 'C', 'F')
static constexpr uint8_t kMagic0 = 0x55;
static constexpr uint8_t kMagic1 = 0xAA;
static constexpr uint8_t kMagic2 = 0x43; // 'C' (Canvas)
static constexpr uint8_t kMagic3 = 0x46; // 'F' (Frame)

enum BinaryType : uint8_t {
    BIN_FULL_FRAME   = 0x01, // Full 768-byte frame payload
    BIN_CHUNK_FRAME  = 0x02, // Chunk payload (<= 384 bytes)
    BIN_SINGLE_PIXEL = 0x03, // 5 bytes payload: [x, y, r, g, b]
    BIN_CLEAR        = 0x04, // Clear canvas (optional 3 bytes [r, g, b])
};

enum Flags : uint16_t {
    FLAG_NONE        = 0,
    FLAG_COMMIT_NOW  = 1u << 0, // Force commit frame immediately
    FLAG_AUTO_MODE   = 1u << 1, // Automatically switch to DisplayMode::PIXEL_CANVAS (29)
};

#pragma pack(push, 1)
struct BinaryHeader {
    uint8_t  magic[4];       // 0x55, 0xAA, 0x43, 0x46
    uint8_t  type;           // BinaryType
    uint8_t  version;        // 0x01
    uint16_t frame_seq;      // Frame sequence number (Little-Endian)
    uint16_t payload_len;    // Length of following payload bytes
    uint16_t offset;         // Byte offset in frame buffer (0..767)
    uint16_t flags;          // Flags bitmask (Flags)
    uint16_t crc16;          // CRC16-CCITT of payload bytes
};
#pragma pack(pop)
static_assert(sizeof(BinaryHeader) == 16, "BinaryHeader must be exactly 16 bytes");

/**
 * Standard CRC16-CCITT (poly 0x1021, init 0xFFFF).
 * Fully matches Python binascii.crc_hqx(data, 0xFFFF).
 */
uint16_t CalculateCrc16(const uint8_t* data, size_t len);

struct FeedResult {
    bool success;
    bool committed;
    uint16_t frame_id;
    uint32_t received_bytes;
    const char* error_msg;
};

class CanvasAssembler {
public:
    static CanvasAssembler& GetInstance();

    CanvasAssembler();
    void Reset();

    // Chunked payload feed (from JSON chunk or binary chunk)
    FeedResult FeedChunk(uint16_t frame_id, uint16_t chunk_idx, uint16_t total_chunks,
                         uint16_t offset, const uint8_t* data, size_t len,
                         uint16_t expected_crc = 0, bool commit_now = false, bool auto_mode = true);

    // Process complete binary frame according to header
    FeedResult ProcessBinaryFrame(const BinaryHeader& header, const uint8_t* payload);

    // Single pixel feed
    FeedResult FeedPixel(uint8_t x, uint8_t y, uint8_t r, uint8_t g, uint8_t b, bool auto_mode = false);

    // Clear canvas
    FeedResult Clear(uint8_t r = 0, uint8_t g = 0, uint8_t b = 0, bool auto_mode = false);

    // Frame completeness validation
    bool IsFrameComplete() const;
    bool IsBitmapFullyCovered() const;

    // Timeout check (discards incomplete frame after inactivity)
    void CheckTimeout(uint32_t now_ms, uint32_t timeout_ms = 500);

    // Diagnostic metrics
    uint32_t GetCommittedFrames() const { return committed_frames_; }
    uint32_t GetDroppedFrames() const { return dropped_frames_; }
    uint32_t GetCrcErrors() const { return crc_errors_; }
    uint32_t GetBoundsErrors() const { return bounds_errors_; }
    uint16_t GetLastCommittedFrameId() const { return last_committed_frame_id_; }
    bool IsFrameInProgress() const { return frame_in_progress_; }

private:
    uint8_t frame_buffer_[kFrameSizeBytes];
    uint8_t byte_bitmap_[kFrameSizeBytes / 8]; // 96 bytes bitmap tracking 768 byte coverage
    uint16_t current_frame_id_ = 0;
    uint32_t bytes_received_ = 0;
    uint32_t frame_start_time_ms_ = 0;
    bool frame_in_progress_ = false;

    uint32_t committed_frames_ = 0;
    uint32_t dropped_frames_ = 0;
    uint32_t crc_errors_ = 0;
    uint32_t bounds_errors_ = 0;
    uint16_t last_committed_frame_id_ = 0;

    void MarkBytes(uint16_t offset, size_t len);
    void CommitFrame(bool auto_mode);
};

} // namespace canvas

