#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <utility>
#include "canvas_protocol.h"

#if !defined(ESP_PLATFORM) && defined(_WIN32)
typedef int esp_err_t;
typedef int uart_port_t;
typedef int gpio_num_t;
typedef uint32_t UBaseType_t;
typedef long BaseType_t;
typedef void* TaskHandle_t;
typedef void* SemaphoreHandle_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define UART_NUM_1 1
#define GPIO_NUM_8 8
#define GPIO_NUM_9 9
#else
#include <esp_err.h>
#include <driver/gpio.h>
#include <driver/uart.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#endif

namespace jetson {

// 串口默认引脚与参数 (显式指定，严禁与扬声器GPIO16/灯板GPIO17/麦克风GPIO5冲突)
static constexpr uart_port_t kDefaultUartPort = UART_NUM_1;
static constexpr gpio_num_t  kDefaultRxPin    = GPIO_NUM_8; // ESP32 RX <- Jetson TX (Pin 8)
static constexpr gpio_num_t  kDefaultTxPin    = GPIO_NUM_9; // ESP32 TX -> Jetson RX (Pin 10)
static constexpr int         kDefaultBaudRate = 115200;
static constexpr size_t      kMaxLineLength   = 1024;
static constexpr const char* kProtocolVersion = "2.3.0";

/**
 * Multi-format stream receiver supporting both:
 * 1. Delimited JSON Lines (\n or \r).
 * 2. High-speed binary canvas frames (magic 0x55 0xAA 0x43 0x46).
 *
 * If incoming text line exceeds kMaxLineLength, triggers on_error ONCE and discards
 * all trailing bytes until the next delimiter. Subsequent frames start fresh.
 */
class FrameReceiver {
public:
    enum class State {
        TEXT,
        BINARY_HEADER,
        BINARY_PAYLOAD
    };

    template <typename TextFn, typename BinaryFn, typename ErrorFn>
    void FeedBytes(const uint8_t* data, size_t len, TextFn&& on_text, BinaryFn&& on_binary, ErrorFn&& on_error) {
        if (!data || len == 0) return;
        uint32_t now = get_current_millis();
        if (state_ != State::TEXT && last_rx_ms_ != 0 && (now - last_rx_ms_) > kBinaryTimeoutMs) {
            // Half-frame / binary reception timeout (>200ms without new bytes)
            // Abort binary reception and resynchronize to text mode
            state_ = State::TEXT;
            header_pos_ = 0;
            payload_pos_ = 0;
            line_len_ = 0;
            on_error(kBinaryTimeoutMs);
        }
        last_rx_ms_ = now;

        for (size_t i = 0; i < len; ++i) {
            uint8_t b = data[i];

            switch (state_) {
                case State::TEXT: {
                    // Check for binary magic sync sequence when starting a new line
                    if (line_len_ == 0 && b == canvas::kMagic0) {
                        header_buf_[0] = b;
                        header_pos_ = 1;
                        state_ = State::BINARY_HEADER;
                        break;
                    }

                    if (b == '\n' || b == '\r') {
                        if (discarding_oversized_) {
                            discarding_oversized_ = false;
                            line_len_ = 0;
                        } else if (line_len_ > 0) {
                            line_buf_[line_len_] = '\0';
                            on_text(line_buf_);
                            line_len_ = 0;
                        }
                    } else {
                        if (discarding_oversized_) {
                            continue;
                        }
                        if (line_len_ < kMaxLineLength) {
                            line_buf_[line_len_++] = static_cast<char>(b);
                        } else {
                            discarding_oversized_ = true;
                            line_len_ = 0;
                            on_error(kMaxLineLength);
                        }
                    }
                    break;
                }

                case State::BINARY_HEADER: {
                    header_buf_[header_pos_++] = b;

                    // Validate magic bytes in positions 1, 2, 3
                    if (header_pos_ == 2 && b != canvas::kMagic1) {
                        // Roll back to text mode: header_buf_[0..1] are normal text chars
                        state_ = State::TEXT;
                        line_buf_[0] = static_cast<char>(header_buf_[0]);
                        line_buf_[1] = static_cast<char>(header_buf_[1]);
                        line_len_ = 2;
                        break;
                    }
                    if (header_pos_ == 3 && b != canvas::kMagic2) {
                        state_ = State::TEXT;
                        for (size_t k = 0; k < 3; ++k) line_buf_[k] = static_cast<char>(header_buf_[k]);
                        line_len_ = 3;
                        break;
                    }
                    if (header_pos_ == 4 && b != canvas::kMagic3) {
                        state_ = State::TEXT;
                        for (size_t k = 0; k < 4; ++k) line_buf_[k] = static_cast<char>(header_buf_[k]);
                        line_len_ = 4;
                        break;
                    }

                    // Once all 16 bytes of BinaryHeader are received
                    if (header_pos_ >= sizeof(canvas::BinaryHeader)) {
                        memcpy(&current_header_, header_buf_, sizeof(canvas::BinaryHeader));
                        bool header_valid = true;
                        if (current_header_.payload_len > canvas::kFrameSizeBytes ||
                            current_header_.offset + current_header_.payload_len > canvas::kFrameSizeBytes) {
                            header_valid = false;
                        }
                        if (current_header_.type == canvas::BIN_FULL_FRAME &&
                            current_header_.payload_len != canvas::kFrameSizeBytes) {
                            header_valid = false;
                        }

                        if (!header_valid) {
                            // Abnormal header, reject and reset to text mode
                            state_ = State::TEXT;
                            line_len_ = 0;
                            header_pos_ = 0;
                            on_error(current_header_.payload_len);
                        } else if (current_header_.payload_len == 0) {
                            on_binary(current_header_, nullptr);
                            state_ = State::TEXT;
                            line_len_ = 0;
                            header_pos_ = 0;
                        } else {
                            state_ = State::BINARY_PAYLOAD;
                            payload_pos_ = 0;
                        }
                    }
                    break;
                }

                case State::BINARY_PAYLOAD: {
                    binary_payload_[payload_pos_++] = b;
                    if (payload_pos_ >= current_header_.payload_len) {
                        on_binary(current_header_, binary_payload_);
                        state_ = State::TEXT;
                        line_len_ = 0;
                        header_pos_ = 0;
                        payload_pos_ = 0;
                    }
                    break;
                }
            }
        }
    }

