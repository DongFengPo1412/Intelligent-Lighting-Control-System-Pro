#ifndef BOARD_LED_H
#define BOARD_LED_H

#include <esp_err.h>
#include <driver/gpio.h>
#include <led_strip.h>

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

enum class BoardLedMode {
    OFF = 0,
    BREATHE_PAIRING = 1,  // 上电配对搜寻: 幽蓝呼吸律动 (中阶 kDeviceStateWifiConfiguring/Starting)
    SOLID_GREEN = 2,      // 语音播发中: 翠绿常亮 (中阶 kDeviceStateSpeaking)
    ACTIVE_INTERACT = 3,  // 思考运算中: 青蓝流光微呼吸 (中阶 kDeviceStateConnecting)
    LISTENING_LOW = 4,    // 待命监听中: 微光暗红 (中阶 kDeviceStateListening, Low Brightness)
    LISTENING_HIGH = 5,   // 人声捕获中: 鲜艳鲜红 (中阶 kDeviceStateListening, High Brightness - VAD Active)
    SOLID_BLUE = 6        // 配对握手确立: 幽蓝常亮 (中阶 kDeviceStateConnecting)
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
    bool is_initialized_;
    SemaphoreHandle_t mutex_;
};

#endif // BOARD_LED_H
