// arcade_manager.h —— 统一街机游戏运行管理中枢
#pragma once

#include "arcade_cartridge.h"
#include <stdint.h>
#include <stddef.h>

namespace arcade {

class ArcadeManager {
public:
    static ArcadeManager& GetInstance();

    // 初始化注册表
    void Init();

    // 游戏选择与幂等生命周期管理
    bool SelectGame(uint8_t game_id);
    void Start();
    void Pause();
    void Resume();
    void Reset();
    void Exit();

    // 输入与 Wi-Fi 看门狗
    void HandleInput(uint16_t keys_down, uint16_t keys_pressed);
    void FeedHeartbeat();
    bool IsNetworkDisconnected() const { return is_network_disconnected_; }

    // 逻辑步进与渲染
    void Update(float dt);
    void Render(uint8_t* fb_rgb24);

    // 状态查询
    bool IsActive() const { return current_game_ != nullptr; }
    uint8_t GetCurrentGameId() const;
    ControlType GetCurrentControlType() const;
    CartridgeStatus GetCurrentStatus() const;
    const char* GetCurrentGameName() const;

private:
    ArcadeManager();
    ~ArcadeManager() = default;

    ArcadeManager(const ArcadeManager&) = delete;
    ArcadeManager& operator=(const ArcadeManager&) = delete;

    Cartridge* FindCartridge(uint8_t game_id);

    Cartridge* current_game_ = nullptr;
    uint16_t current_keys_down_ = 0;
    uint16_t current_keys_pressed_ = 0;
    uint32_t last_heartbeat_time_ms_ = 0;
    bool is_network_disconnected_ = false;
    bool watchdog_enabled_ = true;
    CartridgeState last_state_ = STATE_TITLE;  // 用于检测"离开 PLAYING"事件并触发最高分落盘
};

} // namespace arcade
