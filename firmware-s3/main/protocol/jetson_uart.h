#pragma once

#include <stdint.h>
#include <stddef.h>

#if !defined(ESP_PLATFORM) && defined(_WIN32)
typedef int uart_port_t;
typedef int gpio_num_t;
typedef uint32_t UBaseType_t;
typedef long BaseType_t;
typedef void* TaskHandle_t;
typedef void* SemaphoreHandle_t;
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
static constexpr const char* kProtocolVersion = "2.2.0";

/**
 * Robust stream frame receiver with strict delimiter boundary and overflow discarding.
 * If incoming frame exceeds kMaxLineLength, triggers on_error ONCE and discards
 * all trailing bytes until the next delimiter (\n or \r). Subsequent frames start fresh.
 */
class FrameReceiver {
public:
    template <typename ProcessFn, typename ErrorFn>
    void FeedBytes(const uint8_t* data, size_t len, ProcessFn&& on_frame, ErrorFn&& on_error) {
        if (!data || len == 0) return;
        for (size_t i = 0; i < len; ++i) {
            char c = static_cast<char>(data[i]);
            if (c == '\n' || c == '\r') {
                if (discarding_oversized_) {
                    discarding_oversized_ = false;
                    line_len_ = 0;
                } else if (line_len_ > 0) {
                    line_buf_[line_len_] = '\0';
                    on_frame(line_buf_);
                    line_len_ = 0;
                }
            } else {
                if (discarding_oversized_) {
                    // Silently drop all bytes of oversized frame tail until next delimiter
                    continue;
                }
                if (line_len_ < kMaxLineLength) {
                    line_buf_[line_len_++] = c;
                } else {
                    // Max length exceeded: trigger overflow error ONCE and enter discarding state
                    discarding_oversized_ = true;
                    line_len_ = 0;
                    on_error(kMaxLineLength);
                }
            }
        }
    }

    void Reset() {
        line_len_ = 0;
        discarding_oversized_ = false;
    }

    bool IsDiscardingOversized() const { return discarding_oversized_; }
    size_t GetCurrentLineLength() const { return line_len_; }

private:
    char line_buf_[kMaxLineLength + 1];
    size_t line_len_ = 0;
    bool discarding_oversized_ = false;
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
    // 返回生成的响应 JSON 字符串；若无需回包则返回空字符串
    static void ProcessCommand(const char* line, char* out_reply, size_t out_reply_size);

    bool IsInitialized() const { return initialized_; }
    bool IsRunning() const { return is_running_; }

    // 诊断统计
    uint32_t GetRxFramesCount() const { return rx_frames_; }
    uint32_t GetTxFramesCount() const { return tx_frames_; }
    uint32_t GetRxErrorsCount() const { return rx_errors_; }

private:
    JetsonUart();
    ~JetsonUart();

    JetsonUart(const JetsonUart&) = delete;
    JetsonUart& operator=(const JetsonUart&) = delete;

    static void UartTaskTrampoline(void* arg);
    void UartTaskLoop();

    uart_port_t port_ = kDefaultUartPort;
    gpio_num_t rx_pin_ = kDefaultRxPin;
    gpio_num_t tx_pin_ = kDefaultTxPin;
    int baud_rate_ = kDefaultBaudRate;

    bool initialized_ = false;
    volatile bool is_running_ = false;
    TaskHandle_t task_handle_ = nullptr;
    SemaphoreHandle_t tx_mutex_ = nullptr;

    uint32_t rx_frames_ = 0;
    uint32_t tx_frames_ = 0;
    uint32_t rx_errors_ = 0;
    FrameReceiver receiver_;
};

} // namespace jetson

