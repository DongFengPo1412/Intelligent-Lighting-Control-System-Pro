#include "game_082_artillery.h"
#include "game_080_tron.h"
#include "game_079_penalty.h"
#include "game_078_baseball.h"
#include "game_077_bowling.h"
#include "game_071_peg_solitaire.h"
#include "game_070_flood_it.h"
#include "game_069_nim.h"
#include "game_068_mastermind.h"
#include "game_061_connect_four.h"
#include "game_060_portal_puzzle.h"
#include "game_059_cut_rope.h"
#include "game_056_sliding_puzzle.h"
#include "game_050_mini_sudoku.h"
#include "game_049_lights_out.h"
#include "game_048_triple_town.h"
#include "game_047_blockudoku.h"
#include "game_046_suika.h"
#include "game_039_fog_maze.h"
#include "game_037_qbert.h"
#include "game_036_dig_dug.h"
#include "game_032_defender.h"
#include "game_025_marble_maze.h"
#include "game_024_peggle.h"
#include "game_023_air_hockey.h"
#include "game_013_pendulum_toss.h"
#include "game_012_knife_hit.h"
#include "game_011_dino_runner.h"
#include "game_008_jump_king.h"
#include "game_007_downwell.h"
#include "game_035_boulder_dash.h"
#include "game_057_rush_hour.h"
#include "game_058_program_robot.h"
#include "game_081_qix.h"
#include "game_098_lunar_lander.h"
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

static Game035BoulderDash s_game_035;
static Game057RushHour s_game_057;
static Game058ProgramRobot s_game_058;
static Game081Qix s_game_081;
static Game098LunarLander s_game_098;

static Game007Downwell s_game_007;

static Game008JumpKing s_game_008;

static Game011DinoRunner s_game_011;

static Game012KnifeHit s_game_012;

static Game013PendulumToss s_game_013;

static Game023AirHockey s_game_023;

static Game024Peggle s_game_024;

static Game025MarbleMaze s_game_025;

static Game032Defender s_game_032;

static Game036DigDug s_game_036;

static Game037Qbert s_game_037;

static Game039FogMaze s_game_039;

static Game046Suika s_game_046;

static Game047Blockudoku s_game_047;

static Game048TripleTown s_game_048;

static Game049LightsOut s_game_049;

static Game050MiniSudoku s_game_050;

static Game056SlidingPuzzle s_game_056;

static Game059CutRope s_game_059;

static Game060PortalPuzzle s_game_060;

static Game061ConnectFour s_game_061;

static Game068Mastermind s_game_068;

static Game069Nim s_game_069;

static Game070FloodIt s_game_070;

static Game071PegSolitaire s_game_071;

static Game077Bowling s_game_077;

static Game078Baseball s_game_078;

static Game079Penalty s_game_079;

static Game080Tron s_game_080;

static Game082Artillery s_game_082;

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
        case 82: return &s_game_082;
        case 80: return &s_game_080;
        case 79: return &s_game_079;
        case 78: return &s_game_078;
        case 77: return &s_game_077;
        case 71: return &s_game_071;
        case 70: return &s_game_070;
        case 69: return &s_game_069;
        case 68: return &s_game_068;
        case 61: return &s_game_061;
        case 60: return &s_game_060;
        case 59: return &s_game_059;
        case 56: return &s_game_056;
        case 50: return &s_game_050;
        case 49: return &s_game_049;
        case 48: return &s_game_048;
        case 47: return &s_game_047;
        case 46: return &s_game_046;
        case 39: return &s_game_039;
        case 37: return &s_game_037;
        case 36: return &s_game_036;
        case 32: return &s_game_032;
        case 25: return &s_game_025;
        case 24: return &s_game_024;
        case 23: return &s_game_023;
        case 13: return &s_game_013;
        case 12: return &s_game_012;
        case 11: return &s_game_011;
        case 8: return &s_game_008;
        case 7: return &s_game_007;
        case 35: return &s_game_035;
        case 57: return &s_game_057;
        case 58: return &s_game_058;
        case 81: return &s_game_081;
        case 98: return &s_game_098;

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
    Sounds().Invalidate();
    current_game_ = cart;
    control_paused_ = false;
    current_game_->Init(); // Only selected after app_main has initialized NVS.
    last_state_ = (CartridgeState)current_game_->GetStatus().state;
    ClearInput();
    is_network_disconnected_ = false;
    FeedHeartbeat();

    Sounds().Emit(Sound::Select,game_id);
    ESP_LOGI(TAG, "Selected Cartridge #%03u: %s (%s)",
             current_game_->GetId(), current_game_->GetName(), current_game_->GetEnglishName());
    return true;
}

void ArcadeManager::Start()
{
    if (current_game_) {
        FeedHeartbeat();
        control_paused_ = false;
        auto before=current_game_->GetStatus().state;
        if(before!=STATE_PLAYING)Sounds().Invalidate();
        current_game_->Start();
        if(before!=current_game_->GetStatus().state)Sounds().Emit(Sound::Start,current_game_->GetId());
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
    Sounds().Invalidate();
    ClearInput();
    if (current_game_) {
        auto state = current_game_->GetStatus().state;
        control_paused_ = state == STATE_PLAYING || state == STATE_PAUSED;
        current_game_->Pause();
        if(state==STATE_PLAYING)Sounds().Emit(Sound::Pause,current_game_->GetId());
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
    Sounds().Invalidate();
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
    Sounds().Invalidate();
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

    auto before=current_game_->GetStatus();
    current_game_->Update(dt, current_keys_down_, pressed);
    auto after=current_game_->GetStatus();
    if(after.score>before.score)Sounds().Emit(Sound::Score,current_game_->GetId());
    if(after.lives<before.lives)Sounds().Emit(Sound::Hurt,current_game_->GetId());
    if(after.state!=before.state) {
        if(after.state==STATE_VICTORY){Sounds().Invalidate();Sounds().Emit(Sound::Win,current_game_->GetId());}
        else if(after.state==STATE_GAMEOVER){Sounds().Invalidate();Sounds().Emit(Sound::Lose,current_game_->GetId());}
        else if(after.state==STATE_PAUSED){Sounds().Invalidate();Sounds().Emit(Sound::Pause,current_game_->GetId());}
        else if(after.state==STATE_PLAYING)Sounds().Emit(Sound::Start,current_game_->GetId());
    }

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
        status.difficulty=current_game_->Difficulty();
        status.difficulty_supported=current_game_->SupportsDifficulty();
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

namespace arcade {
bool ArcadeManager::Configure(bool enabled,uint8_t volume,int difficulty) {
    if(volume>100 || difficulty < -1 || difficulty>2)return false;
    if(difficulty>=0) {
        if(!current_game_ || !current_game_->SupportsDifficulty())return false;
        auto state=current_game_->GetStatus().state;
        if(unsigned(difficulty)!=current_game_->Difficulty() && (state==STATE_PLAYING || state==STATE_PAUSED))return false;
        if(unsigned(difficulty)!=current_game_->Difficulty()) {current_game_->SetDifficulty(difficulty);Reset();}
    }
    Sounds().Configure(enabled,volume);return true;
}
}
