// arcade_manager.cpp —— 统一街机游戏运行管理中枢
#include "arcade_manager.h"
#include "game_001_mario.h"
#include "game_002_doodle_jump.h"
#include "game_003_celeste_dash.h"
#include "game_004_gravity_flip.h"
#include "game_005_lode_runner.h"
#include "game_006_bubble_bobble.h"
#include "game_009_flappy_bird.h"
#include "game_010_stack.h"
#include "game_014_orbit_hop.h"
#include "game_015_simon_memory.h"
#include "game_016_whack_a_mole.h"
#include "game_017_rhythm_lanes.h"
#include "game_018_red_green_light.h"
#include "game_019_shell_game.h"
#include "game_020_pong.h"
#include "game_021_breakout.h"
#include "game_022_pinball.h"
#include "game_026_space_invaders.h"
#include "game_027_asteroids.h"
#include "game_028_missile_command.h"
#include "game_029_centipede.h"
#include "game_030_duck_hunt.h"
#include "game_031_robotron.h"
#include "game_033_snake.h"
#include "game_034_pacman.h"
#include "game_038_bomberman.h"
#include "game_040_mirror_maze.h"
#include "game_041_tetris.h"
#include "game_042_puyo_puyo.h"
#include "game_043_merge_2048.h"
#include "game_044_bejeweled.h"
#include "game_045_samegame.h"
#include "game_051_flow_free.h"
#include "game_052_pipe_connect.h"
#include "game_053_tower_of_hanoi.h"
#include "game_054_sokoban.h"
#include "game_055_mirror_laser.h"
#include "game_062_reversi.h"
#include "game_063_gomoku.h"
#include "game_064_checkers.h"
#include "game_065_dots_and_boxes.h"
#include "game_066_battleship.h"
#include "game_067_quoridor.h"
#include "game_072_hex_board.h"
#include "game_073_ludo_race.h"
#include "game_074_highway_racer.h"
#include "game_075_slalom_ski.h"
#include "game_076_mini_golf.h"
#include "game_083_tower_defense.h"
#include "game_084_node_conquest.h"
#include "game_085_lemmings_rescue.h"
#include "game_086_tiny_farm.h"
#include "game_087_traffic_control.h"
#include "game_088_atc_landing.h"
#include "game_092_fruit_slice.h"
#include "game_093_black_hole.h"
#include "game_094_grapple_swing.h"
#include "game_095_super_hexagon.h"
#include "game_097_frogger.h"
#include "arcade_score_store.h"
#include <string.h>
#include <esp_timer.h>
#include <esp_log.h>

static const char* TAG = "ArcadeManager";

namespace arcade {

static Game001Mario s_game_001;
static Game002DoodleJump s_game_002;
static Game003CelesteDash s_game_003;
static Game004GravityFlip s_game_004;
static Game005LodeRunner s_game_005;
static Game006BubbleBobble s_game_006;
static Game009FlappyBird s_game_009;
static Game010Stack s_game_010;
static Game014OrbitHop s_game_014;
static Game015SimonMemory s_game_015;
static Game016WhackAMole s_game_016;
static Game017RhythmLanes s_game_017;
static Game018RedGreenLight s_game_018;
static Game019ShellGame s_game_019;
static Game020Pong s_game_020;
static Game021Breakout s_game_021;
static Game022Pinball s_game_022;
static Game026SpaceInvaders s_game_026;
static Game027Asteroids s_game_027;
static Game028MissileCommand s_game_028;
static Game029Centipede s_game_029;
static Game030DuckHunt s_game_030;
static Game031Robotron s_game_031;
static Game033Snake s_game_033;
static Game034Pacman s_game_034;
static Game038Bomberman s_game_038;
static Game040MirrorMaze s_game_040;
static Game041Tetris s_game_041;
static Game042PuyoPuyo s_game_042;
static Game043Merge2048 s_game_043;
static Game044Bejeweled s_game_044;
static Game045SameGame s_game_045;
static Game051FlowFree s_game_051;
static Game052PipeConnect s_game_052;
static Game053TowerOfHanoi s_game_053;
static Game054Sokoban s_game_054;
static Game055MirrorLaser s_game_055;
static Game062Reversi s_game_062;
static Game063Gomoku s_game_063;
static Game064Checkers s_game_064;
static Game065DotsAndBoxes s_game_065;
static Game066Battleship s_game_066;
static Game067Quoridor s_game_067;
static Game072HexBoard s_game_072;
static Game073LudoRace s_game_073;
static Game074HighwayRacer s_game_074;
static Game075SlalomSki s_game_075;
static Game076MiniGolf s_game_076;
static Game083TowerDefense s_game_083;
static Game084NodeConquest s_game_084;
static Game085LemmingsRescue s_game_085;
static Game086TinyFarm s_game_086;
static Game087TrafficControl s_game_087;
static Game088AtcLanding s_game_088;
static Game092FruitSlice s_game_092;
static Game093BlackHole s_game_093;
static Game094GrappleSwing s_game_094;
static Game095SuperHexagon s_game_095;
static Game097Frogger s_game_097;

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
    ClearInput();
    last_heartbeat_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
    is_network_disconnected_ = false;
    watchdog_enabled_ = true;
    control_paused_ = false;
}

