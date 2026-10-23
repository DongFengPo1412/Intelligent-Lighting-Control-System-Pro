#include "network_audio.h"
#include "command_dispatcher.h"
#include <freertos/task.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <unistd.h>
#include <string.h>

namespace {
const char hello[]="pcm16le/16000/mono/v1";
bool read_all(int fd,void* output,size_t length) {
    auto* p=(uint8_t*)output;while(length){int n=recv(fd,p,length,0);if(n<=0)return false;p+=n;length-=n;}return true;
}
bool write_all(int fd,const void* input,size_t length) {
    auto* p=(const uint8_t*)input;while(length){int n=send(fd,p,length,0);if(n<=0)return false;p+=n;length-=n;}return true;
}
}
NetworkAudio& NetworkAudio::GetInstance(){static NetworkAudio instance;return instance;}
bool NetworkAudio::Start(){
    if(tx_)return true;
    tx_=xSemaphoreCreateMutex();if(!tx_)return false;
    return xTaskCreatePinnedToCore(Task,"wifi_pcm",8192,this,4,nullptr,0)==pdPASS;
}
void NetworkAudio::Task(void* arg){((NetworkAudio*)arg)->Run();vTaskDelete(nullptr);}
bool NetworkAudio::Send(uint8_t kind,const void* data,size_t bytes){
    if(bytes>2048||!tx_)return false;
    if(xSemaphoreTake(tx_,pdMS_TO_TICKS(100))!=pdTRUE)return false;
    uint8_t header[]={'K','A','P','1',kind,(uint8_t)(bytes>>8),(uint8_t)bytes};
    bool ok=client_>=0&&write_all(client_,header,sizeof(header))&&write_all(client_,data,bytes);
    xSemaphoreGive(tx_);return ok;
}
bool NetworkAudio::SendMic(const int16_t* data,size_t count){return ready_&&Send(2,data,count*2);}
void NetworkAudio::Run(){
    int server=socket(AF_INET,SOCK_STREAM,IPPROTO_IP);
    if(server<0)return;
    int reuse=1;setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&reuse,sizeof(reuse));
    sockaddr_in address={};address.sin_family=AF_INET;address.sin_port=htons(8889);address.sin_addr.s_addr=htonl(INADDR_ANY);
    if(bind(server,(sockaddr*)&address,sizeof(address))<0||listen(server,1)<0){close(server);return;}
    for(;;){
        int fd=accept(server,nullptr,nullptr);if(fd<0){vTaskDelay(pdMS_TO_TICKS(100));continue;}
        // PCM chunks are 15-32 ms long. Do not hold a small header/payload
        // behind Nagle while waiting for the peer's delayed acknowledgement.
        int no_delay=1;setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&no_delay,sizeof(no_delay));
        timeval timeout={2,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
        timeout={0,200000};setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
        xSemaphoreTake(tx_,portMAX_DELAY);client_=fd;xSemaphoreGive(tx_);
        uint8_t header[7],payload[2048];
        while(read_all(fd,header,sizeof(header))){
            size_t bytes=((size_t)header[5]<<8)|header[6];
            if(memcmp(header,"KAP1",4)||bytes>sizeof(payload)||!bytes||!read_all(fd,payload,bytes))break;
            if(header[4]==4 && bytes==strlen(hello) && !memcmp(payload,hello,bytes)){
                if(!Send(4,hello,strlen(hello)))break;
                ready_=true;
            } else if(header[4]==1 && ready_ && bytes%2==0){
                CommandDispatcher::GetInstance().EnqueuePcm(payload,bytes);
            } else if(header[4]==5 && ready_){
                if(!Send(5,payload,bytes))break;
            } else break;
        }
        ready_=false;xSemaphoreTake(tx_,portMAX_DELAY);shutdown(fd,SHUT_RDWR);close(fd);client_=-1;xSemaphoreGive(tx_);
    }
}
