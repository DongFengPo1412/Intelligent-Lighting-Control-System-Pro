#include "audio_hal.h"
#include "audio_preferences.h"
#include "audio_sample_format.h"
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
      playback_mutex_(xSemaphoreCreateMutex()),
      settings_mutex_(xSemaphoreCreateMutex()),
      output_volume_(70),
      volume_factor_(32112),
      saved_volume_(-1),
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
    if (playback_mutex_) vSemaphoreDelete(playback_mutex_);
    if (settings_mutex_) vSemaphoreDelete(settings_mutex_);
}

esp_err_t AudioHAL::SetVolume(int volume_percent) {
    if (volume_percent < 0) volume_percent = 0;
    if (volume_percent > 100) volume_percent = 100;
    if (!settings_mutex_ || xSemaphoreTake(settings_mutex_, pdMS_TO_TICKS(500)) != pdTRUE)
        return ESP_ERR_TIMEOUT;
    output_volume_.store(volume_percent);
    volume_factor_.store(audio_pcm::VolumeFactor(volume_percent));
    esp_err_t error = ESP_OK;
    if (saved_volume_ != volume_percent) {
        error = audio_preferences::Save(volume_percent);
        if (error == ESP_OK) saved_volume_ = volume_percent;
    }
    xSemaphoreGive(settings_mutex_);
    if (error != ESP_OK) ESP_LOGW(TAG, "Volume applied in RAM but not saved: %s", esp_err_to_name(error));
    ESP_LOGI(TAG, ">>> [音量设定]: %d%% (saved=%s)", volume_percent, error == ESP_OK ? "yes" : "no");
    return error;
}

esp_err_t AudioHAL::EnableSpeaker(bool enable) {
    if (!tx_chan_) return ESP_ERR_INVALID_STATE;
    if (enable == speaker_enabled_) return ESP_OK;
    // Timer callbacks must not disable DMA during a write or block the timer task.
    if (!enable && xSemaphoreTake(playback_mutex_, 0) != pdTRUE) return ESP_OK;

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
    if (!enable) xSemaphoreGive(playback_mutex_);
    return ret;
}

void AudioHAL::ResetSpeakerTimer() {
    if (spk_power_timer_) {
        esp_timer_stop(spk_power_timer_);
        // Mid AudioService uses a 15-second output idle timeout.
        esp_timer_start_once(spk_power_timer_, 15000 * 1000);
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
    // Init has not started playback/capture yet. Release partial DMA resources so
    // a failed audio peripheral does not starve the display/control fallback.
    auto failed = [&](esp_err_t error) {
        if (spk_power_timer_) { esp_timer_delete(spk_power_timer_); spk_power_timer_ = nullptr; }
        if (rx_chan_) { i2s_del_channel(rx_chan_); rx_chan_ = nullptr; }
        if (tx_chan_) { i2s_del_channel(tx_chan_); tx_chan_ = nullptr; }
        mic_enabled_ = speaker_enabled_ = false;
        return error;
    };
    if (!playback_mutex_ || !settings_mutex_) return failed(ESP_ERR_NO_MEM);

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
        return failed(ret);
    }

    // Mid NoAudioCodecSimplex: mono, 32-bit left slot, Philips bit shift.
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
            .left_align = true,
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
        return failed(ret);
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
    ret = esp_timer_create(&timer_args, &spk_power_timer_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Speaker power timer creation failed: %s", esp_err_to_name(ret));
        return failed(ret);
    }

    // 2. 初始化 INMP441 麦克风输入通道 (RX) 显式绑定至 I2S_NUM_1
    i2s_chan_config_t rx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    rx_chan_cfg.dma_desc_num = 6;
    rx_chan_cfg.dma_frame_num = 240;

    ret = i2s_new_channel(&rx_chan_cfg, nullptr, &rx_chan_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "创建 I2S RX 通道失败: %s", esp_err_to_name(ret));
        return failed(ret);
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
            .left_align = true,
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
        return failed(ret);
    }

    // INMP441 硬件 DMA 通道初始化完毕后常驻使能，杜绝频繁开启关断导致 DMA 悬垂与死锁超时
    ret = i2s_channel_enable(rx_chan_);
    if (ret != ESP_OK) {
        mic_enabled_ = false;
        ESP_LOGE(TAG, "INMP441 RX enable failed: %s; audio initialization incomplete", esp_err_to_name(ret));
        return failed(ret);
    }
    mic_enabled_ = true;
    ESP_LOGI(TAG, "INMP441 硬件麦克风 DMA 通道常驻使能就绪");
    const auto volume = audio_preferences::Load();
    output_volume_.store(volume.value);
    volume_factor_.store(audio_pcm::VolumeFactor(volume.value));
    saved_volume_ = volume.saved ? volume.value : -1;
    initialized_ = true;
    ESP_LOGI(TAG, "I2S ready: mono left slot, 16kHz, volume=%d%% (%s)", volume.value,
             volume.saved ? "restored from NVS" : "default; no saved valid volume");

    return ESP_OK;
}

esp_err_t AudioHAL::EnableMic(bool enable) {
    if (enable && (!initialized_ || !rx_chan_)) return ESP_ERR_INVALID_STATE;
    mic_enabled_ = enable;
    return ESP_OK;
}

