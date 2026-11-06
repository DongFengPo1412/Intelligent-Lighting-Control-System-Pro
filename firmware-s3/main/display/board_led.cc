#include "board_led.h"
#include <esp_log.h>
#include <math.h>
#include <esp_timer.h>
#include "board_led_profile.h"

static const char* TAG = "BoardLed";

BoardLed& BoardLed::GetInstance()
{
    static BoardLed instance;
    return instance;
}

BoardLed::BoardLed()
    : led_strip_(nullptr),
      current_mode_(BoardLedMode::OFF),
      step_count_(0),
      state_started_us_(0),
      blink_on_(false),
      is_initialized_(false),
      mutex_(nullptr)
{
    mutex_ = xSemaphoreCreateMutex();
}

BoardLed::~BoardLed()
{
    if (mutex_) {
        vSemaphoreDelete(mutex_);
        mutex_ = nullptr;
    }
    if (led_strip_) {
        led_strip_del(led_strip_);
        led_strip_ = nullptr;
    }
}

esp_err_t BoardLed::Init(gpio_num_t gpio_pin)
{
    if (is_initialized_) return ESP_OK;

    ESP_LOGI(TAG, "Initializing onboard RGB LED on GPIO %d...", gpio_pin);

    led_strip_config_t strip_config = {
        .strip_gpio_num = gpio_pin,
        .max_leds = 1,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
        .flags = {
            .invert_out = false,
        }
    };

    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000,
        .mem_block_symbols = 48,
        .flags = {
            .with_dma = false,
        }
    };

    esp_err_t ret = led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create onboard led_strip: %s", esp_err_to_name(ret));
        return ret;
    }

    led_strip_clear(led_strip_);
    is_initialized_ = true;
    SetMode(BoardLedMode::STARTING);
    return ESP_OK;
}

void BoardLed::SetMode(BoardLedMode mode)
{
    if (!led_strip_ || !is_initialized_) return;

    if (mutex_ && xSemaphoreTake(mutex_, pdMS_TO_TICKS(50)) != pdTRUE) {
        return;
    }
    if (current_mode_ == mode) {
        if (mutex_) xSemaphoreGive(mutex_);
        return;
    }

    current_mode_ = mode;
    step_count_ = 0;
    state_started_us_ = esp_timer_get_time();
    blink_on_ = true;

    if (current_mode_ == BoardLedMode::SOLID_GREEN) {
        // 语音播发中: 翠绿色常亮 (中阶 kDeviceStateSpeaking)
        led_strip_set_pixel(led_strip_, 0, 0, mid_led::kDefault, 0);
        led_strip_refresh(led_strip_);
    } else if (current_mode_ == BoardLedMode::SOLID_BLUE) {
        // 配对确立: 幽蓝常亮 (中阶 kDeviceStateConnecting)
        led_strip_set_pixel(led_strip_, 0, 0, 0, mid_led::kDefault);
        led_strip_refresh(led_strip_);
    } else if (current_mode_ == BoardLedMode::LISTENING_LOW) {
        // 待命监听中: 微光暗红 (中阶 kDeviceStateListening, Low Brightness)
        led_strip_set_pixel(led_strip_, 0, mid_led::kLow, 0, 0);
        led_strip_refresh(led_strip_);
    } else if (current_mode_ == BoardLedMode::LISTENING_HIGH) {
        // 人声捕获中: 鲜艳鲜红 (中阶 kDeviceStateListening, High Brightness - VAD Active)
        led_strip_set_pixel(led_strip_, 0, mid_led::kHigh, 0, 0);
        led_strip_refresh(led_strip_);
    } else if (current_mode_ == BoardLedMode::OFF) {
        led_strip_clear(led_strip_);
    } else if (mode == BoardLedMode::STARTING || mode == BoardLedMode::BREATHE_PAIRING || mode == BoardLedMode::INITIALIZING) {
        const bool green = mode == BoardLedMode::INITIALIZING;
        led_strip_set_pixel(led_strip_, 0, 0, green ? mid_led::kDefault : 0, green ? 0 : mid_led::kDefault);
        led_strip_refresh(led_strip_);
    }

    if (mutex_) {
        xSemaphoreGive(mutex_);
    }
}

void BoardLed::UpdateAnimation()
{
    if (!led_strip_ || !is_initialized_) return;
    if (mutex_ && xSemaphoreTake(mutex_, pdMS_TO_TICKS(10)) != pdTRUE) {
        return;
    }

    if (current_mode_ == BoardLedMode::BREATHE_PAIRING || current_mode_ == BoardLedMode::STARTING || current_mode_ == BoardLedMode::INITIALIZING) {
        const unsigned interval = current_mode_ == BoardLedMode::STARTING ? 100 : 500;
        const bool on = mid_led::BlinkOn(uint64_t(esp_timer_get_time() - state_started_us_), interval);
        if (on != blink_on_) {
            blink_on_ = on;
            const bool green = current_mode_ == BoardLedMode::INITIALIZING;
            const uint8_t level = on ? mid_led::kDefault : 0;
            led_strip_set_pixel(led_strip_, 0, 0, green ? level : 0, green ? 0 : level);
            led_strip_refresh(led_strip_);
        }
    }
    else if (current_mode_ == BoardLedMode::ACTIVE_INTERACT) {
        // 思考运算中：青白灵动微呼吸 (周期约 1.2s = 40 steps)
        step_count_++;
        float rad = (float)(step_count_ % 40) * (2.0f * M_PI / 40.0f);
        float norm = (sinf(rad) + 1.0f) * 0.5f;
        uint32_t g = 15 + (uint32_t)(norm * 25.0f);
        uint32_t b = 15 + (uint32_t)(norm * 30.0f);
        uint32_t r = (uint32_t)(norm * 8.0f);
        led_strip_set_pixel(led_strip_, 0, r, g, b);
        led_strip_refresh(led_strip_);
    }

    if (mutex_) {
        xSemaphoreGive(mutex_);
    }
}
