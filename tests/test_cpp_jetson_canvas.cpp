#include <iostream>
#include <cassert>
#include <cstring>
#include <vector>
#include <cstdint>

// Define a host mock environment for DisplayManager so canvas_protocol.cc can compile cleanly
#define HOST_TEST 1

#include "../firmware-s3/main/display/display_types.h"

// Mock DisplayManager for host unit testing
class DisplayManager {
public:
    static DisplayManager& GetInstance() {
        static DisplayManager instance;
        return instance;
    }

    void SetMode(DisplayMode mode) {
        current_mode_ = mode;
    }

    void SetMode(uint8_t mode) {
        current_mode_ = static_cast<DisplayMode>(mode);
    }

    DisplayMode GetMode() const {
        return current_mode_;
    }

    void SetManualOverride(bool active) {
        manual_override_active_ = active;
    }

    bool IsManualOverrideActive() const {
        return manual_override_active_;
    }

    void SetCanvasFrame(const ColorRGB* colors) {
        if (colors) {
            std::memcpy(canvas_buffer_, colors, sizeof(canvas_buffer_));
            frame_commit_count_++;
        }
    }

    void SetCanvasPixel(int x, int y, ColorRGB color) {
        if (x >= 0 && x < 16 && y >= 0 && y < 16) {
            canvas_buffer_[y * 16 + x] = color;
            pixel_commit_count_++;
        }
    }

    void ClearCanvas() {
        std::memset(canvas_buffer_, 0, sizeof(canvas_buffer_));
        clear_count_++;
    }

    ColorRGB canvas_buffer_[256]{};
    uint32_t frame_commit_count_ = 0;
    uint32_t pixel_commit_count_ = 0;
    uint32_t clear_count_ = 0;
    DisplayMode current_mode_ = DisplayMode::RAINBOW_WAVE;
    bool manual_override_active_ = false;
};

// Include canvas protocol source and headers
#include "../firmware-s3/main/protocol/canvas_protocol.h"
#include "../firmware-s3/main/protocol/canvas_protocol.cc"
#include "../firmware-s3/main/protocol/jetson_uart.h"

void RunTest(const char* name, void (*fn)()) {
    std::cout << "[RUNNING] " << name << " ... ";
    fn();
    std::cout << "PASSED\n";
}

// 1. CRC16 Calculation Verification
void Test_Crc16_Calculation() {
    const uint8_t data[] = "hello world";
    uint16_t crc = canvas::CalculateCrc16(data, 11);
    // Matches Python binascii.crc_hqx(b"hello world", 0xFFFF) == 0xEFEB
    assert(crc == 0xEFEB);

    uint8_t zero_data[768] = {0};
    uint16_t crc_zero = canvas::CalculateCrc16(zero_data, sizeof(zero_data));
    assert(crc_zero != 0);
}

// 2. Buffer Overflow and Chunk Bounds Defense
void Test_BufferOverflow_Defense() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    assembler.Reset();

    uint8_t payload[800];
    std::memset(payload, 0xAA, sizeof(payload));

    // Case A: Chunk byte length exceeds 384 bytes
    auto res1 = assembler.FeedChunk(1, 0, 2, 0, payload, 385, 0, false, false);
    assert(!res1.success);
    assert(std::strcmp(res1.error_msg, "chunk_bounds_overflow") == 0);

    // Case B: Offset + length exceeds 768
    auto res2 = assembler.FeedChunk(1, 0, 2, 700, payload, 100, 0, false, false);
    assert(!res2.success);
    assert(std::strcmp(res2.error_msg, "chunk_bounds_overflow") == 0);

    // Case C: Invalid chunk index (chunk_idx >= total_chunks)
    auto res3 = assembler.FeedChunk(1, 2, 2, 0, payload, 100, 0, false, false);
    assert(!res3.success);
    assert(std::strcmp(res3.error_msg, "invalid_chunk_idx") == 0);

    // Case D: Empty chunk
    auto res4 = assembler.FeedChunk(1, 0, 2, 0, nullptr, 0, 0, false, false);
    assert(!res4.success);
    assert(std::strcmp(res4.error_msg, "empty_chunk") == 0);
}

