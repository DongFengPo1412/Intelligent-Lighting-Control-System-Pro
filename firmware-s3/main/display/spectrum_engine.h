#pragma once

#include "display_types.h"
#include "display_hal.h"

class SpectrumEngine {
public:
    SpectrumEngine();
    ~SpectrumEngine() = default;

    // 重置频谱状态
    void Reset();

    // 数据输入接口 1: 原始数组注入 (后续用于板载麦克风 FFT 分析直接调用)
    void FeedBands(int beat, const int bands[16]);

    // 数据输入接口 2: 兼容中阶 "f,beat,b0,b1..." 串口字符串格式
    void ParseSerialCommand(const char* cmd);

    // 渲染一帧频谱画面 (返回渲染耗时/建议延时)
    uint32_t RenderFrame();

private:
    int bands_[16];
    float fall_bands_[16]; // 重力滤波器下落高度
    int is_beat_;
    uint32_t last_feed_time_;
};
