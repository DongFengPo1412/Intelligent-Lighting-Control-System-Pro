// arcade_score_store.h — ESP32-S3 NVS 最高分持久化存储
#pragma once

#include <stdint.h>

namespace arcade {

class ArcadeScoreStore {
public:
    // 从 NVS 读取指定游戏编号的最高分 (若未保存过则返回 0)
    static uint32_t LoadHighScore(uint8_t game_id);

    // 将指定游戏的新最高分持久化写入 NVS (仅当新分数高于已存记录时触发 Flash 写入)
    static void SaveHighScore(uint8_t game_id, uint32_t high_score);
};

} // namespace arcade

