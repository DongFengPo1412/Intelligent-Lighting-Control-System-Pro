#include "arcade_audio_task.h"
#include "arcade_sound.h"
#include "audio_hal.h"
#include <esp_timer.h>
#include <freertos/task.h>

static uint32_t NowMs(){return uint32_t(esp_timer_get_time()/1000);}
static void AudioTask(void*) {
    auto& bus=arcade::Sounds();auto& audio=AudioHAL::GetInstance();
    arcade::GameAudioStream stream(bus);
    for(;;) {
        stream.Poll(NowMs(),[&](const int16_t* pcm,unsigned count){return audio.TryPlayGamePcm(pcm,count);});
        // A single bounded attempt; actual sample deadlines govern the next write.
        // No busy-spin, long I2S wait, or unconditional extra 10ms after each write.
        vTaskDelay(1);
    }
}
bool StartArcadeAudioTask() {
    arcade::Sounds().SetClock(NowMs);
    return xTaskCreate(AudioTask,"arcade_sfx",4096,nullptr,2,nullptr)==pdPASS;
}
