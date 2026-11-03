// arcade_manager.cpp —— 统一街机游戏运行管理中枢
#include "arcade_manager.h"
#include "game_001_mario.h"
#include "game_033_snake.h"
#include "game_041_tetris.h"
#include <string.h>
#include <esp_timer.h>
#include <esp_log.h>

static const char* TAG = "ArcadeManager";

namespace arcade {

static Game001Mario s_mario;
static Game033Snake s_snake;
static Game041Tetris s_tetris;

ArcadeManager& ArcadeManager::GetInstance()
{
    static ArcadeManager instance;
    return instance;
}

ArcadeManager::ArcadeManager()
{
    Init();
}

void ArcadeManager::Init()
{
    current_game_ = nullptr;
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    last_heartbeat_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
    is_network_disconnected_ = false;
    watchdog_enabled_ = true;
}

Cartridge* ArcadeManager::FindCartridge(uint8_t game_id)
{
    switch (game_id) {
        case 1:  return &s_mario;
        case 33: return &s_snake;
        case 41: return &s_tetris;
        default: return nullptr;
    }
}

bool ArcadeManager::SelectGame(uint8_t game_id)
{
    Cartridge* cart = FindCartridge(game_id);
    if (!cart) {
        ESP_LOGW(TAG, "Cartridge ID #%u not found", game_id);
        return false;
    }

    current_game_ = cart;
    current_game_->Reset();
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    is_network_disconnected_ = false;
    FeedHeartbeat();

    ESP_LOGI(TAG, "Selected Cartridge #%03u: %s (%s)",
             current_game_->GetId(), current_game_->GetName(), current_game_->GetEnglishName());
    return true;
}

void ArcadeManager::Start()
{
    if (current_game_) {
        current_game_->Start();
    }
}

void ArcadeManager::Pause()
{
    if (current_game_) {
        current_game_->Pause();
    }
}

void ArcadeManager::Resume()
{
    if (current_game_) {
        current_game_->Resume();
    }
}

void ArcadeManager::Reset()
{
    if (current_game_) {
        current_game_->Reset();
        current_keys_down_ = 0;
        current_keys_pressed_ = 0;
    }
}

void ArcadeManager::Exit()
{
    if (current_game_) {
        current_game_->Pause();
    }
    current_game_ = nullptr;
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    is_network_disconnected_ = false;
    ESP_LOGI(TAG, "ArcadeManager exited to system menu");
}

void ArcadeManager::HandleInput(uint16_t keys_down, uint16_t keys_pressed)
{
    FeedHeartbeat();
    current_keys_down_ = keys_down;
    current_keys_pressed_ |= keys_pressed;
}

void ArcadeManager::FeedHeartbeat()
{
    last_heartbeat_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
    if (is_network_disconnected_) {
        // 重连事件：恢复连接标志，但绝不自动开火或乱跑，必须保持 PAUSED
        is_network_disconnected_ = false;
        current_keys_down_ = 0;
        current_keys_pressed_ = 0;
        ESP_LOGI(TAG, "Wi-Fi control connection restored, game remains safely PAUSED until user resumes");
    }
}

void ArcadeManager::Update(float dt)
{
    if (!current_game_) return;

    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    uint32_t elapsed_since_hb = now - last_heartbeat_time_ms_;

    if (watchdog_enabled_) {
        // 第一阶段安全阈值 (500ms)：释放长按键，防止因偶发丢包导致小人持续前冲
        if (elapsed_since_hb > 500) {
            current_keys_down_ = 0;
        }

        // 第二阶段安全阈值 (1000ms)：确认 Wi-Fi 控制链路断开，强制进入安全暂停
        if (elapsed_since_hb > 1000 && !is_network_disconnected_) {
            is_network_disconnected_ = true;
            if (current_game_->GetStatus().state == STATE_PLAYING) {
                current_game_->Pause();
                ESP_LOGW(TAG, "Wi-Fi control timed out (>1000ms)! Game automatically entered SAFE PAUSE");
            }
        }
    }

    uint16_t pressed = current_keys_pressed_;
    current_keys_pressed_ = 0; // 消费单次触发键

    current_game_->Update(dt, current_keys_down_, pressed);
}

void ArcadeManager::Render(uint8_t* fb_rgb24)
{
    if (!current_game_) {
        memset(fb_rgb24, 0, kFrameBufferSize);
        return;
    }
    current_game_->Render(fb_rgb24);
}

uint8_t ArcadeManager::GetCurrentGameId() const
{
    return current_game_ ? current_game_->GetId() : 0;
}

ControlType ArcadeManager::GetCurrentControlType() const
{
    return current_game_ ? current_game_->GetControlType() : CTRL_ARCADE_AB;
}

CartridgeStatus ArcadeManager::GetCurrentStatus() const
{
    if (current_game_) {
        return current_game_->GetStatus();
    }
    CartridgeStatus st;
    st.score = 0;
    st.high_score = 0;
    st.lives = 0;
    st.state = STATE_TITLE;
    st.progress = 0;
    return st;
}

const char* ArcadeManager::GetCurrentGameName() const
{
    return current_game_ ? current_game_->GetName() : "None";
}

} // namespace arcade