esp_err_t AudioHAL::PlayBeep(uint32_t freq_hz, uint32_t duration_ms) {
    if (!freq_hz || freq_hz > 8000 || !duration_ms || duration_ms > 1000) return ESP_ERR_INVALID_ARG;
    // Use the same bounded, serialized PCM path as speech playback. Keep the
    // waveform off the UDP task's limited stack and the notification gentle.
    const size_t count = 16000 * duration_ms / 1000;
    std::vector<int16_t> samples(count);
    for (size_t i = 0; i < count; ++i) {
        samples[i] = (int16_t)(std::sin(6.28318530718f * freq_hz * i / 16000.0f) * 6000.0f);
    }
    return PlayMonoPcm(samples.data(), samples.size());
}

esp_err_t AudioHAL::PlayPcm(const int16_t* pcm_data, size_t samples, size_t* bytes_written) {
    return PlayMonoPcm(pcm_data, samples);
}

esp_err_t AudioHAL::PlayMonoPcm(const int16_t* mono_samples, size_t count) {
    NotifyExternalPlayback();
    if (!initialized_ || !tx_chan_ || !mono_samples || count == 0) return ESP_ERR_INVALID_STATE;
    if (!playback_mutex_ || xSemaphoreTake(playback_mutex_, pdMS_TO_TICKS(500)) != pdTRUE) return ESP_ERR_TIMEOUT;
    if (spk_power_timer_) esp_timer_stop(spk_power_timer_);
    esp_err_t ret = EnableSpeaker(true);
    if (ret != ESP_OK) {
        xSemaphoreGive(playback_mutex_);
        return ret;
    }

    const size_t chunk_size = 240;
    int32_t* bit32_buf = tx_buffer_;
    size_t written_total = 0;

    // 采用对齐中阶 NoAudioCodec 的音量平方律映射:
    const uint32_t v_factor = volume_factor_.load();

    while (written_total < count) {
        size_t frames = std::min(chunk_size, count - written_total);
        audio_pcm::PackMono(mono_samples + written_total, frames, v_factor, bit32_buf);
        size_t bytes_out = 0;
        ret = i2s_channel_write(tx_chan_, bit32_buf, frames * audio_pcm::kI2sBytesPerSample, &bytes_out, 200);
        if (ret != ESP_OK || bytes_out != frames * audio_pcm::kI2sBytesPerSample) {
            if (ret == ESP_OK) ret = ESP_ERR_TIMEOUT;
            ESP_LOGW(TAG, "I2S playback incomplete: %s (%u bytes)", esp_err_to_name(ret), (unsigned)bytes_out);
            break;
        }
        written_total += frames;
    }

    ResetSpeakerTimer();
    xSemaphoreGive(playback_mutex_);
    return ret;
}

void AudioHAL::NotifyExternalPlayback() {
    playback_priority_.External(uint32_t(esp_timer_get_time()/1000));
}

arcade::AudioWriteResult AudioHAL::TryPlayGamePcm(const int16_t* data,size_t count) {
    using State=arcade::AudioWriteState;
    if(!data || !count || count>160 || !initialized_ || !tx_chan_)return {0,State::Fault};
    if(!playback_priority_.GameAllowed(uint32_t(esp_timer_get_time()/1000)))return {0,State::Preempted};
    if(!playback_mutex_ || xSemaphoreTake(playback_mutex_,0)!=pdTRUE)return {0,State::Busy};
    arcade::AudioWriteResult result{0,State::Preempted};
    if(playback_priority_.GameAllowed(uint32_t(esp_timer_get_time()/1000))) {
        if(spk_power_timer_)esp_timer_stop(spk_power_timer_);
        esp_err_t error=EnableSpeaker(true);
        if(error==ESP_OK) {
            audio_pcm::PackMono(data, count, volume_factor_.load(), tx_buffer_);
            size_t written=0;
            error=i2s_channel_write(tx_chan_,tx_buffer_,count*audio_pcm::kI2sBytesPerSample,&written,0);
            result=arcade::GameWriteFromBytes(count,written,
                error==ESP_OK?State::Ready:error==ESP_ERR_TIMEOUT?State::Busy:State::Fault,
                audio_pcm::kI2sBytesPerSample);
        } else result={0,State::Fault};
        ResetSpeakerTimer();
    }
    xSemaphoreGive(playback_mutex_);return result;
}

esp_err_t AudioHAL::ReadMic(int16_t* dest_buf, size_t max_samples, size_t* samples_read, uint32_t timeout_ms) {
    if (!initialized_ || !rx_chan_ || !dest_buf) return ESP_ERR_INVALID_STATE;

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
        // Preserve native PCM16 headroom. Shifting by 12 applies 16x gain
        // before clipping; host gain cannot recover those destroyed samples.
        int32_t value = bit32_buffer[i] >> 16;
        dest_buf[i] = (value > INT16_MAX) ? INT16_MAX : (value < -INT16_MAX) ? -INT16_MAX : (int16_t)value;
    }

    if (samples_read) {
        *samples_read = count;
    }

    return ESP_OK;
}
