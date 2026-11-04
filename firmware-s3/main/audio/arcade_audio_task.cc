#include "arcade_audio_task.h"
#include "arcade_sound.h"
#include "audio_hal.h"
#include <esp_timer.h>
#include <freertos/task.h>

static uint32_t NowMs(){return uint32_t(esp_timer_get_time()/1000);}
static void AudioTask(void*) {
    auto& bus=arcade::Sounds();auto& audio=AudioHAL::GetInstance();
    int16_t pcm[160]; // Recheck priority every 10ms chunk; physical DMA latency is unmeasured.
    for(;;) {
        arcade::SoundEvent event;
        if(!bus.Pop(event)){vTaskDelay(pdMS_TO_TICKS(10));continue;}
        auto tone=arcade::ToneFor(event);bool complete=true;
        for(unsigned offset=0;offset<tone.duration_ms*16;offset+=160) {
            if(!bus.Enabled() || !bus.Volume() || bus.Generation()!=event.generation){complete=false;break;}
            for(unsigned i=0;i<160;++i)pcm[i]=arcade::SoundSample(event,offset+i,bus.Volume());
            if(audio.TryPlayGamePcm(pcm,160)!=ESP_OK){++bus.preempted;complete=false;break;}
            vTaskDelay(pdMS_TO_TICKS(10)>0?pdMS_TO_TICKS(10):1);
        }
        if(complete)++bus.played;
    }
}
bool StartArcadeAudioTask() {
    arcade::Sounds().SetClock(NowMs);
    return xTaskCreate(AudioTask,"arcade_sfx",4096,nullptr,2,nullptr)==pdPASS;
}
