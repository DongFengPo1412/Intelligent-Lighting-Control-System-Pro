#pragma once

#include <stdint.h>
#include <atomic>
#include <esp_err.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/ringbuf.h>

class CommandDispatcher {
public:
    static CommandDispatcher& GetInstance();

    // 启动后台串口指令监听任务 (默认分配至 Core 0，不与 Core 1 渲染任务争抢算力)
    esp_err_t StartSerialTask(UBaseType_t priority = 4, BaseType_t core_id = 0);

    // 解析并执行单行指令 (自动识别纯文本极速指令、旧版串口频谱流或标准 JSON)
    bool ProcessLine(const char* line, bool reply_serial = true);

    // 发送当前系统状态到上位机
    void SendStatus();

    // 麦克风音频流控
    void SetMicStreaming(bool enabled);
    bool IsMicStreaming() const { return mic_streaming_; }
    uint32_t AudioReceived() const { return audio_received_.load(); }
    uint32_t AudioPlayed() const { return audio_played_.load(); }
    uint32_t AudioDropped() const { return audio_dropped_.load(); }
    uint32_t AudioErrors() const { return audio_errors_.load(); }
    bool EnqueuePcm(const void* data,size_t bytes);
    void AbortAudio();
    uint32_t AudioStackFree() const { return audio_play_task_handle_ ? uxTaskGetStackHighWaterMark(audio_play_task_handle_) : 0; }

private:
    CommandDispatcher();
    ~CommandDispatcher();

    CommandDispatcher(const CommandDispatcher&) = delete;
    CommandDispatcher& operator=(const CommandDispatcher&) = delete;

    static void SerialTaskTrampoline(void* arg);
    void SerialTaskLoop();

    static void MicTaskTrampoline(void* arg);
    void MicTaskLoop();

    static void AudioPlayTaskTrampoline(void* arg);
    void AudioPlayTaskLoop();

    bool ProcessJsonCommand(const char* json_str, bool reply_serial);
    bool ProcessTextCommand(const char* text_str, bool reply_serial);

    TaskHandle_t task_handle_;
    TaskHandle_t mic_task_handle_;
    TaskHandle_t audio_play_task_handle_;
    RingbufHandle_t audio_ring_buf_;

    volatile bool is_running_;
    volatile bool mic_streaming_;
    std::atomic<uint32_t> audio_received_{0}, audio_played_{0}, audio_dropped_{0}, audio_errors_{0};
};
