#pragma once

#include <esp_err.h>
#include <driver/gpio.h>
#include <driver/i2s_std.h>
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

    // 播放单声道 16-bit PCM (自动立体声升采样广播至左右声道，防止 MAX98357 静音)
    esp_err_t PlayMonoPcm(const int16_t* mono_samples, size_t count);

    // 从 INMP441 读取一段麦克风采样数据 (16kHz 16-bit 单声道)
    esp_err_t ReadMic(int16_t* dest_buf, size_t max_samples, size_t* samples_read, uint32_t timeout_ms = 200);

    // 麦克风通道硬件启停控制 (按需启动 DMA，防止长时间空载溢出)
    esp_err_t EnableMic(bool enable);

    // 硬件状态查询
    bool IsInitialized() const { return initialized_; }
    bool IsMicEnabled() const { return mic_enabled_; }

private:
    AudioHAL();
    ~AudioHAL();

    AudioHAL(const AudioHAL&) = delete;
    AudioHAL& operator=(const AudioHAL&) = delete;

    i2s_chan_handle_t tx_chan_; // MAX98357A 输出通道
    i2s_chan_handle_t rx_chan_; // INMP441 输入通道
    bool initialized_;
    bool mic_enabled_;
};
