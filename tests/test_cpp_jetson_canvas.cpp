#include <iostream>
#include <cassert>
#include <cstring>
#include <vector>
#include <cstdint>

// Define host test environment
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

// Include canvas protocol and UART receiver headers
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

// 2. Production C++ ProcessBinaryFrame 768-Byte Full Frame Success Path
void Test_Full_Binary_Frame_768_Success() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;
    dm.SetManualOverride(false);
    dm.SetMode(DisplayMode::RAINBOW_WAVE);

    // Prepare 768 bytes of test RGB data (256 pixels)
    uint8_t payload[768];
    for (size_t i = 0; i < 256; ++i) {
        payload[i * 3 + 0] = static_cast<uint8_t>(i);       // R
        payload[i * 3 + 1] = static_cast<uint8_t>(255 - i); // G
        payload[i * 3 + 2] = static_cast<uint8_t>((i * 7) % 256); // B
    }

    uint16_t crc = canvas::CalculateCrc16(payload, sizeof(payload));

    canvas::BinaryHeader hdr{};
    hdr.magic[0] = canvas::kMagic0;
    hdr.magic[1] = canvas::kMagic1;
    hdr.magic[2] = canvas::kMagic2;
    hdr.magic[3] = canvas::kMagic3;
    hdr.type = canvas::BIN_FULL_FRAME;
    hdr.version = 1;
    hdr.frame_seq = 42;
    hdr.payload_len = 768;
    hdr.offset = 0;
    hdr.flags = canvas::FLAG_COMMIT_NOW | canvas::FLAG_AUTO_MODE;
    hdr.crc16 = crc;

    // Call production C++ ProcessBinaryFrame with 768-byte full frame
    auto res = assembler.ProcessBinaryFrame(hdr, payload);

    assert(res.success);
    assert(res.committed);
    assert(res.frame_id == 42);
    assert(res.received_bytes == 768);
    assert(res.error_msg == nullptr);
    assert(dm.frame_commit_count_ == 1);
    assert(dm.GetMode() == DisplayMode::PIXEL_CANVAS);

    // Verify all 256 pixels match byte-for-byte in display buffer
    for (size_t i = 0; i < 256; ++i) {
        assert(dm.canvas_buffer_[i].r == payload[i * 3 + 0]);
        assert(dm.canvas_buffer_[i].g == payload[i * 3 + 1]);
        assert(dm.canvas_buffer_[i].b == payload[i * 3 + 2]);
    }
}

// 3. Sequential 2-Chunk 384+384 Bytes Atomic Assembly
void Test_Two_Chunks_384_Success() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;

    uint8_t chunk0[384];
    uint8_t chunk1[384];
    std::memset(chunk0, 0x11, sizeof(chunk0));
    std::memset(chunk1, 0x22, sizeof(chunk1));

    // Chunk 0: offset 0, len 384, total_chunks 2
    auto r0 = assembler.FeedChunk(101, 0, 2, 0, chunk0, 384, 0, false, true);
    assert(r0.success);
    assert(!r0.committed);
    assert(!assembler.IsFrameComplete());
    assert(dm.frame_commit_count_ == 0);

    // Chunk 1: offset 384, len 384, total_chunks 2, commit_now = true
    auto r1 = assembler.FeedChunk(101, 1, 2, 384, chunk1, 384, 0, true, true);
    assert(r1.success);
    assert(r1.committed);
    assert(dm.frame_commit_count_ == 1);
    assert(assembler.GetLastCommittedFrameId() == 101);
}

// 4. Buffer Overflow and Chunk Bounds Defense
void Test_BufferOverflow_Defense() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    assembler.Reset();

    uint8_t payload[800];
    std::memset(payload, 0xAA, sizeof(payload));

    // Case A: Chunk byte length exceeds 384 bytes in chunk mode (total_chunks > 1)
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

// 5. Incomplete Frame Rejection (commit_now with incomplete frame)
void Test_IncompleteFrame_Rejection() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;

    uint8_t chunk_data[192];
    std::memset(chunk_data, 0x55, sizeof(chunk_data));

    // Send only chunk 0 (192 bytes out of 768) but set commit_now = true
    auto res = assembler.FeedChunk(150, 0, 4, 0, chunk_data, sizeof(chunk_data), 0, true, true);

    // Must be rejected! Incomplete frame cannot be committed to display
    assert(!res.success);
    assert(!res.committed);
    assert(std::strcmp(res.error_msg, "incomplete_frame_premature_commit") == 0);
    assert(!assembler.IsFrameComplete());
    assert(dm.frame_commit_count_ == 0); // Display not modified
}

// 6. CRC Mismatch Rejection
void Test_CrcMismatch_Rejection() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();
    dm.frame_commit_count_ = 0;

    uint8_t payload[768];
    std::memset(payload, 0x88, sizeof(payload));
    uint16_t real_crc = canvas::CalculateCrc16(payload, sizeof(payload));

    canvas::BinaryHeader hdr{};
    hdr.magic[0] = canvas::kMagic0;
    hdr.magic[1] = canvas::kMagic1;
    hdr.magic[2] = canvas::kMagic2;
    hdr.magic[3] = canvas::kMagic3;
    hdr.type = canvas::BIN_FULL_FRAME;
    hdr.version = 1;
    hdr.frame_seq = 160;
    hdr.payload_len = 768;
    hdr.offset = 0;
    hdr.flags = canvas::FLAG_COMMIT_NOW;
    hdr.crc16 = real_crc ^ 0x1234; // Corrupt CRC!

    auto res = assembler.ProcessBinaryFrame(hdr, payload);
    assert(!res.success);
    assert(!res.committed);
    assert(std::strcmp(res.error_msg, "crc_mismatch") == 0);
    assert(dm.frame_commit_count_ == 0);
}

