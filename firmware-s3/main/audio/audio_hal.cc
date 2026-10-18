#include "audio_hal.h"
#include <esp_log.h>
#include <cmath>
#include <vector>
#include <cstring>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static const char* TAG = "AudioHAL";

static void SpeakerTimerCallback(void* arg) {
    AudioHAL* hal = static_cast<AudioHAL*>(arg);
    hal->EnableSpeaker(false);
}

AudioHAL::AudioHAL()
    : tx_chan_(nullptr),
      rx_chan_(nullptr),
      spk_power_timer_(nullptr),
      output_volume_(70),
      volume_factor_(32112),
      initialized_(false),
      speaker_enabled_(false),
      mic_enabled_(false) {}

AudioHAL::~AudioHAL() {
    if (spk_power_timer_) {
        esp_timer_stop(spk_power_timer_);
        esp_timer_delete(spk_power_timer_);
    }
    if (tx_chan_) {
        i2s_channel_disable(tx_chan_);
        i2s_del_channel(tx_chan_);
    }
    if (rx_chan_) {
        i2s_channel_disable(rx_chan_);
        i2s_del_channel(rx_chan_);
    }
}

void AudioHAL::SetVolume(int volume_percent) {
    if (volume_percent < 0) volume_percent = 0;
    if (volume_percent > 100) volume_percent = 100;
    output_volume_ = volume_percent;
    // 平方律音量映射: 对齐中阶项目 NoAudioCodec: pow(vol / 100.0, 2) * 65536
    double ratio = (double)output_volume_ / 100.0;
    volume_factor_ = (int64_t)(ratio * ratio * 65536.0);
    ESP_LOGI(TAG, ">>> [音量设定]: %d%% (volume_factor=%lld)", output_volume_, (long long)volume_factor_);
}

esp_err_t AudioHAL::EnableSpeaker(bool enable) {
    if (!tx_chan_) return ESP_ERR_INVALID_STATE;
    if (enable == speaker_enabled_) return ESP_OK;

    esp_err_t ret = ESP_OK;
    if (enable) {
        ret = i2s_channel_enable(tx_chan_);
        if (ret == ESP_OK) {
            speaker_enabled_ = true;
            ESP_LOGI(TAG, "MAX98357A 硬件输出已唤醒 (BCLK 激活)");
        }
    } else {
        ret = i2s_channel_disable(tx_chan_);
        if (ret == ESP_OK) {
            speaker_enabled_ = false;
            ESP_LOGI(TAG, "MAX98357A 进入自动静音休眠 (BCLK 停止，彻底杜绝电磁底噪)");
        }
    }
    return ret;
}

void AudioHAL::ResetSpeakerTimer() {
    if (spk_power_timer_) {
        esp_timer_stop(spk_power_timer_);
        // 800ms 无新数据写入则自动关断 BCLK，让 MAX98357A 彻底进入零底噪硬件休眠
        esp_timer_start_once(spk_power_timer_, 800 * 1000);
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

    // 1. 初始化 MAX98357A 扬声器输出通道 (TX) 绑定至 I2S_NUM_0 (对齐中阶 NoAudioCodecSimplex)
    // 采用 12 个 DMA 描述符 (180ms 深度抗欠载缓冲)
    i2s_chan_config_t tx_chan_cfg = {
        .id = I2S_NUM_0,
        .role = I2S_ROLE_MASTER,
        .dma_desc_num = 12,
        .dma_frame_num = 240,
        .auto_clear_after_cb = true,
        .auto_clear_before_cb = false,
        .intr_priority = 0,
    };

    esp_err_t ret = i2s_new_channel(&tx_chan_cfg, &tx_chan_, nullptr);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "创建 I2S TX 通道失败: %s", esp_err_to_name(ret));
        return ret;
    }

    // 采用标准飞利浦 Philips 格式 (left_align = false, bit_shift = true)
    i2s_std_config_t tx_std_cfg = {
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
            .left_align = false,
            .big_endian = false,
            .bit_order_lsb = false,
        },
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

    // 默认保持 TX 待命休眠，不常驻振荡 BCLK，彻底阻断空闲状态下的 WS2812 与供电高频电磁啸叫
    speaker_enabled_ = false;

    // 创建扬声器自动休眠管理定时器
    esp_timer_create_args_t timer_args = {
        .callback = SpeakerTimerCallback,
        .arg = this,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "spk_power_timer",
        .skip_unhandled_events = true,
    };
    esp_timer_create(&timer_args, &spk_power_timer_);

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
            .left_align = false,
            .big_endian = false,
            .bit_order_lsb = false,
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
    ESP_LOGI(TAG, "I2S 硬件驱动初始化成功 (对齐中阶 70%% 音量 + 自动休眠静音防啸叫)");

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

    EnableSpeaker(true);
    ResetSpeakerTimer();

    const uint32_t sample_rate = 16000;
    size_t total_samples = (sample_rate * duration_ms) / 1000;
    const float two_pi = 6.28318530718f;
    float phase_step = (two_pi * freq_hz) / sample_rate;

    const size_t chunk_frames = 240;
    int32_t buffer[chunk_frames]; // 32-bit 单声道

    float phase = 0.0f;
    size_t samples_generated = 0;

    // 提示音量按当前音量系数换算
    float amp = (float)volume_factor_ * 0.25f; // 提示音保持适中温和，严防破音

    while (samples_generated < total_samples) {
        size_t frames_this_round = std::min(chunk_frames, total_samples - samples_generated);
        for (size_t i = 0; i < frames_this_round; ++i) {
            int32_t val = (int32_t)(std::sin(phase) * amp);
            buffer[i] = val;
            phase += phase_step;
            if (phase >= two_pi) phase -= two_pi;
        }

        size_t bytes_written = 0;
        esp_err_t ret = i2s_channel_write(
            tx_chan_,
            buffer,
            frames_this_round * sizeof(int32_t),
            &bytes_written,
            portMAX_DELAY
        );
        if (ret != ESP_OK) {
            ESP_LOGW(TAG, "I2S 写入超时或失败: %s", esp_err_to_name(ret));
            break;
        }
        samples_generated += frames_this_round;
    }

    ResetSpeakerTimer();
    return ESP_OK;
}

esp_err_t AudioHAL::PlayPcm(const int16_t* pcm_data, size_t samples, size_t* bytes_written) {
    return PlayMonoPcm(pcm_data, samples);
}

esp_err_t AudioHAL::PlayMonoPcm(const int16_t* mono_samples, size_t count) {
    if (!tx_chan_ || !mono_samples || count == 0) return ESP_ERR_INVALID_STATE;

    EnableSpeaker(true);
    ResetSpeakerTimer();

    const size_t chunk_size = 240;
    int32_t bit32_buf[chunk_size];
    size_t written_total = 0;

    // 采用对齐中阶 NoAudioCodec 的音量平方律映射:
    const int64_t v_factor = volume_factor_;

    while (written_total < count) {
        size_t frames = std::min(chunk_size, count - written_total);
        for (size_t i = 0; i < frames; i++) {
            int64_t temp = (int64_t)mono_samples[written_total + i] * v_factor;
            if (temp > INT32_MAX) temp = INT32_MAX;
            else if (temp < INT32_MIN) temp = INT32_MIN;
            bit32_buf[i] = (int32_t)temp;
        }
        size_t bytes_out = 0;
        i2s_channel_write(tx_chan_, bit32_buf, frames * sizeof(int32_t), &bytes_out, portMAX_DELAY);
        written_total += frames;
    }

    ResetSpeakerTimer();
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