// 3. Incomplete Frame Rejection (commit_now with incomplete frame)
void Test_IncompleteFrame_Rejection() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;

    uint8_t chunk_data[192];
    std::memset(chunk_data, 0x55, sizeof(chunk_data));

    // Send only chunk 0 (192 bytes out of 768) but set commit_now = true
    auto res = assembler.FeedChunk(10, 0, 4, 0, chunk_data, sizeof(chunk_data), 0, true, true);

    // Must be rejected! Incomplete frame cannot be committed to display
    assert(!res.success);
    assert(!res.committed);
    assert(std::strcmp(res.error_msg, "incomplete_frame_premature_commit") == 0);
    assert(!assembler.IsFrameComplete());
    assert(dm.frame_commit_count_ == 0); // Display not modified
}

// 4. Atomic Frame Completeness and Sequential Chunk Commit
void Test_Atomic_FrameCompleteness() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;

    uint8_t chunk[192];
    std::memset(chunk, 0x11, sizeof(chunk));

    // Chunk 0 (0..191)
    auto r0 = assembler.FeedChunk(100, 0, 4, 0, chunk, 192, 0, false, true);
    assert(r0.success && !r0.committed);
    assert(!assembler.IsFrameComplete());

    // Chunk 1 (192..383)
    std::memset(chunk, 0x22, sizeof(chunk));
    auto r1 = assembler.FeedChunk(100, 1, 4, 192, chunk, 192, 0, false, true);
    assert(r1.success && !r1.committed);

    // Chunk 2 (384..575)
    std::memset(chunk, 0x33, sizeof(chunk));
    auto r2 = assembler.FeedChunk(100, 2, 4, 384, chunk, 192, 0, false, true);
    assert(r2.success && !r2.committed);

    // Chunk 3 (576..767) - Completes the full 768 bytes
    std::memset(chunk, 0x44, sizeof(chunk));
    auto r3 = assembler.FeedChunk(100, 3, 4, 576, chunk, 192, 0, true, true);
    assert(r3.success && r3.committed);
    assert(dm.frame_commit_count_ == 1);
    assert(assembler.GetLastCommittedFrameId() == 100);
}

// 5. Stale and Duplicate Frame Defense
void Test_StaleAndDuplicateFrame_Defense() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    assembler.Reset();

    uint8_t full_frame[768];
    std::memset(full_frame, 0x77, sizeof(full_frame));

    // Feed and commit frame 200 via 2 chunks of 384
    assembler.FeedChunk(200, 0, 2, 0, full_frame, 384, 0, false, false);
    auto r_commit = assembler.FeedChunk(200, 1, 2, 384, full_frame + 384, 384, 0, true, false);
    assert(r_commit.success && r_commit.committed);

    // Attempt to resend duplicate frame 200
    auto r_dup = assembler.FeedChunk(200, 0, 2, 0, full_frame, 384, 0, false, false);
    assert(!r_dup.success);
    assert(std::strcmp(r_dup.error_msg, "duplicate_frame_id") == 0);

    // Attempt to send older/stale frame 199
    auto r_stale = assembler.FeedChunk(199, 0, 2, 0, full_frame, 384, 0, false, false);
    assert(!r_stale.success);
    assert(std::strcmp(r_stale.error_msg, "stale_frame_id") == 0);
}

// 6. Cross-Source Manual Control Priority & Arbitration
void Test_CrossSource_Arbitration() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();

    // User on Mobile or PC web app manually switches to Mode 3 (Matrix Rain Pro)
    dm.SetMode(DisplayMode::MATRIX_RAIN_PRO);
    dm.SetManualOverride(true);
    assert(dm.GetMode() == DisplayMode::MATRIX_RAIN_PRO);
    assert(dm.IsManualOverrideActive());

    // Jetson sends full frame with auto_mode = true
    uint8_t full[768] = {0};
    assembler.FeedChunk(300, 0, 2, 0, full, 384, 0, false, true);
    auto r = assembler.FeedChunk(300, 1, 2, 384, full + 384, 384, 0, true, true);
    assert(r.success && r.committed);

    // CRITICAL: Mode MUST NOT be stolen! Mode must still be MATRIX_RAIN_PRO
    assert(dm.GetMode() == DisplayMode::MATRIX_RAIN_PRO);

    // User clears manual override or switches to Mode 29 explicitly
    dm.SetManualOverride(false);
    assembler.FeedChunk(301, 0, 2, 0, full, 384, 0, false, true);
    assembler.FeedChunk(301, 1, 2, 384, full + 384, 384, 0, true, true);

    // Now auto_mode is allowed to switch to PIXEL_CANVAS
    assert(dm.GetMode() == DisplayMode::PIXEL_CANVAS);
}

