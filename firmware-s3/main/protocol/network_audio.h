#pragma once
#include <stdint.h>
#include <stddef.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>

// Pro PCM transport (not XiaoZhi's Opus/WebSocket wire format).
// KAP1 | kind:u8 | length:u16 BE | payload. PCM16LE mono at 16000 Hz.
class NetworkAudio {
public:
    static NetworkAudio& GetInstance();
    bool Start();
    bool SendMic(const int16_t* samples,size_t count);
    bool Connected() const { return ready_; }
private:
    int client_=-1;
    volatile bool ready_=false;
    SemaphoreHandle_t tx_=nullptr;
    bool Send(uint8_t kind,const void* data,size_t bytes);
    static void Task(void* arg);
    void Run();
};
