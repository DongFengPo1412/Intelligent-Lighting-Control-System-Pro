// arcade_score_store.cpp — ESP32-S3 NVS 最高分持久化存储
#include "arcade_score_store.h"
#include <nvs_flash.h>
#include <nvs.h>
#include <esp_log.h>
#include <stdio.h>

namespace arcade {

static const char* TAG = "ArcadeScore";

uint32_t ArcadeScoreStore::LoadHighScore(uint8_t game_id)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open("arcade_hs", NVS_READONLY, &handle);
    if (err != ESP_OK) {
        return 0;
    }
    char key[16];
    snprintf(key, sizeof(key), "hs_%03u", (unsigned int)game_id);
    uint32_t score = 0;
    err = nvs_get_u32(handle, key, &score);
    nvs_close(handle);
    if (err != ESP_OK) {
        return 0;
    }
    ESP_LOGI(TAG, "Loaded high score for game #%03u: %u", (unsigned int)game_id, (unsigned int)score);
    return score;
}

void ArcadeScoreStore::SaveHighScore(uint8_t game_id, uint32_t high_score)
{
    if (high_score == 0) return;

    nvs_handle_t handle;
    esp_err_t err = nvs_open("arcade_hs", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace arcade_hs: %s", esp_err_to_name(err));
        return;
    }
    char key[16];
    snprintf(key, sizeof(key), "hs_%03u", (unsigned int)game_id);
    uint32_t existing = 0;
    nvs_get_u32(handle, key, &existing);
    if (high_score > existing) {
        err = nvs_set_u32(handle, key, high_score);
        if (err == ESP_OK) {
            nvs_commit(handle);
            ESP_LOGI(TAG, "Persisted new high score for game #%03u: %u (previous: %u)",
                     (unsigned int)game_id, (unsigned int)high_score, (unsigned int)existing);
        } else {
            ESP_LOGE(TAG, "Failed to write high score to NVS: %s", esp_err_to_name(err));
        }
    }
    nvs_close(handle);
}

} // namespace arcade