// 7. Binary Frame Receiver Timeout and Resynchronization
void Test_FrameReceiver_TimeoutAndResync() {
    jetson::FrameReceiver receiver;
    receiver.Reset();

    // Feed 4 bytes magic
    uint8_t magic[4] = {canvas::kMagic0, canvas::kMagic1, canvas::kMagic2, canvas::kMagic3};
    receiver.FeedBytes(magic, 4, [](const char*){}, [](const canvas::BinaryHeader&, const uint8_t*){}, [](size_t){});
    assert(receiver.GetState() == jetson::FrameReceiver::State::BINARY_HEADER);

    // Feed 8 bytes of header (incomplete, total 12 bytes received so far)
    uint8_t partial_hdr[8] = {1, 1, 0, 0, 0, 0, 0, 3}; // 768 bytes payload claimed
    receiver.FeedBytes(partial_hdr, 8, [](const char*){}, [](const canvas::BinaryHeader&, const uint8_t*){}, [](size_t){});
    assert(receiver.GetState() == jetson::FrameReceiver::State::BINARY_HEADER);

    // Advance time past 200ms timeout
    bool timeout_called = false;
    uint32_t now = get_current_millis() + 300;
    receiver.CheckTimeout(now, [&](size_t code) {
        timeout_called = true;
    });

    // Verify parser recovered back to TEXT state cleanly!
    assert(timeout_called);
    assert(receiver.GetState() == jetson::FrameReceiver::State::TEXT);

    // Now feed a regular JSON line, verify it is cleanly dispatched
    bool text_received = false;
    const char json_cmd[] = "{\"cmd\":\"get_capabilities\"}\n";
    receiver.FeedBytes(reinterpret_cast<const uint8_t*>(json_cmd), std::strlen(json_cmd),
                       [&](const char* line) {
                           text_received = true;
                           assert(std::strcmp(line, "{\"cmd\":\"get_capabilities\"}") == 0);
                       },
                       [](const canvas::BinaryHeader&, const uint8_t*){},
                       [](size_t){});
    assert(text_received);
}

// 8. Binary Header Oversized Payload Defense
void Test_BinaryHeader_OversizedDefense() {
    jetson::FrameReceiver receiver;
    receiver.Reset();

    canvas::BinaryHeader hdr{};
    hdr.magic[0] = canvas::kMagic0;
    hdr.magic[1] = canvas::kMagic1;
    hdr.magic[2] = canvas::kMagic2;
    hdr.magic[3] = canvas::kMagic3;
    hdr.version = 1;
    hdr.type = canvas::BIN_FULL_FRAME;
    hdr.payload_len = 1000; // Abnormal: exceeds 768

    bool error_invoked = false;
    receiver.FeedBytes(reinterpret_cast<const uint8_t*>(&hdr), sizeof(hdr),
                       [](const char*){},
                       [](const canvas::BinaryHeader&, const uint8_t*){},
                       [&](size_t code) {
                           error_invoked = true;
                           assert(code == 1000);
                       });

    // Verify rejected and state reset to TEXT
    assert(error_invoked);
    assert(receiver.GetState() == jetson::FrameReceiver::State::TEXT);
}

int main() {
    std::cout << "====================================================\n";
    std::cout << "Starting Native C++ Canvas Protocol & UART Tests\n";
    std::cout << "====================================================\n";

    RunTest("Test_Crc16_Calculation", Test_Crc16_Calculation);
    RunTest("Test_BufferOverflow_Defense", Test_BufferOverflow_Defense);
    RunTest("Test_IncompleteFrame_Rejection", Test_IncompleteFrame_Rejection);
    RunTest("Test_Atomic_FrameCompleteness", Test_Atomic_FrameCompleteness);
    RunTest("Test_StaleAndDuplicateFrame_Defense", Test_StaleAndDuplicateFrame_Defense);
    RunTest("Test_CrossSource_Arbitration", Test_CrossSource_Arbitration);
    RunTest("Test_FrameReceiver_TimeoutAndResync", Test_FrameReceiver_TimeoutAndResync);
    RunTest("Test_BinaryHeader_OversizedDefense", Test_BinaryHeader_OversizedDefense);

    std::cout << "====================================================\n";
    std::cout << "ALL 8 NATIVE C++ TESTS PASSED!\n";
    std::cout << "====================================================\n";
    return 0;
}
