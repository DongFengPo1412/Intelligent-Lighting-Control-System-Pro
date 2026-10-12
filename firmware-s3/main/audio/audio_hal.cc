#include "audio_hal.h"
#include <esp_log.h>
#include <cmath>
#include <vector>
#include <cstring>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static const char* TAG = "AudioHAL";

AudioHAL::AudioHAL() : tx_chan_(nullptr), rx_chan_(nullptr), initialized_(false), mic_enabled_(false) {}

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

    // 1. 初始化 MAX98357A 扬声器输出通道 (TX) 绑定至 I2S_NUM_0
    i2s_chan_config_t tx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    tx_chan_cfg.dma_desc_num = 6;
    tx_chan_cfg.dma_frame_num = 240;
    tx_chan_cfg.auto_clear_after_cb = true;

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

    // 2. 初始化 INMP441 麦克风输入通道 (RX) 显式绑定至 I2S_NUM_1
    i2s_chan_config_t rx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    rx_chan_cfg.dma_desc_num = 6;
    rx_chan_cfg.dma_frame_num = 240;

    ret = i2s_new_channel(&rx_chan_cfg, nullptr, &rx_chan_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "创建 I2S RX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    // INMP441 32-bit slot, MONO, LEFT mask (标准单工收音配置)
    i2s_std_config_t rx_std_cfg = {
        .clk_cfg = {
            .sample_rate_hz = 16000,
            .clk_src = I2S_CLK_SRC_DEFAULT,
            .mclk_multiple = I2S_MCLK_MULTIPLE_256,
        },
        .slot_cfg = {
            .data_bit_width = I2S_DATA_BIT_WIDTH_32BIT,
            .slot_bit_width = I2S_SLOT_BIT_WIDTH_AUTO,
            .slot_mode = I2S_SLOT_MODE_MONO,
            .slot_mask = I2S_STD_SLOT_LEFT,
            .ws_width = I2S_DATA_BIT_WIDTH_32BIT,
            .ws_pol = false,
            .bit_shift = true,
        },
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

    // 默认保持 RX 待命，录音开启时再启动 DMA，防止长时间溢出
    mic_enabled_ = false;
    initialized_ = true;
    ESP_LOGI(TAG, "I2S 硬件音频全双工驱动初始化成功 (TX 已激活，RX 待命)");

    // 开机自检提示音 (双音阶清脆开机蜂鸣 880Hz -> 1320Hz)
    PlayBeep(880, 120);
    PlayBeep(1320, 160);

    return ESP_OK;
}

esp_err_t AudioHAL::EnableMic(bool enable) {
    if (!rx_chan_) return ESP_ERR_INVALID_STATE;
    if (enable == mic_enabled_) return ESP_OK;
    esp_err_t ret = ESP_OK;
    if (enable) {
        ret = i2s_channel_enable(rx_chan_);
        if (ret == ESP_OK) {
            mic_enabled_ = true;
            ESP_LOGI(TAG, "INMP441 硬件麦克风 DMA 已激活");
        } else {
            ESP_LOGE(TAG, "启用 INMP441 失败: %s", esp_err_to_name(ret));
        }
    } else {
        ret = i2s_channel_disable(rx_chan_);
        mic_enabled_ = false;
        ESP_LOGI(TAG, "INMP441 硬件麦克风 DMA 已挂起休眠");
    }
    return ret;
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

    const size_t raw_buffer_size = 256;
    int32_t bit32_buffer[raw_buffer_size];
    size_t samples_to_read = std::min(max_samples, raw_buffer_size);
    size_t bytes_read = 0;

    esp_err_t ret = i2s_channel_read(
        rx_chan_,
        bit32_buffer,
        samples_to_read * sizeof(int32_t),
        &bytes_read,
        pdMS_TO_TICKS(timeout_ms)
    );

    if (ret != ESP_OK) {
        if (samples_read) *samples_read = 0;
        return ret;
    }

    size_t count = bytes_read / sizeof(int32_t);
    for (size_t i = 0; i < count; ++i) {
        int32_t value = bit32_buffer[i] >> 12;
        dest_buf[i] = (value > INT16_MAX) ? INT16_MAX : (value < -INT16_MAX) ? -INT16_MAX : (int16_t)value;
    }

    if (samples_read) {
        *samples_read = count;
    }

    return ESP_OK;
}
