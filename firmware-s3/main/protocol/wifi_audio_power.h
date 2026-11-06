#pragma once
#include <esp_wifi.h>
#include <esp_log.h>

namespace pcm_transport {
// Like Mid's audio-channel callbacks: performance while authenticated audio
// is open, then restore the prior policy on every exit (including handshake
// or transport failure). Never persist or change the user's Wi-Fi settings.
class WifiAudioPowerSession {
public:
    WifiAudioPowerSession() = default;
    WifiAudioPowerSession(const WifiAudioPowerSession&) = delete;
    WifiAudioPowerSession& operator=(const WifiAudioPowerSession&) = delete;

    esp_err_t Activate() {
        if (active_) return ESP_OK;
        esp_err_t result = esp_wifi_get_ps(&previous_);
        if (result != ESP_OK) return result;
        if (previous_ != WIFI_PS_NONE) {
            result = esp_wifi_set_ps(WIFI_PS_NONE);
            if (result != ESP_OK) return result;
            restore_ = true;
        }
        active_ = true;
        return ESP_OK;
    }

    ~WifiAudioPowerSession() {
        if (restore_) {
            const esp_err_t result = esp_wifi_set_ps(previous_);
            if (result != ESP_OK)
                ESP_LOGW("NetworkAudio", "Wi-Fi power policy restore failed (%d)", result);
        }
    }

private:
    wifi_ps_type_t previous_ = WIFI_PS_MIN_MODEM;
    bool active_ = false;
    bool restore_ = false;
};
}  // namespace pcm_transport
