#pragma once

#include <stdint.h>
#include <stddef.h>
#include <esp_err.h>
#include <driver/gpio.h>
#include <driver/uart.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>

namespace jetson {

// 串口默认引脚与参数 (显式指定，严禁与扬声器GPIO16/灯板GPIO17/麦克风GPIO5冲突)
static constexpr uart_port_t kDefaultUartPort = UART_NUM_1;
static constexpr gpio_num_t  kDefaultRxPin    = GPIO_NUM_8; // ESP32 RX <- Jetson TX (Pin 8)
static constexpr gpio_num_t  kDefaultTxPin    = GPIO_NUM_9; // ESP32 TX -> Jetson RX (Pin 10)
static constexpr int         kDefaultBaudRate = 115200;
static constexpr size_t      kMaxLineLength   = 1024;
static constexpr const char* kProtocolVersion = "2.2.0";

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
};

} // namespace jetson
