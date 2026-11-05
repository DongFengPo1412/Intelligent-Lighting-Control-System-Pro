#pragma once
#include <nvs.h>

// Same namespace/key and integer encoding as Mid AudioCodec. Called after
// app_main initializes NVS, never during static construction; never erases NVS.
namespace audio_preferences {
struct Volume { int value; bool saved; esp_err_t error; };
inline Volume Load(int fallback = 70) {
    nvs_handle_t handle;
    esp_err_t error = nvs_open("audio", NVS_READONLY, &handle);
    if (error != ESP_OK) return {fallback, false, error};
    int32_t value = fallback;
    error = nvs_get_i32(handle, "output_volume", &value);
    nvs_close(handle);
    if (error != ESP_OK || value < 0 || value > 100)
        return {fallback, false, error == ESP_OK ? ESP_FAIL : error};
    // Preserve explicit mute (0). Do not unexpectedly unmute on reboot.
    return {int(value), true, ESP_OK};
}
inline esp_err_t Save(int value) {
    if (value < 0 || value > 100) return ESP_FAIL;
    nvs_handle_t handle;
    esp_err_t error = nvs_open("audio", NVS_READWRITE, &handle);
    if (error != ESP_OK) return error;
    error = nvs_set_i32(handle, "output_volume", value);
    if (error == ESP_OK) error = nvs_commit(handle);
    nvs_close(handle);
    return error;
}
}
