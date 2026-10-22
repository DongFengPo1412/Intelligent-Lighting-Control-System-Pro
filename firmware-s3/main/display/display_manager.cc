#include "display_manager.h"
#include "board_led.h"
#include "audio_hal.h"
#include <esp_log.h>

namespace {
void SignalTask(void* argument) {
    bool worldline=argument!=nullptr;
    auto& audio=AudioHAL::GetInstance();
    if(worldline) {
        for(int i=0;i<5;i++)audio.PlayBeep(500+i*230,45);
    } else audio.PlayBeep(1046,180);
    vTaskDelete(nullptr);
}
void Signal(bool worldline) {
    xTaskCreate(SignalTask,"display_signal",4096,worldline?(void*)1:nullptr,2,nullptr);
}
class DisplayLock {
    SemaphoreHandle_t mutex_;
public:
    explicit DisplayLock(SemaphoreHandle_t mutex):mutex_(mutex) {
        if(!mutex_ || xSemaphoreTakeRecursive(mutex_,portMAX_DELAY)!=pdTRUE) abort();
    }
    ~DisplayLock(){xSemaphoreGiveRecursive(mutex_);}
    DisplayLock(const DisplayLock&)=delete;
    DisplayLock& operator=(const DisplayLock&)=delete;
};
}

static const char* TAG = "DisplayManager";

DisplayManager& DisplayManager::GetInstance()
{
    static DisplayManager instance;
    return instance;
}

DisplayManager::DisplayManager()
    : hal_(DisplayHAL::GetInstance()),
      current_mode_(DisplayMode::KURISU_DESK_PET),
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
    mutex_ = xSemaphoreCreateRecursiveMutex();
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
    interaction_engine_.Reset();

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
        8192,
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
        uint32_t delay_ms = 33;
        {
            DisplayLock lock(mutex_);
            DisplayMode mode = current_mode_;

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
                } else if (mode == DisplayMode::FINGERTIP_TRACKER) {
                    fingertip_tracker_.Reset();
                } else if ((int)mode >= 27) {
                    interaction_engine_.Reset();
                    if(mode==DisplayMode::WORLDLINE)Signal(true);
                }
                last_mode_ = mode;
            }

            // 根据模式路由到各个引擎
            if(mode==DisplayMode::KURISU_DESK_PET && interaction_engine_.RenderCelebration()) {
                delay_ms=16;
            } else switch (mode) {
                case DisplayMode::FINGERTIP_TRACKER:
                    delay_ms = fingertip_tracker_.RenderFrame(); break;
                case DisplayMode::LIGHT_SANDBOX:
                case DisplayMode::WORLDLINE:
                case DisplayMode::PIXEL_CANVAS:
                case DisplayMode::MUSIC_FLUID:
                case DisplayMode::AMBIENT:
                    delay_ms = interaction_engine_.Render(mode); break;
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

            // 串行同步刷新板载指示灯 (严格在主屏帧渲染后执行，杜绝并发 RMT 中断破坏 WS2812 800kHz 时序)
            BoardLed::GetInstance().UpdateAnimation();

        } // Release before sleeping so network/input tasks can proceed.
        vTaskDelay(pdMS_TO_TICKS(delay_ms) > 0 ? pdMS_TO_TICKS(delay_ms) : 1);
    }

    vTaskDelete(NULL);
}

DisplayMode DisplayManager::GetMode() const
{
    DisplayLock lock(mutex_);return current_mode_;
}

void DisplayManager::SetMode(DisplayMode mode)
{
    DisplayLock lock(mutex_);
    int number=static_cast<int>(mode);
    if(!IsDirectDisplayMode(number))return;
    if(mode!=DisplayMode::COUNTDOWN_TIMER) {
        countdown_active_=false;countdown_finished_anim_=false;
    }
    current_mode_=mode;
}

void DisplayManager::SetMode(int mode_number)
{
    SetMode(static_cast<DisplayMode>(mode_number));
}

void DisplayManager::SnakeMove(int dx, int dy)
{
    DisplayLock lock(mutex_);
    game_engine_.SnakeSetDirection(dx, dy);
}

void DisplayManager::TetrisMove(int dx)
{
    DisplayLock lock(mutex_);
    game_engine_.TetrisMove(dx);
}

void DisplayManager::TetrisRotate()
{
    DisplayLock lock(mutex_);
    game_engine_.TetrisRotate();
}

void DisplayManager::TetrisDrop()
{
    DisplayLock lock(mutex_);
    game_engine_.TetrisDrop();
}

void DisplayManager::FeedSpectrum(int beat, const int bands[16])
{
    DisplayLock lock(mutex_);
    spectrum_engine_.FeedBands(beat, bands);
}

bool DisplayManager::FeedSpectrumSerial(const char* cmd)
{
    DisplayLock lock(mutex_);
    return spectrum_engine_.ParseSerialCommand(cmd);
}

