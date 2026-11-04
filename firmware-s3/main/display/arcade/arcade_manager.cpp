// arcade_manager.cpp —— 统一街机游戏运行管理中枢
#include "arcade_manager.h"
#include "game_001_mario.h"
#include "game_009_flappy_bird.h"
#include "game_010_stack.h"
#include "game_020_pong.h"
#include "game_021_breakout.h"
#include "game_026_space_invaders.h"
#include "game_033_snake.h"
#include "game_034_pacman.h"
#include "game_038_bomberman.h"
#include "game_041_tetris.h"
#include "game_054_sokoban.h"
#include "game_074_highway_racer.h"
#include "game_097_frogger.h"
#include "arcade_score_store.h"
#include <string.h>
#include <esp_timer.h>
#include <esp_log.h>

static const char* TAG = "ArcadeManager";

namespace arcade {

static Game001Mario s_mario;
static Game009FlappyBird s_flappy_bird;
static Game010Stack s_stack;
static Game020Pong s_pong;
static Game021Breakout s_breakout;
static Game026SpaceInvaders s_space_invaders;
static Game033Snake s_snake;
static Game034Pacman s_pacman;
static Game038Bomberman s_bomberman;
static Game041Tetris s_tetris;
static Game054Sokoban s_sokoban;
static Game074HighwayRacer s_highway_racer;
static Game097Frogger s_frogger;

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
    control_paused_ = false;
}

Cartridge* ArcadeManager::FindCartridge(uint8_t game_id)
{
    switch (game_id) {
        case 1:  return &s_mario;
        case 9:  return &s_flappy_bird;
        case 10: return &s_stack;
        case 20: return &s_pong;
        case 21: return &s_breakout;
        case 26: return &s_space_invaders;
        case 33: return &s_snake;
        case 34: return &s_pacman;
        case 38: return &s_bomberman;
        case 41: return &s_tetris;
        case 54: return &s_sokoban;
        case 74: return &s_highway_racer;
        case 97: return &s_frogger;
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

    ArcadeScoreStore::Flush(); // 落盘上一款游戏尚未保存的最高分
    current_game_ = cart;
    control_paused_ = false;
    current_game_->Init(); // Only selected after app_main has initialized NVS.
    last_state_ = (CartridgeState)current_game_->GetStatus().state;
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
        FeedHeartbeat();
        control_paused_ = false;
        current_game_->Start();
    }
}

void ArcadeManager::Pause()
{
    current_keys_down_ = current_keys_pressed_ = 0;
    if (current_game_) {
        auto state = current_game_->GetStatus().state;
        control_paused_ = state == STATE_PLAYING || state == STATE_PAUSED;
        current_game_->Pause();
        ArcadeScoreStore::Flush();
    }
}

void ArcadeManager::Resume()
{
    if (current_game_) {
        FeedHeartbeat();
        control_paused_ = false;
        current_game_->Resume();
    }
}

void ArcadeManager::Reset()
{
    if (current_game_) {
        ArcadeScoreStore::Flush();
        current_game_->Reset();
        control_paused_ = false;
        current_keys_down_ = 0;
        current_keys_pressed_ = 0;
        last_state_ = (CartridgeState)current_game_->GetStatus().state;
    }
}

void ArcadeManager::Exit()
{
    if (current_game_) {
        current_game_->Pause();
    }
    ArcadeScoreStore::Flush();
    current_game_ = nullptr;
    control_paused_ = false;
    current_keys_down_ = 0;
    current_keys_pressed_ = 0;
    is_network_disconnected_ = false;
    ESP_LOGI(TAG, "ArcadeManager exited to system menu");
}

void ArcadeManager::HandleInput(uint16_t keys_down, uint16_t keys_pressed)
{
    FeedHeartbeat();
    if (!current_game_ || control_paused_ || current_game_->GetStatus().state == STATE_PAUSED) {
        current_keys_down_ = current_keys_pressed_ = 0;
        return; // Only an explicit lifecycle resume/start may leave safe pause.
    }
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
            current_keys_pressed_ = 0;
        }

        // 第二阶段安全阈值 (1000ms)：确认 Wi-Fi 控制链路断开，强制进入安全暂停
        if (elapsed_since_hb > 1000 && !is_network_disconnected_) {
            is_network_disconnected_ = true;
            if (current_game_->GetStatus().state == STATE_PLAYING) {
                Pause();
                ESP_LOGW(TAG, "Wi-Fi control timed out (>1000ms)! Game automatically entered SAFE PAUSE");
            }
        }
    }

    uint16_t pressed = current_keys_pressed_;
    current_keys_pressed_ = 0; // 消费单次触发键
    if (control_paused_) return;

    current_game_->Update(dt, current_keys_down_, pressed);

    // 离开 PLAYING (结算/胜利/暂停) 时才把本局最高分写入 Flash, 游戏帧内绝不擦写 Flash
    CartridgeState st = (CartridgeState)current_game_->GetStatus().state;
    if (last_state_ == STATE_PLAYING && st != STATE_PLAYING) {
        ArcadeScoreStore::Flush();
    }
    last_state_ = st;
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
        auto status = current_game_->GetStatus();
        if (control_paused_) status.state = STATE_PAUSED;
        return status;
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
