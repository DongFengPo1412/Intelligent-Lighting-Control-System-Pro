#include "network_auth.h"
#include <nvs.h>
#include <esp_random.h>
#include <bootloader_random.h>
#include <string.h>

namespace {
void RandomHex(char* out, size_t bytes) {
    unsigned char data[32];
    esp_fill_random(data, bytes);
    const char* hex = "0123456789abcdef";
    for (size_t i = 0; i < bytes; ++i) {
        out[2*i] = hex[data[i] >> 4]; out[2*i+1] = hex[data[i] & 15];
    }
    out[2*bytes] = 0;
}
}
NetworkAuth& NetworkAuth::GetInstance() { static NetworkAuth auth; return auth; }
bool NetworkAuth::Init(bool nvs_ready) {
    if (ready_) return true;
    if (!nvs_ready) return false;
    // Called before the RF/ADC drivers start; enable the hardware entropy source.
    bootloader_random_enable();
    RandomHex(boot_id_, 16);
    nvs_handle_t handle;
    esp_err_t err = nvs_open("kurisu_pair", NVS_READWRITE, &handle);
    if (err == ESP_OK) {
        size_t size = sizeof(token_);
        err = nvs_get_str(handle, "control_key", token_, &size);
        if (err == ESP_ERR_NVS_NOT_FOUND) {
            RandomHex(token_, 32);
            err = nvs_set_str(handle, "control_key", token_);
            if (err == ESP_OK) err = nvs_commit(handle);
        }
        ready_ = err == ESP_OK && strlen(token_) == 64 &&
            strspn(token_, "0123456789abcdef") == 64;
        nvs_close(handle);
    }
    bootloader_random_disable();
    if (!ready_) memset(token_, 0, sizeof(token_));
    return ready_;
}
bool NetworkAuth::Check(const char* token) const {
    if (!ready_ || !token) return false;
    size_t len = 0;
    while (len < 65 && token[len] != '\0') ++len;
    if (len != 64) return false;
    unsigned char diff = 0;
    for (size_t i = 0; i < 64; ++i) diff |= token_[i] ^ token[i];
    return diff == 0;
}
