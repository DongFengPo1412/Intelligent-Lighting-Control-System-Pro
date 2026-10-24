#pragma once

#include "display_types.h"
#include "display_hal.h"
#include "effect_engine.h"
#include "game_engine.h"
#include "spectrum_engine.h"
#include "fingertip_tracker.h"
#include "interaction_engine.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>

class DisplayManager {
public:
    static DisplayManager& GetInstance();

    // 初始化硬件与所有引擎
    esp_err_t Init(gpio_num_t gpio_pin = GPIO_NUM_17);

    // 启动 FreeRTOS 独立渲染后台任务
    esp_err_t StartTask(UBaseType_t priority = 5, BaseType_t core_id = 1);

    // 模式切换与查询 (线程安全)
    void SetMode(DisplayMode mode);
    void SetMode(int mode_number);
    DisplayMode GetMode() const;

    // 游戏交互输入
    void SnakeMove(int dx, int dy);
    void TetrisMove(int dx);
    void TetrisRotate();
    void TetrisDrop();

    // 音频频谱注入
    void FeedSpectrum(int beat, const int bands[16]);
    bool FeedSpectrumSerial(const char* cmd);

    // 整板统一亮度
    void SetBrightness(uint8_t brightness);
    void FeedFingertip(float x,float y,bool visible,float confidence);
    void ConfigureFingertip(float x0,float y0,float x1,float y1,bool invert_x,bool invert_y);
    void FeedHand(float x,float y,float z,bool pinch,bool visible);
    void FeedMusic(float energy,float flux,bool onset,float tempo,float phase=0,const float* bands=nullptr);
    void Celebrate();
    void SetCanvasPixel(int x,int y,ColorRGB color);
    void SetCanvasFrame(const ColorRGB* colors);
    void ClearCanvas();
    uint32_t SnapshotFrame(char* hex, size_t size);
    void SetGamma(bool enabled);
    void FeedPet(int hour,float gaze,bool present,bool tired);
    void ConfigureDifficulty(float level,bool adaptive);
    void FeedPerformance(float reaction_ms,float frustration,bool success);

    // 智能倒计时系统 (按秒设置，256灯珠等比逐颗熄灭，精准对齐总耗时)
    void StartCountdown(uint32_t total_seconds);
    void StopCountdown();
    bool IsCountdownActive() const;
    uint32_t GetCountdownRemainingSeconds() const;

    // 获取底层组件 (高级扩展用)
    DisplayHAL& GetHAL() { return hal_; }
    EffectEngine& GetEffectEngine() { return effect_engine_; }
    GameEngine& GetGameEngine() { return game_engine_; }
    SpectrumEngine& GetSpectrumEngine() { return spectrum_engine_; }

private:
    DisplayManager();
    ~DisplayManager();

    DisplayManager(const DisplayManager&) = delete;
    DisplayManager& operator=(const DisplayManager&) = delete;

    static void DisplayTaskTrampoline(void* arg);
    void DisplayTaskLoop();
    uint32_t RenderCountdownTimer();

    DisplayHAL& hal_;
    EffectEngine effect_engine_;
    GameEngine game_engine_;
    SpectrumEngine spectrum_engine_;
    FingertipTracker fingertip_tracker_;
    InteractionEngine interaction_engine_;

    DisplayMode current_mode_;
    DisplayMode last_mode_;
    SemaphoreHandle_t mutex_;
    TaskHandle_t task_handle_;
    bool is_running_;

    // 智能倒计时状态机
    uint32_t countdown_start_ms_;
    uint32_t countdown_total_ms_;
    bool countdown_active_;
    bool countdown_finished_anim_;
    uint32_t countdown_finish_start_ms_;
};
