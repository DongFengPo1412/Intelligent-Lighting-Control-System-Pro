#include "display_manager.h"
#include <esp_log.h>

static const char* TAG = "DisplayManager";

DisplayManager& DisplayManager::GetInstance()
{
    static DisplayManager instance;
    return instance;
}

DisplayManager::DisplayManager()
    : hal_(DisplayHAL::GetInstance()),
      current_mode_(DisplayMode::RAINBOW_WAVE),
      last_mode_(DisplayMode::OFF),
      mutex_(nullptr),
      task_handle_(nullptr),
      is_running_(false),
      countdown_start_ms_(0),
      countdown_total_ms_(0),
      countdown_active_(false),
      countdown_finished_anim_(false),
      countdown_finish_start_ms_(0)
{
    mutex_ = xSemaphoreCreateMutex();
}

DisplayManager::~DisplayManager()
{
    is_running_ = false;
    if (task_handle_) {
        vTaskDelete(task_handle_);
        task_handle_ = nullptr;
    }
    if (mutex_) {
        vSemaphoreDelete(mutex_);
        mutex_ = nullptr;
    }
}

esp_err_t DisplayManager::Init(gpio_num_t gpio_pin)
{
    esp_err_t ret = hal_.Init(gpio_pin);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "HAL Init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    effect_engine_.Reset();
    game_engine_.InitSnake();
    game_engine_.InitTetris();
    spectrum_engine_.Reset();

    ESP_LOGI(TAG, "DisplayManager initialized.");
    return ESP_OK;
}

esp_err_t DisplayManager::StartTask(UBaseType_t priority, BaseType_t core_id)
{
    if (is_running_) return ESP_OK;

    is_running_ = true;
    BaseType_t ret = xTaskCreatePinnedToCore(
        DisplayTaskTrampoline,
        "display_task",
        4096,
        this,
        priority,
        &task_handle_,
        core_id
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create display task!");
        is_running_ = false;
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Display task started on Core %d (priority %d)", (int)core_id, (int)priority);
    return ESP_OK;
}

void DisplayManager::DisplayTaskTrampoline(void* arg)
{
    DisplayManager* manager = static_cast<DisplayManager*>(arg);
    manager->DisplayTaskLoop();
}

void DisplayManager::DisplayTaskLoop()
{
    ESP_LOGI(TAG, "Display task loop entered.");

    while (is_running_) {
        DisplayMode mode;
        if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(10)) == pdTRUE) {
            mode = current_mode_;
            xSemaphoreGive(mutex_);
        } else {
            mode = current_mode_;
        }

        // 模式切换瞬间的初始化工作 (复刻中阶 changeToMode)
        if (mode != last_mode_) {
            ESP_LOGI(TAG, ">>> Mode switched from %d to %d", (int)last_mode_, (int)mode);
            hal_.Clear();
            if (mode == DisplayMode::SNAKE_GAME) {
                game_engine_.InitSnake();
            } else if (mode == DisplayMode::TETRIS_GAME) {
                game_engine_.InitTetris();
            } else if (mode == DisplayMode::AUDIO_SPECTRUM) {
                spectrum_engine_.Reset();
            }
            last_mode_ = mode;
        }

        uint32_t delay_ms = 33;

        // 根据模式路由到各个引擎
        switch (mode) {
            case DisplayMode::SNAKE_GAME:
                delay_ms = game_engine_.RunSnake();
                if (game_engine_.IsSnakeGameOver()) {
                    SetMode(DisplayMode::SNAKE_SCORE);
                }
                break;

            case DisplayMode::SNAKE_SCORE:
                game_engine_.DrawScore(game_engine_.GetSnakeScore());
                delay_ms = 100;
                break;

            case DisplayMode::TETRIS_GAME:
                delay_ms = game_engine_.RunTetris();
                if (game_engine_.IsTetrisGameOver()) {
                    SetMode(DisplayMode::TETRIS_SCORE);
                }
                break;

            case DisplayMode::TETRIS_SCORE:
                game_engine_.DrawScore(game_engine_.GetTetrisScore());
                delay_ms = 100;
                break;

            case DisplayMode::AUDIO_SPECTRUM:
                delay_ms = spectrum_engine_.RenderFrame();
                break;

            case DisplayMode::COUNTDOWN_TIMER:
                delay_ms = RenderCountdownTimer();
                break;

            default:
                // 基础特效与表情包
                delay_ms = effect_engine_.RenderFrame(mode);
                break;
        }

        vTaskDelay(pdMS_TO_TICKS(delay_ms > 5 ? delay_ms : 5));
    }

    vTaskDelete(NULL);
}

void DisplayManager::SetMode(DisplayMode mode)
{
    if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(50)) == pdTRUE) {
        current_mode_ = mode;
        xSemaphoreGive(mutex_);
    }
}

void DisplayManager::SetMode(int mode_number)
{
    SetMode(static_cast<DisplayMode>(mode_number));
}

void DisplayManager::SnakeMove(int dx, int dy)
{
    game_engine_.SnakeSetDirection(dx, dy);
}

void DisplayManager::TetrisMove(int dx)
{
    game_engine_.TetrisMove(dx);
}

void DisplayManager::TetrisRotate()
{
    game_engine_.TetrisRotate();
}

void DisplayManager::TetrisDrop()
{
    game_engine_.TetrisDrop();
}

void DisplayManager::FeedSpectrum(int beat, const int bands[16])
{
    spectrum_engine_.FeedBands(beat, bands);
}

void DisplayManager::FeedSpectrumSerial(const char* cmd)
{
    spectrum_engine_.ParseSerialCommand(cmd);
}