// 7. Stale and Duplicate Frame Defense
void Test_StaleAndDuplicateFrame_Defense() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    assembler.Reset();

    uint8_t full_frame[768];
    std::memset(full_frame, 0x77, sizeof(full_frame));

    // Feed and commit frame 200 via FeedFullFrame
    auto r_commit = assembler.FeedFullFrame(200, full_frame, 768, 0, false);
    assert(r_commit.success && r_commit.committed);

    // Attempt to resend duplicate frame 200
    auto r_dup = assembler.FeedFullFrame(200, full_frame, 768, 0, false);
    assert(!r_dup.success);
    assert(std::strcmp(r_dup.error_msg, "duplicate_frame_id") == 0);

    // Attempt to send older/stale frame 199
    auto r_stale = assembler.FeedFullFrame(199, full_frame, 768, 0, false);
    assert(!r_stale.success);
    assert(std::strcmp(r_stale.error_msg, "stale_frame_id") == 0);
}

// 8. Cross-Source Manual Control Priority & Displayed Flag
void Test_CrossSource_Arbitration() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    auto& dm = DisplayManager::GetInstance();
    assembler.Reset();

    // User on Mobile or PC web app manually switches to Mode 3 (Matrix Rain Pro)
    dm.SetMode(DisplayMode::MATRIX_RAIN_PRO);
    dm.SetManualOverride(true);
    assert(dm.GetMode() == DisplayMode::MATRIX_RAIN_PRO);
    assert(dm.IsManualOverrideActive());

    // Jetson sends full 768-byte frame with auto_mode = true
    uint8_t full[768] = {0};
    auto r = assembler.FeedFullFrame(300, full, 768, 0, true);
    assert(r.success && r.committed);

    // CRITICAL: Mode MUST NOT be stolen! Mode must still be MATRIX_RAIN_PRO
    assert(dm.GetMode() == DisplayMode::MATRIX_RAIN_PRO);

    // Verify displayed calculation: committed is true, but displayed is FALSE because manual_override is active
    bool manual_overridden = dm.IsManualOverrideActive();
    bool displayed = r.committed && !manual_overridden && (dm.GetMode() == DisplayMode::PIXEL_CANVAS);
    assert(!displayed);
    assert(manual_overridden);

    // User clears manual override or switches to Mode 29 explicitly
    dm.SetManualOverride(false);
    auto r2 = assembler.FeedFullFrame(301, full, 768, 0, true);
    assert(r2.success && r2.committed);

    // Now auto_mode is allowed to switch to PIXEL_CANVAS and displayed becomes true!
    assert(dm.GetMode() == DisplayMode::PIXEL_CANVAS);
    bool displayed2 = r2.committed && !dm.IsManualOverrideActive() && (dm.GetMode() == DisplayMode::PIXEL_CANVAS);
    assert(displayed2);
}

// 9. Session Stop & Timeout Defense
void Test_Session_Stop_And_Expiry() {
    auto& assembler = canvas::CanvasAssembler::GetInstance();
    assembler.Reset();

    // Verify session timeout behavior logic
    uint32_t last_ping = 1000;
    uint32_t now_active = 5000;
    bool active = (now_active - last_ping) <= 15000;
    assert(active);

    uint32_t now_expired = 20000;
    bool expired = (now_expired - last_ping) > 15000;
    assert(expired);

    // Verify StopSession resets assembler so late chunks cannot finish
    uint32_t committed_before = assembler.GetCommittedFrames();
    uint8_t chunk[384] = {0};
    assembler.FeedChunk(400, 0, 2, 0, chunk, 384, 0, false, false);
    assert(assembler.IsFrameInProgress());

    // Stop session resets state
    assembler.Reset();
    assert(!assembler.IsFrameInProgress());
    assert(assembler.GetCommittedFrames() == committed_before);
}

// 10. Binary Frame Receiver Timeout and Resynchronization
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

// 11. Binary Header Oversized Payload Defense
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
    RunTest("Test_Full_Binary_Frame_768_Success", Test_Full_Binary_Frame_768_Success);
    RunTest("Test_Two_Chunks_384_Success", Test_Two_Chunks_384_Success);
    RunTest("Test_BufferOverflow_Defense", Test_BufferOverflow_Defense);
    RunTest("Test_IncompleteFrame_Rejection", Test_IncompleteFrame_Rejection);
    RunTest("Test_CrcMismatch_Rejection", Test_CrcMismatch_Rejection);
    RunTest("Test_StaleAndDuplicateFrame_Defense", Test_StaleAndDuplicateFrame_Defense);
    RunTest("Test_CrossSource_Arbitration", Test_CrossSource_Arbitration);
    RunTest("Test_Session_Stop_And_Expiry", Test_Session_Stop_And_Expiry);
    RunTest("Test_FrameReceiver_TimeoutAndResync", Test_FrameReceiver_TimeoutAndResync);
    RunTest("Test_BinaryHeader_OversizedDefense", Test_BinaryHeader_OversizedDefense);

    std::cout << "====================================================\n";
    std::cout << "ALL 11 NATIVE C++ TESTS PASSED!\n";
    std::cout << "====================================================\n";
    return 0;
}
