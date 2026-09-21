#pragma once

#include "display_types.h"
#include "display_hal.h"
#include "effect_engine.h"
#include "game_engine.h"
#include "spectrum_engine.h"
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
    DisplayMode GetMode() const { return current_mode_; }

    // 游戏交互输入
    void SnakeMove(int dx, int dy);
    void TetrisMove(int dx);
    void TetrisRotate();
    void TetrisDrop();

    // 音频频谱注入
    void FeedSpectrum(int beat, const int bands[16]);
    void FeedSpectrumSerial(const char* cmd);

    // 亮度与均光补偿
    void SetBrightness(uint8_t brightness);
    void SetCompensation(bool enable);

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
