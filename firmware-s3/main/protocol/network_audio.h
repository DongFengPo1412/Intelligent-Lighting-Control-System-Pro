#pragma once
#include <stdint.h>
#include <stddef.h>
#include <netinet/in.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <atomic>
namespace pcm_transport {class PcmTxQueue;}

// Pro PCM transport (not XiaoZhi's Opus/WebSocket wire format).
// KAP1 | kind:u8 | length:u16 BE | payload. PCM16LE mono at 16000 Hz.
class NetworkAudio {
public:
    static NetworkAudio& GetInstance();
    bool Start();
    bool SendMic(const int16_t* samples,size_t count);
    bool Connected() const { return ready_; }
    bool CreateAudioTicket(struct in_addr ip, char* out_ticket_64);
    bool CheckAudioTicket(const char* token, struct in_addr ip);
    static constexpr size_t kMaxAudioRx = 2048;
    uint32_t TxQueued() const {return queued_.load();}
    uint32_t TxBusy() const {return busy_.load();}
    uint32_t MicDropped() const {return mic_dropped_.load();}
    uint32_t TxErrors() const {return tx_errors_.load();}
    uint32_t TxStackFree() const {return tx_stack_free_.load();}
private:
    int client_=-1;
    std::atomic<bool> ready_{false};
    std::atomic<bool> running_{false};
    SemaphoreHandle_t tx_=nullptr;
    pcm_transport::PcmTxQueue* queue_=nullptr;
    std::atomic<uint32_t> queued_{0},busy_{0},mic_dropped_{0},tx_errors_{0};
    std::atomic<uint32_t> tx_stack_free_{0};
    char audio_ticket_[65] = {};
    struct in_addr ticket_ip_ = {};
    uint32_t ticket_expire_ms_ = 0;
    uint8_t rx_payload_[kMaxAudioRx] = {};
    bool Send(uint8_t kind,const void* data,size_t bytes);
    bool FlushPending();
    bool FlushLocked();
    void SyncStatsLocked();
    void FailLocked(const char* reason,int error);
    static void Task(void* arg);
    void Run();
};
