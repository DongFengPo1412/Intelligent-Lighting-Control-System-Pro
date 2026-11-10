#include "network_audio.h"
#include "command_dispatcher.h"
#include "network_auth.h"
#include "wifi_manager.h"
#include "pcm_frame_writer.h"
#include "wifi_audio_power.h"
#include "pcm_tx_queue.h"
#include <freertos/task.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <unistd.h>
#include <string.h>
#include <esp_log.h>
#include <errno.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <new>
#include <sys/select.h>

namespace {
const char hello[]="pcm16le/16000/mono/v2";
uint32_t now_ms(){return static_cast<uint32_t>(esp_timer_get_time()/1000);}
bool read_all(int fd,void* output,size_t length) {
    auto* p=(uint8_t*)output;while(length){int n=recv(fd,p,length,0);if(n<=0)return false;p+=n;length-=n;}return true;
}
}
NetworkAudio& NetworkAudio::GetInstance(){static NetworkAudio instance;return instance;}
bool NetworkAudio::Start(){
    bool expected=false;
    if(!running_.compare_exchange_strong(expected,true))return true;
    if(!tx_)tx_=xSemaphoreCreateMutex();
    if(!tx_){running_=false;ESP_LOGE("NetworkAudio","PCM mutex allocation failed");return false;}
    if(!queue_){
        void* memory=heap_caps_malloc(sizeof(pcm_transport::PcmTxQueue),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
        if(!memory){running_=false;ESP_LOGE("NetworkAudio","PCM PSRAM queue allocation failed");return false;}
        queue_=new(memory) pcm_transport::PcmTxQueue;
        ESP_LOGI("NetworkAudio","PCM TX queue: %u bytes PSRAM",unsigned(sizeof(pcm_transport::PcmTxQueue)));
    }
    if(xTaskCreatePinnedToCore(Task,"wifi_pcm",8192,this,4,nullptr,0)!=pdPASS){
        running_=false;ESP_LOGE("NetworkAudio","PCM worker creation failed");return false;
    }
    return true;
}
void NetworkAudio::Task(void* arg){
    auto* audio=(NetworkAudio*)arg;audio->Run();audio->ready_=false;audio->running_=false;vTaskDelete(nullptr);
}
void NetworkAudio::SyncStatsLocked(){
    queued_=queue_->Queued();busy_=queue_->Busy();mic_dropped_=queue_->DroppedSamples();
}

bool NetworkAudio::CreateAudioTicket(struct in_addr ip, char* out_ticket_64) {
    if (!out_ticket_64) return false;
    if (!tx_) tx_ = xSemaphoreCreateMutex();
    if (tx_) xSemaphoreTake(tx_, portMAX_DELAY);
    bool ok = ticket_guard_.CreateTicket(ip, out_ticket_64, now_ms(), [](void* buf, size_t n) {
        esp_fill_random(buf, n);
    });
    if (tx_) xSemaphoreGive(tx_);
    return ok;
}

bool NetworkAudio::CheckAudioTicket(const char* token, struct in_addr ip) {
    if (!token || strlen(token) != 64) return false;
    if (!tx_) return false;
    xSemaphoreTake(tx_, portMAX_DELAY);
    bool match = ticket_guard_.CheckAndConsume(token, ip, now_ms());
    xSemaphoreGive(tx_);
    return match;
}

void NetworkAudio::FailLocked(const char* reason,int error){
    ready_=false;++tx_errors_;queue_->Clear();SyncStatsLocked();
    if(client_>=0)shutdown(client_,SHUT_RDWR);
    ESP_LOGW("NetworkAudio","PCM connection closed: %s (errno=%d)",reason,error);
}
bool NetworkAudio::FlushLocked(){
    const int fd=client_;
    int write_error=0;
    const auto result=queue_->Flush(now_ms(),[fd,&write_error](const uint8_t* p,size_t length){
        const int count=send(fd,p,length,MSG_DONTWAIT);
        if(count>0)return pcm_transport::TxWrite{static_cast<size_t>(count),pcm_transport::TxState::Progress};
        write_error=count==0?ECONNRESET:errno;
        if(count<0&&(errno==EAGAIN||errno==EWOULDBLOCK||errno==EINTR))
            return pcm_transport::TxWrite{0,pcm_transport::TxState::Blocked};
        return pcm_transport::TxWrite{0,pcm_transport::TxState::Fault};
    });
    SyncStatsLocked();
    if(result==pcm_transport::FlushResult::Fault || result==pcm_transport::FlushResult::Expired){
        FailLocked(result==pcm_transport::FlushResult::Expired?"TX queue expired":"socket write failed",
                   result==pcm_transport::FlushResult::Expired?ETIMEDOUT:write_error);
        return false;
    }
    return true;
}
bool NetworkAudio::FlushPending(){
    if(xSemaphoreTake(tx_,pdMS_TO_TICKS(10))!=pdTRUE)return ready_.load();
    const bool ok=client_>=0&&ready_&&FlushLocked();
    xSemaphoreGive(tx_);return ok;
}
bool NetworkAudio::Send(uint8_t kind,const void* data,size_t bytes){
    if(!data||!bytes||bytes>2048||!tx_)return false;
    if(xSemaphoreTake(tx_,pdMS_TO_TICKS(100))!=pdTRUE)return false;
    const int fd=client_;
    bool ok=false;
    if(fd>=0 && kind==4){
        // Initial hello has no microphone/control backlog yet.
        ok=pcm_transport::WriteFrame(kind,data,bytes,
            [fd](const uint8_t* p,size_t length){return send(fd,p,length,0);},
            [this]{FailLocked("hello write failed",errno);});
    }else if(fd>=0&&ready_){
        ok=queue_->Enqueue(kind,data,bytes,now_ms());SyncStatsLocked();
        if(!ok&&kind==5)FailLocked("control echo queue full",0);
        if(ready_&&!FlushLocked())ok=false;
    }
    xSemaphoreGive(tx_);return ok;
}
bool NetworkAudio::SendMic(const int16_t* data,size_t count){
    return data&&count&&count<=1024&&ready_&&Send(2,data,count*2);
}
void NetworkAudio::Run(){
    int server=socket(AF_INET,SOCK_STREAM,IPPROTO_IP);
    if(server<0){ESP_LOGE("NetworkAudio","PCM socket creation failed: errno=%d",errno);return;}
    int reuse=1;setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&reuse,sizeof(reuse));
    sockaddr_in address={};address.sin_family=AF_INET;address.sin_port=htons(8889);address.sin_addr.s_addr=htonl(INADDR_ANY);
    if(bind(server,(sockaddr*)&address,sizeof(address))<0||listen(server,1)<0){
        ESP_LOGE("NetworkAudio","PCM bind/listen failed: errno=%d",errno);close(server);return;
    }
    ESP_LOGI("NetworkAudio","PCM listener ready on TCP 8889");
    for(;;){
        sockaddr_in client_addr = {};
        socklen_t client_len = sizeof(client_addr);
        int fd = accept(server, (sockaddr*)&client_addr, &client_len);
        if(fd<0){vTaskDelay(pdMS_TO_TICKS(100));continue;}
        // PCM chunks are 15-32 ms long. Do not hold a small header/payload
        // behind Nagle while waiting for the peer's delayed acknowledgement.
        int no_delay=1;setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&no_delay,sizeof(no_delay));
        timeval timeout={2,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
        timeout={0,200000};setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
        uint8_t header[7];
        uint8_t handshake_payload[256];
        // Authenticate BEFORE assigning the mic/output connection. Unpaired peers
        // cannot capture audio or displace the active authenticated connection.
        if (!read_all(fd, header, sizeof(header))) { close(fd); continue; }
        size_t first_size = 0;
        pcm_transport::ValidateFrameHeader(header, first_size);
        const size_t prefix = strlen(hello);
        bool valid_hello = false;
        char token[65] = {};
        if (header[4] == 4 && first_size < sizeof(handshake_payload) && read_all(fd, handshake_payload, first_size)) {
            handshake_payload[first_size] = '\0';
            if (pcm_transport::ValidateHandshakePayload(header, handshake_payload, first_size, token)) {
                if (NetworkAuth::GetInstance().Check(token) || CheckAudioTicket(token, client_addr.sin_addr)) {
                    valid_hello = true;
                }
            }
        }
        if (!valid_hello) { close(fd); continue; }
        pcm_transport::WifiAudioPowerSession power;
        const esp_err_t power_result=power.Activate();
        if(power_result!=ESP_OK){
            ESP_LOGW("NetworkAudio","PCM performance policy failed (%d)",power_result);
            close(fd);continue;
        }
        ESP_LOGI("NetworkAudio","Authenticated PCM active: Wi-Fi power save NONE");
        xSemaphoreTake(tx_,portMAX_DELAY);queue_->Clear();SyncStatsLocked();client_=fd;xSemaphoreGive(tx_);
        if (!Send(4, hello, prefix)) {
            xSemaphoreTake(tx_,portMAX_DELAY);client_=-1;close(fd);xSemaphoreGive(tx_);continue;
        }
        ready_=true;
        uint32_t last_rx=now_ms();
        uint32_t last_stack_sample=0;
        while(ready_){
            if(!FlushPending())break;
            if(uint32_t(now_ms()-last_stack_sample)>=1000){
                tx_stack_free_=static_cast<uint32_t>(uxTaskGetStackHighWaterMark(nullptr));
                last_stack_sample=now_ms();
            }
            fd_set readable;FD_ZERO(&readable);FD_SET(fd,&readable);
            timeval poll={0,10000};
            const int selected=select(fd+1,&readable,nullptr,nullptr,&poll);
            if(selected<0)break;
            if(!selected){if(uint32_t(now_ms()-last_rx)>2000)break;continue;}
            if(!read_all(fd,header,sizeof(header)))break;
            size_t bytes = 0;
            const auto frame_status = pcm_transport::ValidateFrameHeader(header, bytes);
            if(frame_status != pcm_transport::ParseFrameStatus::OkAudio &&
               frame_status != pcm_transport::ParseFrameStatus::OkControlEcho) break;
            if(!read_all(fd,rx_payload_,bytes)) break;
            last_rx=now_ms();
            if(frame_status == pcm_transport::ParseFrameStatus::OkAudio && ready_){
                CommandDispatcher::GetInstance().EnqueuePcm(rx_payload_,bytes);
            } else if(frame_status == pcm_transport::ParseFrameStatus::OkControlEcho && ready_){
                if(!Send(5,rx_payload_,bytes))break;
            } else break;
        }
        ready_=false;xSemaphoreTake(tx_,portMAX_DELAY);shutdown(fd,SHUT_RDWR);close(fd);client_=-1;
        queue_->Clear();SyncStatsLocked();xSemaphoreGive(tx_);
    }
}