    // 2-callback backward compatibility overload
    template <typename TextFn, typename ErrorFn>
    void FeedBytes(const uint8_t* data, size_t len, TextFn&& on_text, ErrorFn&& on_error) {
        FeedBytes(data, len, std::forward<TextFn>(on_text),
                  [](const canvas::BinaryHeader&, const uint8_t*){},
                  std::forward<ErrorFn>(on_error));
    }

    void Reset() {
        line_len_ = 0;
        discarding_oversized_ = false;
        state_ = State::TEXT;
        header_pos_ = 0;
        payload_pos_ = 0;
        last_rx_ms_ = 0;
    }

    template <typename ErrorFn>
    void CheckTimeout(uint32_t now, ErrorFn&& on_error) {
        if (state_ != State::TEXT && last_rx_ms_ != 0 && (now - last_rx_ms_) > kBinaryTimeoutMs) {
            state_ = State::TEXT;
            header_pos_ = 0;
            payload_pos_ = 0;
            line_len_ = 0;
            on_error(kBinaryTimeoutMs);
        }
    }

    bool IsDiscardingOversized() const { return discarding_oversized_; }
    size_t GetCurrentLineLength() const { return line_len_; }
    State GetState() const { return state_; }

private:
    char line_buf_[kMaxLineLength + 1];
    size_t line_len_ = 0;
    bool discarding_oversized_ = false;

    State state_ = State::TEXT;
    uint8_t header_buf_[sizeof(canvas::BinaryHeader)];
    size_t header_pos_ = 0;
    canvas::BinaryHeader current_header_{};
    uint8_t binary_payload_[canvas::kFrameSizeBytes];
    size_t payload_pos_ = 0;

    uint32_t last_rx_ms_ = 0;
    static constexpr uint32_t kBinaryTimeoutMs = 200;
};

class JetsonUart {
public:
    static JetsonUart& GetInstance();

    // 初始化 UART1 硬件控制器与引脚
    esp_err_t Init(uart_port_t port = kDefaultUartPort,
                   gpio_num_t rx_pin = kDefaultRxPin,
                   gpio_num_t tx_pin = kDefaultTxPin,
                   int baud_rate = kDefaultBaudRate);

    // 启动后台异步监听任务 (运行在 Core 0，优先级 3)
    esp_err_t StartTask(UBaseType_t priority = 3, BaseType_t core_id = 0);

    // 线程安全发送整行数据 (自动追加 \n)
    esp_err_t SendLine(const char* line);

    // 线程安全直接发送原生字节流
    esp_err_t SendRaw(const void* data, size_t len);

    // 解析与调度单行命令 (供内部任务及主机自动化单测直接调用)
    static void ProcessCommand(const char* line, char* out_reply, size_t out_reply_size);

    // 处理二进制画布帧
    static void ProcessBinaryFrame(const canvas::BinaryHeader& header, const uint8_t* payload,
                                   char* out_reply, size_t out_reply_size);

    bool IsInitialized() const { return initialized_; }
    bool IsRunning() const { return is_running_; }

    // 会话与冲突仲裁
    void SetSession(const char* session_id);
    void ClearSession();
    const char* GetSessionId() const { return session_id_; }
    bool IsSessionActive() const { return session_active_; }
    void StartSession();
    void StopSession();
    void PingSession();
    bool IsManualOverrideActive() const;
    void SetManualOverride(bool active);

    // 释放所有当前处于按住状态的按键
    void ReleaseHeldKeys();
    uint16_t GetHeldKeys() const { return held_keys_; }

    // 诊断统计
    uint32_t GetRxFramesCount() const { return rx_frames_; }
    uint32_t GetTxFramesCount() const { return tx_frames_; }
    uint32_t GetRxErrorsCount() const { return rx_errors_; }

private:
    JetsonUart();
    ~JetsonUart();

    static void UartTaskTrampoline(void* arg);
    void UartTaskLoop();

    uart_port_t port_ = kDefaultUartPort;
    gpio_num_t  rx_pin_ = kDefaultRxPin;
    gpio_num_t  tx_pin_ = kDefaultTxPin;
    int         baud_rate_ = kDefaultBaudRate;

    bool        initialized_ = false;
    bool        is_running_ = false;
    TaskHandle_t task_handle_ = nullptr;
    SemaphoreHandle_t tx_mutex_ = nullptr;

    FrameReceiver receiver_;

    uint32_t rx_frames_ = 0;
    uint32_t tx_frames_ = 0;
    uint32_t rx_errors_ = 0;

    // 会话与超时看门狗
    char     session_id_[36] = {0};
    bool     session_active_ = false;
    uint32_t session_start_ms_ = 0;
    uint32_t last_session_ping_ms_ = 0;
    uint16_t held_keys_ = 0;
    uint32_t last_input_time_ms_ = 0;
};

} // namespace jetson