void DisplayManager::SetBrightness(uint8_t brightness)
{
    hal_.SetGlobalBrightness(brightness);
}

void DisplayManager::SetCompensation(bool enable)
{
    hal_.SetCompensationEnabled(enable);
}

// =========================================================================
// 智能倒计时系统 (按秒设置，256灯珠等比逐颗熄灭，精准对齐总耗时)
// =========================================================================
void DisplayManager::StartCountdown(uint32_t total_seconds)
{
    if (total_seconds == 0) {
        StopCountdown();
        return;
    }

    if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(50)) == pdTRUE) {
        countdown_start_ms_ = get_millis();
        countdown_total_ms_ = total_seconds * 1000;
        countdown_active_ = true;
        countdown_finished_anim_ = false;
        countdown_finish_start_ms_ = 0;
        current_mode_ = DisplayMode::COUNTDOWN_TIMER;
        xSemaphoreGive(mutex_);
    }

    ESP_LOGI(TAG, ">>> [倒计时启动]: 目标时长 %u 秒 (%u 毫秒), 256颗灯珠进入精确等比退行扫描",
             (unsigned int)total_seconds, (unsigned int)(total_seconds * 1000));
}

void DisplayManager::StopCountdown()
{
    if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(50)) == pdTRUE) {
        countdown_active_ = false;
        countdown_finished_anim_ = false;
        current_mode_ = DisplayMode::OFF;
        xSemaphoreGive(mutex_);
    }
}

bool DisplayManager::IsCountdownActive() const
{
    return countdown_active_;
}

uint32_t DisplayManager::GetCountdownRemainingSeconds() const
{
    if (!countdown_active_) return 0;
    uint32_t now = get_millis();
    uint32_t elapsed = now - countdown_start_ms_;
    if (elapsed >= countdown_total_ms_) return 0;
    return (countdown_total_ms_ - elapsed + 999) / 1000;
}

uint32_t DisplayManager::RenderCountdownTimer()
{
    uint32_t now = get_millis();

    // 1. 如果倒计时已完成，播放终结脉冲呼吸闪烁动画 (提示用户时间到)
    if (countdown_finished_anim_) {
        uint32_t finish_elapsed = now - countdown_finish_start_ms_;
        if (finish_elapsed < 1500) {
            // 2次柔和脉冲呼吸闪烁
            uint8_t pulse = beatsin8(80, 0, 255);
            hal_.FillSolid(ColorRGB(pulse, pulse, pulse));
            hal_.Show();
            return 33;
        } else {
            // 动画完成，自动关屏或复位
            countdown_active_ = false;
            countdown_finished_anim_ = false;
            SetMode(DisplayMode::OFF);
            hal_.Clear();
            hal_.Show();
            return 33;
        }
    }

    // 2. 正常倒计时流逝计算
    uint32_t elapsed_ms = now - countdown_start_ms_;

    // 检查是否恰好耗尽设定时间
    if (elapsed_ms >= countdown_total_ms_) {
        countdown_finished_anim_ = true;
        countdown_finish_start_ms_ = now;
        ESP_LOGI(TAG, ">>> [倒计时结束]: 耗时精准对齐，播放到时全屏脉冲提示！");
        return 33;
    }

    // 剩余进度比例 1.0f -> 0.0f
    float remaining_ratio = 1.0f - ((float)elapsed_ms / (float)countdown_total_ms_);
    float active_float = remaining_ratio * 256.0f;
    int active_leds = (int)active_float;
    if (active_leds < 0) active_leds = 0;
    if (active_leds > 256) active_leds = 256;

    // 3. 动态情感色彩计算：根据剩余时间百分比无级渐变
    ColorRGB current_color;
    if (remaining_ratio > 0.5f) {
        // 100% ~ 50%: 青碧绿 -> 翡翠翠绿 (平静、充裕)
        float t = (1.0f - remaining_ratio) / 0.5f;
        current_color = ColorRGB::Lerp(ColorRGB(0, 255, 180), ColorRGB(0, 255, 50), t);
    } else if (remaining_ratio > 0.2f) {
        // 50% ~ 20%: 翡翠绿 -> 暖调琥珀橙 (提醒、过半)
        float t = (0.5f - remaining_ratio) / 0.3f;
        current_color = ColorRGB::Lerp(ColorRGB(0, 255, 50), ColorRGB(255, 160, 0), t);
    } else {
        // 20% ~ 0%: 警示烈焰红 (伴随心跳呼吸频闪，压迫感)
        uint8_t pulse = beatsin8(140, 140, 255);
        current_color = ColorRGB(pulse, 0, (uint8_t)(pulse * 0.1f));
    }

    // 4. 256 颗灯珠蛇形逐颗熄灭拓扑
    // k 从 0 到 255：
    // k < active_leds 点亮，k >= active_leds 熄灭
    hal_.Clear();

    for (int k = 0; k < active_leds; k++) {
        int y = k / 16;
        int x = (y % 2 == 0) ? (k % 16) : (15 - (k % 16));

        // 如果是正在过渡的临界灯珠，按亚像素浮点进行亮度羽化，使熄灭极其丝滑
        if (k == active_leds - 1) {
            float frac = active_float - (float)active_leds;
            uint8_t scale = (uint8_t)(frac * 80.0f + 20.0f);
            hal_.SetPixel(x, y, current_color.scale(scale));
        } else {
            hal_.SetPixel(x, y, current_color);
        }
    }

    hal_.Show();
    return 33; // 约 30 FPS 高帧率渲染
}
