// arcade_score_store.cpp —— ESP32-S3 NVS 最高分持久化存储 (RAM 写回缓存)
//
// 旧实现在每次分数上涨时都执行 nvs_set_u32 + nvs_commit。一旦本局超过历史最高分,
// 像变道赛车这类"每帧计分"的游戏会以每秒数十次的频率擦写 Flash, 既磨损 Flash,
// 又会因 commit 阻塞造成掉帧。现在改为: 游戏帧内只写 RAM, 在回合结束/暂停/切换时统一落盘。
#include "arcade_score_store.h"
#include <nvs_flash.h>
#include <nvs.h>
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <stdio.h>

namespace arcade {

static const char* TAG = "ArcadeScore";

static uint32_t s_pending[256];
static bool s_dirty[256];
static bool s_any_dirty = false;
static portMUX_TYPE s_lock = portMUX_INITIALIZER_UNLOCKED;

static void MakeKey(uint8_t game_id, char* key, size_t len)
{
    snprintf(key, len, "hs_%03u", (unsigned int)game_id);
}

uint32_t ArcadeScoreStore::LoadHighScore(uint8_t game_id)
{
    uint32_t score = 0;
    nvs_handle_t handle;
    if (nvs_open("arcade_hs", NVS_READONLY, &handle) == ESP_OK) {
        char key[16];
        MakeKey(game_id, key, sizeof(key));
        if (nvs_get_u32(handle, key, &score) != ESP_OK) {
            score = 0;
        }
        nvs_close(handle);
    }

    portENTER_CRITICAL(&s_lock);
    uint32_t pending = s_pending[game_id];
    portEXIT_CRITICAL(&s_lock);
    if (pending > score) {
        score = pending;
    }
    return score;
}

void ArcadeScoreStore::SaveHighScore(uint8_t game_id, uint32_t high_score)
{
    if (high_score == 0) return;
    portENTER_CRITICAL(&s_lock);
    if (high_score > s_pending[game_id]) {
        s_pending[game_id] = high_score;
        s_dirty[game_id] = true;
        s_any_dirty = true;
    }
    portEXIT_CRITICAL(&s_lock);
}

bool ArcadeScoreStore::HasPending()
{
    portENTER_CRITICAL(&s_lock);
    bool any = s_any_dirty;
    portEXIT_CRITICAL(&s_lock);
    return any;
}

void ArcadeScoreStore::Flush()
{
    // 先在临界区内快照脏数据, 再在临界区外做 Flash 操作 (Flash 操作不可在临界区内执行)
    // 快照缓冲放在静态区, 避免在调用方任务栈上占用 1.3KB; s_flushing 防止多任务重入。
    static uint32_t snapshot[256];
    static bool dirty[256];
    static bool s_flushing = false;
    portENTER_CRITICAL(&s_lock);
    if (!s_any_dirty || s_flushing) {
        portEXIT_CRITICAL(&s_lock);
        return;
    }
    s_flushing = true;
    for (int i = 0; i < 256; ++i) {
        snapshot[i] = s_pending[i];
        dirty[i] = s_dirty[i];
        s_dirty[i] = false;
    }
    s_any_dirty = false;
    portEXIT_CRITICAL(&s_lock);

    nvs_handle_t handle;
    esp_err_t err = nvs_open("arcade_hs", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS namespace arcade_hs: %s", esp_err_to_name(err));
        // 落盘失败: 恢复脏位, 下次再试
        portENTER_CRITICAL(&s_lock);
        for (int i = 0; i < 256; ++i) {
            if (dirty[i]) { s_dirty[i] = true; s_any_dirty = true; }
        }
        s_flushing = false;
        portEXIT_CRITICAL(&s_lock);
        return;
    }

    bool wrote = false;
    for (int i = 0; i < 256; ++i) {
        if (!dirty[i]) continue;
        char key[16];
        MakeKey((uint8_t)i, key, sizeof(key));
        uint32_t existing = 0;
        nvs_get_u32(handle, key, &existing);
        if (snapshot[i] > existing) {
            err = nvs_set_u32(handle, key, snapshot[i]);
            if (err == ESP_OK) {
                wrote = true;
                ESP_LOGI(TAG, "High score #%03d: %u -> %u", i, (unsigned int)existing,
                         (unsigned int)snapshot[i]);
            } else {
                ESP_LOGE(TAG, "Failed to write high score #%03d: %s", i, esp_err_to_name(err));
            }
        }
    }
    if (wrote) {
        err = nvs_commit(handle);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to commit high scores to NVS: %s", esp_err_to_name(err));
        }
    }
    nvs_close(handle);

    portENTER_CRITICAL(&s_lock);
    s_flushing = false;
    portEXIT_CRITICAL(&s_lock);
}

} // namespace arcade
