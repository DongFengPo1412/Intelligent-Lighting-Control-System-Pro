// arcade_score_store.h —— ESP32-S3 NVS 最高分持久化存储 (RAM 写回缓存)
#pragma once

#include <stdint.h>

namespace arcade {

class ArcadeScoreStore {
public:
    // 从 NVS 读取指定游戏编号的最高分 (同时考虑尚未落盘的 RAM 缓存, 取较大值; 未保存过返回 0)
    static uint32_t LoadHighScore(uint8_t game_id);

    // 记录新的最高分: 只更新 RAM 缓存并标记脏位, 不会在游戏帧内触发 Flash 擦写。
    // 游戏过程中分数每涨 1 分都可能调用本函数, 因此必须是零阻塞的。
    static void SaveHighScore(uint8_t game_id, uint32_t high_score);

    // 把所有脏的最高分一次性写入 NVS 并 commit。
    // 由 ArcadeManager 在回合结束 / 暂停 / 切换游戏 / 退出时调用。
    static void Flush();

    // 是否存在尚未落盘的最高分 (测试与诊断用)
    static bool HasPending();
};

} // namespace arcade
