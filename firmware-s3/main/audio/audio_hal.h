#pragma once

#include <esp_err.h>
#include <driver/gpio.h>
#include <driver/i2s_std.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <cstdint>
#include <cstddef>

class AudioHAL {
public:
    static AudioHAL& GetInstance() {
        static AudioHAL instance;
        return instance;
    }

    // 初始化 I2S 硬件通道 (INMP441 麦克风输入 + MAX98357A 扬声器输出)
    esp_err_t Init(
        gpio_num_t mic_ws   = GPIO_NUM_4,
        gpio_num_t mic_sck  = GPIO_NUM_5,
        gpio_num_t mic_din  = GPIO_NUM_6,
        gpio_num_t spk_dout = GPIO_NUM_7,
        gpio_num_t spk_bclk = GPIO_NUM_15,
        gpio_num_t spk_lrck = GPIO_NUM_16
    );

    // 播放指定频率与时长的硬件提示音 (正弦波合成，用于开机自检与指令反馈)
    esp_err_t PlayBeep(uint32_t freq_hz = 880, uint32_t duration_ms = 300);

    // 播放一段 PCM 16-bit 音频数据
    esp_err_t PlayPcm(const int16_t* pcm_data, size_t samples, size_t* bytes_written = nullptr);

    // 播放单声道 16-bit PCM (根据音量系数映射至 32-bit，对齐中阶 NoAudioCodecSimplex)
    esp_err_t PlayMonoPcm(const int16_t* mono_samples, size_t count);

    // 从 INMP441 读取一段麦克风采样数据 (16kHz 16-bit 单声道)
    esp_err_t ReadMic(int16_t* dest_buf, size_t max_samples, size_t* samples_read, uint32_t timeout_ms = 200);

    // 扬声器音量控制 (0 - 100，默认 70，采用平方律 pow(vol/100, 2) * 65536 映射)
    void SetVolume(int volume_percent);
    int GetVolume() const { return output_volume_; }

    // 扬声器通道动态启停 (自动休眠管理，彻底消除空闲时的 RMT 与地回路电磁杂音)
    esp_err_t EnableSpeaker(bool enable);
    bool IsSpeakerEnabled() const { return speaker_enabled_; }

    // 麦克风通道硬件启停控制 (按需启动 DMA，防止长时间空载溢出)
    esp_err_t EnableMic(bool enable);
    bool IsMicEnabled() const { return mic_enabled_; }

    // 硬件状态查询
    bool IsInitialized() const { return initialized_; }

private:
    AudioHAL();
    ~AudioHAL();

    AudioHAL(const AudioHAL&) = delete;
    AudioHAL& operator=(const AudioHAL&) = delete;

    void ResetSpeakerTimer();

    i2s_chan_handle_t tx_chan_; // MAX98357A 输出通道
    i2s_chan_handle_t rx_chan_; // INMP441 输入通道
    esp_timer_handle_t spk_power_timer_; // 扬声器自动休眠定时器
    SemaphoreHandle_t playback_mutex_;
    int32_t tx_buffer_[480]; // Protected by playback_mutex_; never on a task's stack.
    int output_volume_;
    int64_t volume_factor_;
    bool initialized_;
    bool speaker_enabled_;
    bool mic_enabled_;
};
