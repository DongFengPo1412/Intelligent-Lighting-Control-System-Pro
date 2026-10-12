#pragma once

#include <stdint.h>
#include <esp_err.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

class CommandDispatcher {
public:
    static CommandDispatcher& GetInstance();

    // 启动后台串口指令监听任务 (默认分配至 Core 0，不与 Core 1 渲染任务争抢算力)
    esp_err_t StartSerialTask(UBaseType_t priority = 4, BaseType_t core_id = 0);

    // 解析并执行单行指令 (自动识别纯文本极速指令、旧版串口频谱流或标准 JSON)
    void ProcessLine(const char* line);

    // 发送当前系统状态到上位机
    void SendStatus();

    // 麦克风音频流控
    void SetMicStreaming(bool enabled) { mic_streaming_ = enabled; }
    bool IsMicStreaming() const { return mic_streaming_; }

private:
    CommandDispatcher();
    ~CommandDispatcher();

    CommandDispatcher(const CommandDispatcher&) = delete;
    CommandDispatcher& operator=(const CommandDispatcher&) = delete;

    static void SerialTaskTrampoline(void* arg);
    void SerialTaskLoop();

    static void MicTaskTrampoline(void* arg);
    void MicTaskLoop();

    bool ProcessJsonCommand(const char* json_str);
    bool ProcessTextCommand(const char* text_str);

    TaskHandle_t task_handle_;
    TaskHandle_t mic_task_handle_;
    bool is_running_;
    bool mic_streaming_;
};
