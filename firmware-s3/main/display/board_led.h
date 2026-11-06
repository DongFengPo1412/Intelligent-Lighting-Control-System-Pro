#ifndef BOARD_LED_H
#define BOARD_LED_H

#include <esp_err.h>
#include <driver/gpio.h>
#include <led_strip.h>

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

enum class BoardLedMode {
    OFF = 0,
    BREATHE_PAIRING = 1,  // 兼容旧命令名：中阶配网蓝灯500ms明灭
    SOLID_GREEN = 2,      // 语音播发中: 翠绿常亮 (中阶 kDeviceStateSpeaking)
    ACTIVE_INTERACT = 3,  // 思考运算中: 青蓝流光微呼吸 (中阶 kDeviceStateConnecting)
    LISTENING_LOW = 4,    // 待命监听中: 微光暗红 (中阶 kDeviceStateListening, Low Brightness)
    LISTENING_HIGH = 5,   // 人声捕获中: 鲜艳鲜红 (中阶 kDeviceStateListening, High Brightness - VAD Active)
    SOLID_BLUE = 6,       // 连接语音通道：中阶蓝灯常亮
    STARTING = 7,         // 中阶启动：蓝灯100ms明灭
    INITIALIZING = 8      // 本地语音初始化：对应中阶Activating绿灯500ms明灭
};

class BoardLed {
public:
    static BoardLed& GetInstance();

    esp_err_t Init(gpio_num_t gpio_pin = GPIO_NUM_48);
    void SetMode(BoardLedMode mode);
    BoardLedMode GetMode() const { return current_mode_; }

    // 随同主显示引擎同步串行刷新，避免高优先级定时器中断破坏 16x16 矩阵的 800kHz RMT 传输时序
    void UpdateAnimation();

private:
    BoardLed();
    ~BoardLed();

    led_strip_handle_t led_strip_;
    BoardLedMode current_mode_;
    uint32_t step_count_;
    int64_t state_started_us_;
    bool blink_on_;
    bool is_initialized_;
    SemaphoreHandle_t mutex_;
};

#endif // BOARD_LED_H
