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
      is_running_(false)
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