Cartridge* ArcadeManager::FindCartridge(uint8_t game_id)
{
    switch (game_id) {
        case 1: return &s_game_001;
        case 2: return &s_game_002;
        case 3: return &s_game_003;
        case 4: return &s_game_004;
        case 5: return &s_game_005;
        case 6: return &s_game_006;
        case 9: return &s_game_009;
        case 10: return &s_game_010;
        case 14: return &s_game_014;
        case 15: return &s_game_015;
        case 16: return &s_game_016;
        case 17: return &s_game_017;
        case 18: return &s_game_018;
        case 19: return &s_game_019;
        case 20: return &s_game_020;
        case 21: return &s_game_021;
        case 22: return &s_game_022;
        case 26: return &s_game_026;
        case 27: return &s_game_027;
        case 28: return &s_game_028;
        case 29: return &s_game_029;
        case 30: return &s_game_030;
        case 31: return &s_game_031;
        case 33: return &s_game_033;
        case 34: return &s_game_034;
        case 38: return &s_game_038;
        case 40: return &s_game_040;
        case 41: return &s_game_041;
        case 42: return &s_game_042;
        case 43: return &s_game_043;
        case 44: return &s_game_044;
        case 45: return &s_game_045;
        case 51: return &s_game_051;
        case 52: return &s_game_052;
        case 53: return &s_game_053;
        case 54: return &s_game_054;
        case 55: return &s_game_055;
        case 62: return &s_game_062;
        case 63: return &s_game_063;
        case 64: return &s_game_064;
        case 65: return &s_game_065;
        case 66: return &s_game_066;
        case 67: return &s_game_067;
        case 72: return &s_game_072;
        case 73: return &s_game_073;
        case 74: return &s_game_074;
        case 75: return &s_game_075;
        case 76: return &s_game_076;
        case 83: return &s_game_083;
        case 84: return &s_game_084;
        case 85: return &s_game_085;
        case 86: return &s_game_086;
        case 87: return &s_game_087;
        case 88: return &s_game_088;
        case 92: return &s_game_092;
        case 93: return &s_game_093;
        case 94: return &s_game_094;
        case 95: return &s_game_095;
        case 97: return &s_game_097;
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
    ClearInput();
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

bool ArcadeManager::SetPlayerCount(uint8_t count)
{
    if (!current_game_ || current_game_->GetId() != 20) return false;
    if (!static_cast<Game020Pong*>(current_game_)->SetPlayerCount(count)) return false;
    ClearInput();
    FeedHeartbeat();
    return true;
}

void ArcadeManager::Pause()
{
    ClearInput();
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
        ClearInput();
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
    ClearInput();
    is_network_disconnected_ = false;
    ESP_LOGI(TAG, "ArcadeManager exited to system menu");
}

bool ArcadeManager::HandleInput(uint16_t keys_down, uint16_t keys_pressed)
{
    FeedHeartbeat();
    if (!current_game_ || control_paused_ || current_game_->GetStatus().state == STATE_PAUSED) {
        ClearInput();
        return true; // Input cannot leave safe pause.
    }
    if (keys_pressed && input_count_ == kInputEvents) {
        Pause(); // Report overload instead of silently dropping a press edge.
        return false;
    }
    current_keys_down_ = keys_down;
    if (keys_pressed) {
        input_events_[(input_head_ + input_count_) % kInputEvents] = keys_pressed;
        ++input_count_;
    }
    return true;
}

void ArcadeManager::FeedHeartbeat()
{
    last_heartbeat_time_ms_ = (uint32_t)(esp_timer_get_time() / 1000);
    if (is_network_disconnected_) {
        // 重连事件：恢复连接标志，但绝不自动开火或乱跑，必须保持 PAUSED
        is_network_disconnected_ = false;
        ClearInput();
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
            ClearInput();
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

    uint16_t pressed = 0;
    if (input_count_) {
        pressed = input_events_[input_head_];
        input_head_ = (input_head_ + 1) % kInputEvents;
        --input_count_;
    }
    current_keys_pressed_ = 0; // One edge per game tick; rapid taps do not collapse.
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