void DisplayManager::SetBrightness(uint8_t brightness)
{
    DisplayLock lock(mutex_);
    hal_.SetGlobalBrightness(brightness);
}

void DisplayManager::FeedFingertip(float x,float y,bool visible,float confidence) {
    DisplayLock lock(mutex_);fingertip_tracker_.FeedTarget(x,y,visible,confidence);
}
void DisplayManager::ConfigureFingertip(float x0,float y0,float x1,float y1,bool invert_x,bool invert_y) {
    DisplayLock lock(mutex_);
    fingertip_tracker_.SetInputWindow(x0,y0,x1,y1);fingertip_tracker_.SetInvert(invert_x,invert_y);
}
void DisplayManager::FeedHand(float x,float y,float z,bool pinch,bool visible) {
    DisplayLock lock(mutex_);interaction_engine_.FeedHand(x,y,z,pinch,visible);
}
void DisplayManager::FeedMusic(float energy,float flux,bool onset,float tempo,float phase) {
    DisplayLock lock(mutex_);interaction_engine_.FeedMusic(energy,flux,onset,tempo,phase);
}
void DisplayManager::SetCanvasFrame(const ColorRGB* colors) {
    DisplayLock lock(mutex_);
    for(int i=0;i<256;i++)interaction_engine_.SetPixel(i%16,i/16,colors[i]);
}
void DisplayManager::Celebrate() {
    DisplayLock lock(mutex_);
    if(current_mode_==DisplayMode::KURISU_DESK_PET)interaction_engine_.Celebrate();
}
void DisplayManager::SetCanvasPixel(int x,int y,ColorRGB color) {
    DisplayLock lock(mutex_);interaction_engine_.SetPixel(x,y,color);
}
void DisplayManager::ClearCanvas() {
    DisplayLock lock(mutex_);interaction_engine_.ClearCanvas();
}
void DisplayManager::SetGamma(bool enabled) {
    DisplayLock lock(mutex_);hal_.SetGammaEnabled(enabled);
}
uint32_t DisplayManager::SnapshotFrame(char* hex,size_t size) {
    DisplayLock lock(mutex_);if(size<1537)return 0;
    const char* digits="0123456789abcdef";
    const ColorRGB* frame=hal_.GetFrontBuffer();
    for(int y=0;y<16;y++)for(int x=0;x<16;x++) {
        const auto& c=frame[DisplayHAL::GetPixelIndex(x,y)];uint8_t values[]={c.r,c.g,c.b};
        for(int n=0;n<3;n++){int i=(y*16+x)*6+n*2;hex[i]=digits[values[n]>>4];hex[i+1]=digits[values[n]&15];}
    }
    hex[1536]=0;return hal_.GetFrameId();
}
void DisplayManager::FeedPet(int hour,float gaze,bool present,bool tired) {
    DisplayLock lock(mutex_);effect_engine_.FeedPet(hour,gaze,present,tired);
}
void DisplayManager::ConfigureDifficulty(float level,bool adaptive) {
    DisplayLock lock(mutex_);game_engine_.ConfigureDifficulty(level,adaptive);
}
void DisplayManager::FeedPerformance(float reaction_ms,float frustration,bool success) {
    DisplayLock lock(mutex_);game_engine_.FeedPerformance(reaction_ms,frustration,success);
}

// =========================================================================
// 智能倒计时系统 (按秒设置，256灯珠等比逐颗熄灭，精准对齐总耗时)
// =========================================================================
void DisplayManager::StartCountdown(uint32_t total_seconds)
{
    if(total_seconds>86400)return;
    if (total_seconds == 0) {
        StopCountdown();
        return;
    }

    {
        DisplayLock lock(mutex_);
        countdown_start_ms_ = get_millis();
        countdown_total_ms_ = total_seconds * 1000;
        countdown_active_ = true;
        countdown_finished_anim_ = false;
        countdown_finish_start_ms_ = 0;
        current_mode_ = DisplayMode::COUNTDOWN_TIMER;
    }

    ESP_LOGI(TAG, ">>> [倒计时启动]: 目标时长 %u 秒 (%u 毫秒), 256颗灯珠进入精确等比退行扫描",
             (unsigned int)total_seconds, (unsigned int)(total_seconds * 1000));
}

void DisplayManager::StopCountdown()
{
    {
        DisplayLock lock(mutex_);
        countdown_active_ = false;
        countdown_finished_anim_ = false;
        current_mode_ = DisplayMode::OFF;
    }
}

bool DisplayManager::IsCountdownActive() const
{
    DisplayLock lock(mutex_);
    return countdown_active_;
}

uint32_t DisplayManager::GetCountdownRemainingSeconds() const
{
    DisplayLock lock(mutex_);
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
        Signal(false);
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
