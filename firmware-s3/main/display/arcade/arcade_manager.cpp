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
    last_input_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
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
        ESP_LOGW(TAG, "Cartridge ID #%u not found or not yet registered", game_id);
        return false;
    }

    current_game_ = cart;
    current_game_->Reset();
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    FeedHeartbeat();

    ESP_LOGI(TAG, "Selected Cartridge #%03u: %s (%s)",
             current_game_->GetId(), current_game_->GetName(), current_game_->GetEnglishName());
    return true;
}

void ArcadeManager::Start()
{
    if (current_game_) {
        // 模拟按下 START / A 启动游戏
        current_game_->Update(0.016f, KEY_START, KEY_START);
    }
}

void ArcadeManager::Pause()
{
    if (current_game_) {
        current_game_->Update(0.016f, KEY_START, KEY_START);
    }
}

void ArcadeManager::Resume()
{
    if (current_game_) {
        current_game_->Update(0.016f, KEY_START, KEY_START);
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
    current_game_ = nullptr;
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    ESP_LOGI(TAG, "ArcadeManager exited to system menu");
}

void ArcadeManager::HandleInput(uint16_t keys_down, uint16_t keys_pressed)
{
    current_keys_down_ = keys_down;
    current_keys_pressed_ |= keys_pressed;
    FeedHeartbeat();
}

void ArcadeManager::FeedHeartbeat()
{
    last_input_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
}

void ArcadeManager::Update(float dt)
{
    if (!current_game_) return;

    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000);
    // 安全断连看门狗机制：若超过 500ms 未收到手机端心跳/输入数据，自动释放长按键，防止失控冲撞
    if (watchdog_enabled_ && (now - last_input_time_ms_ > 500)) {
        current_keys_down_ = 0;
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
    return CartridgeStatus{0, 0, STATE_TITLE, 0};
}

const char* ArcadeManager::GetCurrentGameName() const
{
    return current_game_ ? current_game_->GetName() : "None";
}

} // namespace arcade
