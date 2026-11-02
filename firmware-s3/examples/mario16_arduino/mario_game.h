// mario_game.h —— 16x16 灯板上的迷你马里奥游戏引擎（与硬件无关）
//
// 设计目的：
//   * 不依赖 FastLED / Arduino，方便塞进任何固件里当“第 N 号模式”；
//   * 输入是一帧的按键位图，输出是 16x16 的 RGB888 帧缓冲；
//   * 屏幕坐标 y 向下，1 个字符 = 1 颗灯，马里奥 2x3 像素，板栗仔 2x2 像素。
//
// 典型用法（Arduino）：
//     mario16::Game game;
//     game.begin();
//     mario16::Input in{ keysDown, keysPressed };
//     game.update(dt, in);
//     game.render(fb);              // fb[16*16*3]  RGB
//     for (int y = 0; y < 16; y++)
//       for (int x = 0; x < 16; x++)
//         leds[XY(x, y)] = CRGB(fb[(y*16+x)*3], fb[(y*16+x)*3+1], fb[(y*16+x)*3+2]);

#ifndef MARIO16_GAME_H
#define MARIO16_GAME_H

#include <stdint.h>

#include "mario_level.h"

namespace mario16 {

static const int kPanelW = 16;
static const int kPanelH = 16;
static const int kLevelW = LEVEL_W;
static const int kLevelH = LEVEL_H;

// 一帧的按键：down 是当前按住，pressed 是“本帧刚按下”（处理开始/暂停这类一次性操作）
enum KeyBits : uint16_t {
  KEY_LEFT   = 1u << 0,
  KEY_RIGHT  = 1u << 1,
  KEY_UP     = 1u << 2,
  KEY_DOWN   = 1u << 3,
  KEY_A      = 1u << 4,   // 跳跃
  KEY_B      = 1u << 5,   // 加速跑
  KEY_START  = 1u << 6,   // 暂停 / 继续
  KEY_SELECT = 1u << 7,
};

struct Input {
  uint16_t down;
  uint16_t pressed;
};

enum GameState : uint8_t {
  ST_TITLE = 0,
  ST_READY = 1,
  ST_PLAY = 2,
  ST_PAUSE = 3,
  ST_DEAD = 4,
  ST_GAMEOVER = 5,
  ST_WIN = 6,
};

struct Status {
  uint16_t score;
  uint8_t lives;
  uint8_t coins;
  uint8_t state;     // GameState
  uint8_t progress;  // 0..100 关卡进度
};

enum SoundId : uint8_t {
  SND_JUMP = 0,
  SND_COIN,
  SND_STOMP,
  SND_DIE,
  SND_WIN,
  SND_START,
  SND_PAUSE,
  SND_1UP,
};

// 音效回调：固件里实现（可以留空）。引擎里有 weak 默认空实现。
// 注意：它在全局命名空间，声明见文件末尾。

class Game {
 public:
  void begin();
  // dt 单位秒，内部裁剪到 [0, 0.05]
  void update(float dt, const Input& in);
  // 把当前画面写进 16x16 的 RGB888 缓冲区（长度 768）
  void render(uint8_t* rgb);
  Status status() const;
  void resetAll();
  void setPaused(bool on);
  void togglePause();
  bool isPaused() const { return state_ == ST_PAUSE; }

 private:
  enum { kPlayerW = 2, kPlayerH = 3 };
  enum { kMaxEnemies = 12, kMaxParticles = 24 };

  struct Enemy {
    float x, y;
    float vx, vy;
    float squash;   // >0 表示被踩扁后的残留动画
    bool alive;
  };

  struct Particle {
    float x, y, vx, vy, life, life0;
    uint8_t r, g, b;
  };

  // ---- 关卡 ----
  char map0_[kLevelW * kLevelH];   // 原始地图（含 S / g / o 标记）
  char map_[kLevelW * kLevelH];    // 运行中的地图，金币被吃掉后改成 '.'
  int levelW_ = 0;
  int flagX_ = 0;
  int spawnX_ = 2, spawnY_ = 11;

  // ---- 玩家 ----
  float px_ = 0, py_ = 0, vx_ = 0, vy_ = 0;
  bool onGround_ = false;
  bool jumpCut_ = false;
  float coyote_ = 0, jumpBuf_ = 0, invuln_ = 0;
  int face_ = 1;

  // ---- 世界 ----
  float cam_ = 0;
  Enemy enemies_[kMaxEnemies];
  int enemyCount_ = 0;
  Particle parts_[kMaxParticles];
  int partCount_ = 0;
  int coins_ = 0;
  int lives_ = 3;
  uint16_t score_ = 0;
  float clock_ = 0;
  float stateT_ = 0;
  GameState state_ = ST_TITLE;

  void parseLevel();
  void resetLevel();
  void resetPlayer();
  void setState(GameState s);
  void updatePlay(float dt, const Input& in);
  void updateEnemies(float dt);
  void collectCoins();
  void checkEnemyHit();
  void killPlayer();
  void winLevel();
  void updateParticles(float dt);
  void spawnParticles(float x, float y, uint8_t r, uint8_t g, uint8_t b, int n);

  bool solidTile(int tx, int ty) const;
  bool rectSolid(float x, float y, float w, float h) const;

  // ---- 渲染 ----
  uint8_t fb_[kPanelW * kPanelH * 3];
  void clear(uint8_t r, uint8_t g, uint8_t b);
  void px(int x, int y, uint8_t r, uint8_t g, uint8_t b);
  void dim(uint8_t k);
  void drawWorld();
  void drawPlayerSprite();
  void drawEnemies();
  void drawParticles();
  void drawTitle();
  void drawReadyScreen();
  void drawPauseScreen();
  void drawDeadScreen();
  void drawGameOverScreen();
  void drawWinScreen();
  void drawChar(int x, int y, char c, uint8_t r, uint8_t g, uint8_t b);
  void drawCharScaled(int x, int y, char c, int scale, uint8_t r, uint8_t g, uint8_t b);
  void drawText(int x, int y, const char* s, uint8_t r, uint8_t g, uint8_t b);
  void drawTextScaled(int x, int y, const char* s, int scale, uint8_t r, uint8_t g, uint8_t b);
  void drawMarquee(const char* s, float x, int y, uint8_t r, uint8_t g, uint8_t b);
};

}  // namespace mario16

// 音效回调：名字在全局命名空间，固件里直接实现一个同名函数即可覆盖
// （引擎内部有 weak 空实现，不实现也不会链接报错）。
void mario16Sound(uint8_t id);

#endif  // MARIO16_GAME_H
