#ifndef BOARD_LED_H
#define BOARD_LED_H

#include <esp_err.h>
#include <driver/gpio.h>
#include <led_strip.h>

enum class BoardLedMode {
    OFF = 0,
    BREATHE_PAIRING = 1,  // 上电配对搜寻: 板载单颗 LED 呼吸律动 (模拟中阶配对态)
    SOLID_GREEN = 2,      // 配对成功: 板载 LED 常亮绿色
    ACTIVE_INTERACT = 3   // 唤醒交互中: 青绿灵动微呼吸
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
};

#endif // BOARD_LED_H
