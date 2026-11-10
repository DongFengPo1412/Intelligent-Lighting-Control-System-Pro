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
      mic_mutex_(xSemaphoreCreateMutex()),
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
    if (mic_mutex_) vSemaphoreDelete(mic_mutex_);
#if defined(CONFIG_AUDIO_ENABLE_AFE)
    if (afe_iface_ && afe_data_) {
        afe_iface_->destroy(afe_data_);
        afe_data_ = nullptr;
    }
#endif
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
    // 采用 6 个 DMA 描述符 (DMA 6x240, 24kHz 输出)
    i2s_chan_config_t tx_chan_cfg = {
        .id = I2S_NUM_0,
        .role = I2S_ROLE_MASTER,
        .dma_desc_num = 6,
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

    // Mid NoAudioCodecSimplex: mono, 32-bit left slot, Philips bit shift, 24kHz output.
    i2s_std_config_t tx_std_cfg = {
        .clk_cfg = {
            .sample_rate_hz = 24000,
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
#if defined(CONFIG_AUDIO_ENABLE_AFE)
    afe_config_t* afe_config = afe_config_init("M", nullptr, AFE_TYPE_VC, AFE_MODE_HIGH_PERF);
    if (afe_config) {
        afe_config->aec_init = false;
        afe_config->vad_init = true;
        afe_config->vad_mode = VAD_MODE_0;
        afe_config->vad_model_name = nullptr;
        afe_config->vad_min_noise_ms = 100;
        afe_config->ns_init = true;
        afe_config->afe_ns_mode = AFE_NS_MODE_WEBRTC;
        afe_config->ns_model_name = nullptr;
        afe_config->agc_init = false;
        afe_config->memory_alloc_mode = AFE_MEMORY_ALLOC_MORE_PSRAM;
        afe_iface_ = esp_afe_handle_from_config(afe_config);
        if (afe_iface_) {
            afe_data_ = afe_iface_->create_from_config(afe_config);
            if (afe_data_) {
                afe_feed_chunk_ = afe_iface_->get_feed_chunksize(afe_data_);
                afe_fetch_chunk_ = afe_iface_->get_fetch_chunksize(afe_data_);
                ESP_LOGI(TAG, "ESP-SR AFE initialized: WebRTC NS + VAD (feed_chunk=%d, fetch_chunk=%d)",
                         afe_feed_chunk_, afe_fetch_chunk_);
            } else {
                ESP_LOGW(TAG, "ESP-SR AFE create_from_config failed, fallback to raw PCM");
            }
        }
    }
#endif
    initialized_ = true;
    ESP_LOGI(TAG, "I2S ready: mono left slot, 16kHz, volume=%d%% (%s)", volume.value,
             volume.saved ? "restored from NVS" : "default; no saved valid volume");

    return ESP_OK;
}

esp_err_t AudioHAL::EnableMic(bool enable) {
    if (enable && (!initialized_ || !rx_chan_)) return ESP_ERR_INVALID_STATE;
    if (mic_mutex_) xSemaphoreTake(mic_mutex_, portMAX_DELAY);
    mic_enabled_ = enable;
    mic_stream_generation_.fetch_add(1, std::memory_order_relaxed);
#if defined(CONFIG_AUDIO_ENABLE_AFE)
    if (!enable && afe_iface_ && afe_data_) {
        afe_iface_->reset_buffer(afe_data_);
        afe_stream_.Reset();
    }
#endif
    if (mic_mutex_) xSemaphoreGive(mic_mutex_);
    return ESP_OK;
}

esp_err_t AudioHAL::PlayBeep(uint32_t freq_hz, uint32_t duration_ms) {
    if (!freq_hz || freq_hz > 8000 || !duration_ms || duration_ms > 1000) return ESP_ERR_INVALID_ARG;
    // Synthesize directly at 24000 Hz actual I2S rate
    const size_t count = 24000 * duration_ms / 1000;
    std::vector<int16_t> samples(count);
    for (size_t i = 0; i < count; ++i) {
        samples[i] = (int16_t)(std::sin(6.28318530718f * freq_hz * i / 24000.0f) * 6000.0f);
    }
    if (!initialized_ || !tx_chan_) return ESP_ERR_INVALID_STATE;
    if (!playback_mutex_ || xSemaphoreTake(playback_mutex_, pdMS_TO_TICKS(500)) != pdTRUE) return ESP_ERR_TIMEOUT;
    if (spk_power_timer_) esp_timer_stop(spk_power_timer_);
    esp_err_t ret = EnableSpeaker(true);
    if (ret != ESP_OK) {
        xSemaphoreGive(playback_mutex_);
        return ret;
    }
    const size_t chunk_size = 240;
    const uint32_t v_factor = volume_factor_.load();
    size_t written_total = 0;
    while (written_total < count) {
        size_t frames = std::min(chunk_size, count - written_total);
        audio_pcm::PackMono(samples.data() + written_total, frames, v_factor, tx_buffer_);
        size_t bytes_out = 0;
        ret = i2s_channel_write(tx_chan_, tx_buffer_, frames * audio_pcm::kI2sBytesPerSample, &bytes_out, 200);
        if (ret != ESP_OK || bytes_out != frames * audio_pcm::kI2sBytesPerSample) {
            break;
        }
        written_total += frames;
    }
    ResetSpeakerTimer();
    xSemaphoreGive(playback_mutex_);
    return ret;
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

    const size_t chunk_size = 160; // 160 frames @ 16kHz -> 240 frames @ 24kHz
    int32_t* bit32_buf = tx_buffer_;
    size_t written_total = 0;

    // 采用对齐中阶 NoAudioCodec 的音量平方律映射与 16k -> 24k 重采样:
    const uint32_t v_factor = volume_factor_.load();
    audio_pcm::ResetResampler16kTo24k();

    while (written_total < count) {
        size_t frames_in = std::min(chunk_size, count - written_total);
        bool is_last_chunk = (written_total + frames_in >= count);
        size_t frames_out = audio_pcm::PackMono16kTo24k(mono_samples + written_total, frames_in, v_factor, bit32_buf, is_last_chunk);
        size_t written_frames = 0;
        while (written_frames < frames_out) {
            size_t bytes_out = 0;
            ret = i2s_channel_write(tx_chan_, bit32_buf + written_frames,
                                    (frames_out - written_frames) * audio_pcm::kI2sBytesPerSample,
                                    &bytes_out, 200);
            if (ret != ESP_OK || bytes_out == 0) {
                if (ret == ESP_OK) ret = ESP_ERR_TIMEOUT;
                ESP_LOGW(TAG, "I2S playback incomplete: %s (%u bytes)", esp_err_to_name(ret), (unsigned)bytes_out);
                break;
            }
            written_frames += bytes_out / audio_pcm::kI2sBytesPerSample;
        }
        if (written_frames < frames_out) break;
        written_total += frames_in;
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
            // Drain any pending unwritten 24kHz frames from earlier short writes first
            if (pending_game_frames_ > 0) {
                size_t written = 0;
                size_t bytes_to_write = pending_game_frames_ * audio_pcm::kI2sBytesPerSample;
                error = i2s_channel_write(tx_chan_, pending_game_buf_ + pending_game_offset_, bytes_to_write, &written, 0);
                size_t written_frames = written / audio_pcm::kI2sBytesPerSample;
                pending_game_offset_ += written_frames;
                pending_game_frames_ -= written_frames;
                if (pending_game_frames_ > 0) {
                    ResetSpeakerTimer();
                    xSemaphoreGive(playback_mutex_);
                    return {0, State::Busy};
                }
                pending_game_offset_ = 0;
            }

            // Resample 16kHz chunk to 24kHz
            size_t frames_out = game_resampler_.Process(data, count, volume_factor_.load(), tx_buffer_, false);
            size_t written = 0;
            error = i2s_channel_write(tx_chan_, tx_buffer_, frames_out * audio_pcm::kI2sBytesPerSample, &written, 0);
            size_t written_frames = written / audio_pcm::kI2sBytesPerSample;
            if (written_frames < frames_out) {
                // Short write: save remainder into pending buffer to maintain continuous sample timeline
                size_t remainder = frames_out - written_frames;
                if (remainder <= sizeof(pending_game_buf_) / sizeof(pending_game_buf_[0])) {
                    memcpy(pending_game_buf_, tx_buffer_ + written_frames, remainder * audio_pcm::kI2sBytesPerSample);
                    pending_game_frames_ = remainder;
                    pending_game_offset_ = 0;
                }
            }
            // Report entire input chunk consumed: all samples have been converted and written or queued
            result = {unsigned(count), (error == ESP_OK || error == ESP_ERR_TIMEOUT) ? State::Ready : State::Fault};
        } else result={0,State::Fault};
        ResetSpeakerTimer();
    }
    xSemaphoreGive(playback_mutex_);return result;
}

esp_err_t AudioHAL::ReadMic(int16_t* dest_buf, size_t max_samples, size_t* samples_read, uint32_t timeout_ms) {
    if (!initialized_ || !rx_chan_ || !dest_buf) return ESP_ERR_INVALID_STATE;

    uint32_t session_generation = mic_stream_generation_.load(std::memory_order_relaxed);

    const size_t raw_buffer_size = 256;
    size_t samples_to_read = std::min(max_samples, raw_buffer_size);
    size_t bytes_read = 0;

    esp_err_t ret = i2s_channel_read(
        rx_chan_,
        rx_raw_buf_,
        samples_to_read * sizeof(int32_t),
        &bytes_read,
        pdMS_TO_TICKS(timeout_ms)
    );

    if (ret != ESP_OK) {
        if (samples_read) *samples_read = 0;
        return ret;
    }

    size_t count = bytes_read / sizeof(int32_t);
#if defined(CONFIG_AUDIO_MIC_SHIFT_12)
    constexpr int kMicShift = 12;
#else
    constexpr int kMicShift = 16;
#endif
    static uint32_t s_total_samples = 0;
    static uint32_t s_clipped_samples = 0;
    for (size_t i = 0; i < count; ++i) {
        int32_t value = rx_raw_buf_[i] >> kMicShift;
        if (value > INT16_MAX || value < -INT16_MAX) {
            s_clipped_samples++;
        }
        s_total_samples++;
        rx_shifted_buf_[i] = (value > INT16_MAX) ? INT16_MAX : (value < -INT16_MAX) ? -INT16_MAX : (int16_t)value;
    }
    if (s_total_samples >= 160000) {
        ESP_LOGD(TAG, "MIC (shift=%d) clipping rate: %.2f%% (%u/%u)",
                 kMicShift, (double)s_clipped_samples * 100.0 / s_total_samples,
                 (unsigned)s_clipped_samples, (unsigned)s_total_samples);
        s_total_samples = 0;
        s_clipped_samples = 0;
    }

#if defined(CONFIG_AUDIO_ENABLE_AFE)
    if (mic_mutex_) xSemaphoreTake(mic_mutex_, portMAX_DELAY);
    if (!mic_enabled_ || session_generation != mic_stream_generation_.load(std::memory_order_relaxed)) {
        // Stream teardown, stop, or stop-and-restart occurred while I2S read was in flight:
        // discard stale in-flight samples from obsolete generation
        if (mic_mutex_) xSemaphoreGive(mic_mutex_);
        if (samples_read) *samples_read = 0;
        return ESP_ERR_INVALID_STATE;
    }
    if (afe_iface_ && afe_data_ && count > 0) {
        afe_stream_.PushInput(rx_shifted_buf_, count);
        while (afe_stream_.CanFeed(afe_feed_chunk_)) {
            const int16_t* feed_data = afe_stream_.FeedChunk(afe_feed_chunk_, afe_feed_scratch_);
            afe_iface_->feed(afe_data_, feed_data);
            afe_fetch_result_t* res = afe_iface_->fetch_with_delay(afe_data_, 0);
            while (res && res->ret_value == ESP_OK && res->data && res->data_size > 0) {
                size_t out_samples = res->data_size / sizeof(int16_t);
                afe_stream_.PushFetched((const int16_t*)res->data, out_samples);
                res = afe_iface_->fetch_with_delay(afe_data_, 0);
            }
        }
        if (afe_stream_.Emit(dest_buf, rx_shifted_buf_, count)) {
            afe_processed_samples_.fetch_add(count, std::memory_order_relaxed);
        } else {
            afe_fallback_samples_.fetch_add(count, std::memory_order_relaxed);
        }
    } else {
        memcpy(dest_buf, rx_shifted_buf_, count * sizeof(int16_t));
    }
    if (mic_mutex_) xSemaphoreGive(mic_mutex_);
#else
    if (mic_mutex_) xSemaphoreTake(mic_mutex_, portMAX_DELAY);
    if (!mic_enabled_ || session_generation != mic_stream_generation_.load(std::memory_order_relaxed)) {
        if (mic_mutex_) xSemaphoreGive(mic_mutex_);
        if (samples_read) *samples_read = 0;
        return ESP_ERR_INVALID_STATE;
    }
    memcpy(dest_buf, rx_shifted_buf_, count * sizeof(int16_t));
    if (mic_mutex_) xSemaphoreGive(mic_mutex_);
#endif

    if (samples_read) {
        *samples_read = count;
    }

    return ESP_OK;
}
