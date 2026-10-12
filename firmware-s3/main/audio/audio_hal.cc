#include "audio_hal.h"
#include <esp_log.h>
#include <cmath>
#include <vector>
#include <cstring>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static const char* TAG = "AudioHAL";

AudioHAL::AudioHAL() : tx_chan_(nullptr), rx_chan_(nullptr), initialized_(false) {}

AudioHAL::~AudioHAL() {
    if (tx_chan_) {
        i2s_channel_disable(tx_chan_);
        i2s_del_channel(tx_chan_);
    }
    if (rx_chan_) {
        i2s_channel_disable(rx_chan_);
        i2s_del_channel(rx_chan_);
    }
}

esp_err_t AudioHAL::Init(
    gpio_num_t mic_ws,
    gpio_num_t mic_sck,
    gpio_num_t mic_din,
    gpio_num_t spk_dout,
    gpio_num_t spk_bclk,
    gpio_num_t spk_lrck
) {
    if (initialized_) {
        ESP_LOGW(TAG, "AudioHAL 已经初始化，跳过重复初始化");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "正在初始化 I2S 硬件音频驱动...");
    ESP_LOGI(TAG, "  - INMP441 麦克风: WS=%d, SCK=%d, DIN=%d", mic_ws, mic_sck, mic_din);
    ESP_LOGI(TAG, "  - MAX98357 扬声器: DOUT=%d, BCLK=%d, LRCK=%d", spk_dout, spk_bclk, spk_lrck);

    // 1. 初始化 MAX98357A 扬声器输出通道 (TX)
    i2s_chan_config_t tx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    tx_chan_cfg.dma_desc_num = 6;
    tx_chan_cfg.dma_frame_num = 240;
    tx_chan_cfg.auto_clear = true;

    esp_err_t ret = i2s_new_channel(&tx_chan_cfg, &tx_chan_, nullptr);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "创建 I2S TX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    i2s_std_config_t tx_std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = spk_bclk,
            .ws = spk_lrck,
            .dout = spk_dout,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    ret = i2s_channel_init_std_mode(tx_chan_, &tx_std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "初始化 I2S TX 标准模式失败: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = i2s_channel_enable(tx_chan_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "启动 I2S TX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    // 2. 初始化 INMP441 麦克风输入通道 (RX)
    i2s_chan_config_t rx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    rx_chan_cfg.dma_desc_num = 6;
    rx_chan_cfg.dma_frame_num = 240;

    ret = i2s_new_channel(&rx_chan_cfg, nullptr, &rx_chan_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "创建 I2S RX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    // INMP441 输出为 24-bit 数据对齐在 32-bit slot
    i2s_std_config_t rx_std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = mic_sck,
            .ws = mic_ws,
            .dout = I2S_GPIO_UNUSED,
            .din = mic_din,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    ret = i2s_channel_init_std_mode(rx_chan_, &rx_std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "初始化 I2S RX 标准模式失败: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = i2s_channel_enable(rx_chan_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "启动 I2S RX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "I2S 硬件音频全双工驱动初始化成功！");

    // 开机自检提示音 (双音阶清脆开机蜂鸣 880Hz -> 1320Hz)
    PlayBeep(880, 120);
    PlayBeep(1320, 160);

    return ESP_OK;
}

esp_err_t AudioHAL::PlayBeep(uint32_t freq_hz, uint32_t duration_ms) {
    if (!tx_chan_) return ESP_ERR_INVALID_STATE;

    const uint32_t sample_rate = 16000;
    size_t total_samples = (sample_rate * duration_ms) / 1000;
    const float two_pi = 6.28318530718f;
    float phase_step = (two_pi * freq_hz) / sample_rate;

    // 每次合成 256 个立体声帧
    const size_t chunk_frames = 256;
    int16_t buffer[chunk_frames * 2]; // 左+右声道

    float phase = 0.0f;
    size_t samples_generated = 0;

    while (samples_generated < total_samples) {
        size_t frames_this_round = std::min(chunk_frames, total_samples - samples_generated);
        for (size_t i = 0; i < frames_this_round; ++i) {
            // 平滑正弦波，峰值幅度设定在 0.25 防止小喇叭爆音破音
            int16_t val = (int16_t)(std::sin(phase) * 8000.0f);
            buffer[i * 2]     = val; // L
            buffer[i * 2 + 1] = val; // R
            phase += phase_step;
            if (phase >= two_pi) phase -= two_pi;
        }

        size_t bytes_written = 0;
        esp_err_t ret = i2s_channel_write(
            tx_chan_,
            buffer,
            frames_this_round * 2 * sizeof(int16_t),
            &bytes_written,
            pdMS_TO_TICKS(100)
        );
        if (ret != ESP_OK) {
            ESP_LOGW(TAG, "I2S 写入超时或失败: %s", esp_err_to_name(ret));
            break;
        }
        samples_generated += frames_this_round;
    }

    return ESP_OK;
}

esp_err_t AudioHAL::PlayPcm(const int16_t* pcm_data, size_t samples, size_t* bytes_written) {
    if (!tx_chan_ || !pcm_data) return ESP_ERR_INVALID_STATE;
    return i2s_channel_write(
        tx_chan_,
        pcm_data,
        samples * sizeof(int16_t),
        bytes_written,
        pdMS_TO_TICKS(200)
    );
}

esp_err_t AudioHAL::PlayMonoPcm(const int16_t* mono_samples, size_t count) {
    if (!tx_chan_ || !mono_samples) return ESP_ERR_INVALID_STATE;
    const size_t chunk_size = 256;
    int16_t stereo_buf[chunk_size * 2];
    size_t written_total = 0;

    while (written_total < count) {
        size_t frames = std::min(chunk_size, count - written_total);
        for (size_t i = 0; i < frames; i++) {
            int16_t s = mono_samples[written_total + i];
            stereo_buf[i * 2]     = s;
            stereo_buf[i * 2 + 1] = s;
        }
        size_t bytes_out = 0;
        i2s_channel_write(tx_chan_, stereo_buf, frames * 2 * sizeof(int16_t), &bytes_out, pdMS_TO_TICKS(100));
        written_total += frames;
    }
    return ESP_OK;
}

esp_err_t AudioHAL::ReadMic(int16_t* dest_buf, size_t max_samples, size_t* samples_read, uint32_t timeout_ms) {
    if (!rx_chan_ || !dest_buf) return ESP_ERR_INVALID_STATE;

    // INMP441 为 32-bit slot，高 24 位为有效数据，右移 14 位映射为 16-bit 线性 PCM
    const size_t raw_buffer_size = 256;
    int32_t raw_data[raw_buffer_size];
    size_t bytes_read = 0;

    esp_err_t ret = i2s_channel_read(
        rx_chan_,
        raw_data,
        sizeof(raw_data),
        &bytes_read,
        pdMS_TO_TICKS(timeout_ms)
    );

    if (ret != ESP_OK) {
        if (samples_read) *samples_read = 0;
        return ret;
    }

    size_t items = bytes_read / sizeof(int32_t);
    size_t to_copy = std::min(items, max_samples);

    for (size_t i = 0; i < to_copy; ++i) {
        // INMP441 24-bit MSB 规整化转 16-bit
        dest_buf[i] = (int16_t)(raw_data[i] >> 14);
    }

    if (samples_read) {
        *samples_read = to_copy;
    }

    return ESP_OK;
}
