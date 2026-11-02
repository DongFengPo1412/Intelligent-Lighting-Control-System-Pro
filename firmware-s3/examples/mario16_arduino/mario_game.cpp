// mario_game.cpp —— 16x16 灯板迷你马里奥游戏引擎
//
// 纯逻辑 + 软件渲染，不依赖任何硬件库；固件只需把 render() 出来的
// RGB 缓冲区按自己的灯板映射刷到 WS2812 上即可。

#include "mario_game.h"

#include <math.h>
#include <string.h>

// 固件里覆写这个 weak 函数即可加音效（声明在头文件末尾，全局命名空间）
#if defined(_MSC_VER)
void mario16Sound(uint8_t id) { (void)id; }
#else
__attribute__((weak)) void mario16Sound(uint8_t id) { (void)id; }
#endif

namespace mario16 {

namespace {

struct Rgb {
  uint8_t r, g, b;
};

const Rgb SKY_TOP  = {0, 4, 14};
const Rgb SKY_BOT  = {0, 12, 30};
const Rgb GRASS    = {0, 95, 20};
const Rgb DIRT     = {60, 36, 9};
const Rgb BRICK    = {150, 85, 15};
const Rgb BRICK2   = {182, 112, 32};
const Rgb PIPE     = {0, 195, 55};
const Rgb PIPE_DARK= {0, 85, 28};
const Rgb COIN     = {255, 190, 10};
const Rgb CAP      = {235, 24, 24};
const Rgb SKIN     = {255, 190, 130};
const Rgb OVERALL  = {28, 64, 235};
const Rgb GOOMBA   = {165, 96, 30};
const Rgb GOOMBA_FOOT = {78, 44, 10};
const Rgb POLE     = {200, 200, 200};
const Rgb CLOTH    = {0, 220, 90};
const Rgb WHITE    = {255, 255, 255};
const Rgb GOLD     = {255, 205, 40};
const Rgb RED      = {255, 60, 40};

// 物理参数（单位：灯格 / 秒）
const float GRAV         = 62.0f;
const float MAX_FALL     = 26.0f;
const float WALK_SPEED   = 3.4f;
const float RUN_SPEED    = 5.6f;
const float ACCEL_GROUND = 70.0f;
const float ACCEL_AIR    = 45.0f;
const float JUMP_V       = 23.5f;
const float ENEMY_SPEED  = 1.7f;

// 3x5 点阵字体：每行 3 bit，bit2 是最左
struct Glyph {
  char c;
  uint8_t rows[5];
};

const Glyph FONT[] = {
    {'A', {2, 5, 7, 5, 5}},
    {'B', {6, 5, 6, 5, 6}},
    {'C', {3, 4, 4, 4, 3}},
    {'D', {6, 5, 5, 5, 6}},
    {'E', {7, 4, 6, 4, 7}},
    {'F', {7, 4, 6, 4, 4}},
    {'G', {3, 4, 5, 5, 3}},
    {'H', {5, 5, 7, 5, 5}},
    {'I', {7, 2, 2, 2, 7}},
    {'J', {1, 1, 1, 5, 2}},
    {'K', {5, 5, 6, 5, 5}},
    {'L', {4, 4, 4, 4, 7}},
    {'M', {5, 7, 7, 5, 5}},
    {'N', {6, 5, 5, 5, 5}},
    {'O', {2, 5, 5, 5, 2}},
    {'P', {6, 5, 6, 4, 4}},
    {'Q', {2, 5, 5, 6, 3}},
    {'R', {6, 5, 6, 5, 5}},
    {'S', {3, 4, 2, 1, 6}},
    {'T', {7, 2, 2, 2, 2}},
    {'U', {5, 5, 5, 5, 7}},
    {'V', {5, 5, 5, 5, 2}},
    {'W', {5, 5, 7, 7, 5}},
    {'X', {5, 5, 2, 5, 5}},
    {'Y', {5, 5, 2, 2, 2}},
    {'Z', {7, 1, 2, 4, 7}},
    {'0', {7, 5, 5, 5, 7}},
    {'1', {2, 6, 2, 2, 7}},
    {'2', {6, 1, 2, 4, 7}},
    {'3', {6, 1, 2, 1, 6}},
    {'4', {5, 5, 7, 1, 1}},
    {'5', {7, 4, 6, 1, 6}},
    {'6', {3, 4, 7, 5, 7}},
    {'7', {7, 1, 2, 4, 4}},
    {'8', {7, 5, 7, 5, 7}},
    {'9', {7, 5, 7, 1, 6}},
    {'!', {2, 2, 2, 0, 2}},
    {'?', {3, 1, 2, 0, 2}},
    {'*', {2, 7, 2, 0, 0}},
    {'-', {0, 0, 7, 0, 0}},
    {'.', {0, 0, 0, 0, 2}},
    {'[', {6, 4, 4, 4, 6}},
    {']', {6, 1, 1, 1, 6}},
    {' ', {0, 0, 0, 0, 0}},
};

const uint8_t* glyphRows(char c) {
  if (c >= 'a' && c <= 'z') c = (char)(c - 'a' + 'A');
  for (unsigned i = 0; i < sizeof(FONT) / sizeof(FONT[0]); ++i) {
    if (FONT[i].c == c) return FONT[i].rows;
  }
  return FONT[sizeof(FONT) / sizeof(FONT[0]) - 1].rows;  // 未知字符画成空格
}

inline void putPx(uint8_t* fb, int x, int y, const Rgb& c) {
  if (x < 0 || x >= kPanelW || y < 0 || y >= kPanelH) return;
  uint8_t* p = fb + (y * kPanelW + x) * 3;
  p[0] = c.r;
  p[1] = c.g;
  p[2] = c.b;
}

inline Rgb fade(const Rgb& c, float k) {
  if (k < 0) k = 0;
  if (k > 1) k = 1;
  Rgb o;
  o.r = (uint8_t)(c.r * k);
  o.g = (uint8_t)(c.g * k);
  o.b = (uint8_t)(c.b * k);
  return o;
}

inline Rgb mix(const Rgb& a, const Rgb& b, float t) {
  Rgb o;
  o.r = (uint8_t)(a.r + (b.r - a.r) * t);
  o.g = (uint8_t)(a.g + (b.g - a.g) * t);
  o.b = (uint8_t)(a.b + (b.b - a.b) * t);
  return o;
}

}  // namespace

// ---------------------------------------------------------------- 生命周期

void Game::begin() {
  parseLevel();
  resetAll();
}

void Game::resetAll() {
  score_ = 0;
  lives_ = 3;
  coins_ = 0;
  partCount_ = 0;
  state_ = ST_TITLE;
  stateT_ = 0.0f;
  clock_ = 0.0f;
  resetLevel();
}

void Game::parseLevel() {
  for (int i = 0; i < kLevelW * kLevelH; ++i) map0_[i] = '.';
  int row = 0, col = 0;
  for (const char* p = LEVEL_MAP; *p; ++p) {
    if (*p == '\n') {
      ++row;
      col = 0;
      continue;
    }
    if (*p == '\r') continue;
    if (row >= kLevelH) break;
    if (col >= kLevelW) continue;
    map0_[row * kLevelW + col] = *p;
    ++col;
  }
  levelW_ = kLevelW;

  spawnX_ = 2;
  spawnY_ = 11;
  flagX_ = -1;
  for (int y = 0; y < kLevelH; ++y) {
    for (int x = 0; x < kLevelW; ++x) {
      char c = map0_[y * kLevelW + x];
      if (c == 'S') {
        spawnX_ = x;
        spawnY_ = y;
      } else if (c == 'F' && flagX_ < 0) {
        flagX_ = x;
      }
    }
  }
}

void Game::resetLevel() {
  memcpy(map_, map0_, sizeof(map_));
  enemyCount_ = 0;
  partCount_ = 0;
  coins_ = 0;
  for (int y = 0; y < kLevelH; ++y) {
    for (int x = 0; x < kLevelW; ++x) {
      char& c = map_[y * kLevelW + x];
      if (c == 'g') {
        c = '.';
        if (enemyCount_ < kMaxEnemies) {
          Enemy& e = enemies_[enemyCount_++];
          e.x = (float)x;
          e.y = (float)y;
          e.vx = -ENEMY_SPEED;
          e.vy = 0.0f;
          e.squash = 0.0f;
          e.alive = true;
        }
      } else if (c == 'S') {
        c = '.';
      }
    }
  }
  resetPlayer();
  cam_ = 0.0f;
}

void Game::resetPlayer() {
  px_ = (float)spawnX_;
  py_ = (float)spawnY_;
  vx_ = 0.0f;
  vy_ = 0.0f;
  onGround_ = false;
  jumpCut_ = false;
  coyote_ = 0.0f;
  jumpBuf_ = 0.0f;
  invuln_ = 1.0f;
  face_ = 1;
}

void Game::setState(GameState s) {
  state_ = s;
  stateT_ = 0.0f;
}

void Game::setPaused(bool on) {
  if (on && state_ == ST_PLAY) {
    setState(ST_PAUSE);
  } else if (!on && state_ == ST_PAUSE) {
    setState(ST_PLAY);
  }
}

void Game::togglePause() {
  if (state_ == ST_PLAY) {
    setState(ST_PAUSE);
    mario16Sound(SND_PAUSE);
  } else if (state_ == ST_PAUSE) {
    setState(ST_PLAY);
  }
}

Status Game::status() const {
  Status s;
  s.score = score_;
  s.lives = (uint8_t)(lives_ < 0 ? 0 : lives_);
  s.coins = (uint8_t)(coins_ > 255 ? 255 : coins_);
  s.state = (uint8_t)state_;
  int span = levelW_ - kPanelW;
  int prog = 100;
  if (span > 0) {
    prog = (int)((px_ / (float)span) * 100.0f);
    if (prog < 0) prog = 0;
    if (prog > 100) prog = 100;
  }
  s.progress = (uint8_t)prog;
  return s;
}

// ------------------------------------------------------------------- 更新

void Game::update(float dt, const Input& in) {
  if (dt < 0.0f) dt = 0.0f;
  if (dt > 0.05f) dt = 0.05f;
  clock_ += dt;
  stateT_ += dt;

  switch (state_) {
    case ST_TITLE:
      if (in.pressed & (KEY_A | KEY_START | KEY_UP)) {
        score_ = 0;
        lives_ = 3;
        resetLevel();
        setState(ST_READY);
        mario16Sound(SND_START);
      }
      break;

    case ST_READY:
      if (stateT_ >= 1.70f) setState(ST_PLAY);
      break;

    case ST_PLAY:
      if (in.pressed & KEY_START) {
        setState(ST_PAUSE);
        mario16Sound(SND_PAUSE);
      } else {
        updatePlay(dt, in);
      }
      break;

    case ST_PAUSE:
      if (in.pressed & (KEY_START | KEY_A)) setState(ST_PLAY);
      break;

    case ST_DEAD:
      updateParticles(dt);
      if (stateT_ >= 1.20f) {
        if (lives_ > 0) {
          resetLevel();
          setState(ST_READY);
        } else {
          setState(ST_GAMEOVER);
        }
      }
      break;

    case ST_GAMEOVER:
      updateParticles(dt);
      if ((in.pressed & (KEY_A | KEY_START)) || stateT_ > 8.0f) setState(ST_TITLE);
      break;

    case ST_WIN:
      updateParticles(dt);
      if (stateT_ > 4.0f) setState(ST_TITLE);
      break;
  }
}

void Game::updatePlay(float dt, const Input& in) {
  // 跳跃宽容时间
  coyote_ = onGround_ ? 0.09f : fmaxf(0.0f, coyote_ - dt);
  jumpBuf_ = (in.pressed & (KEY_A | KEY_UP)) ? 0.12f : fmaxf(0.0f, jumpBuf_ - dt);
  invuln_ = fmaxf(0.0f, invuln_ - dt);

  const bool left = (in.down & KEY_LEFT) != 0;
  const bool right = (in.down & KEY_RIGHT) != 0;
  const bool run = (in.down & KEY_B) != 0;
  const bool jumpHeld = (in.down & (KEY_A | KEY_UP)) != 0;

  // ---- 水平速度 ----
  float target = 0.0f;
  if (left && !right) target = -(run ? RUN_SPEED : WALK_SPEED);
  else if (right && !left) target = (run ? RUN_SPEED : WALK_SPEED);

  if (target == 0.0f) {
    float brake = onGround_ ? 55.0f : 22.0f;
    if (vx_ > 0.0f) vx_ = fmaxf(0.0f, vx_ - brake * dt);
    else if (vx_ < 0.0f) vx_ = fminf(0.0f, vx_ + brake * dt);
  } else {
    float accel = onGround_ ? ACCEL_GROUND : ACCEL_AIR;
    if (vx_ < target) vx_ = fminf(target, vx_ + accel * dt);
    else if (vx_ > target) vx_ = fmaxf(target, vx_ - accel * dt);
  }
  if (target > 0.0f) face_ = 1;
  else if (target < 0.0f) face_ = -1;

  // ---- 起跳 ----
  if (jumpBuf_ > 0.0f && coyote_ > 0.0f) {
    vy_ = -JUMP_V;
    onGround_ = false;
    jumpCut_ = false;
    jumpBuf_ = 0.0f;
    coyote_ = 0.0f;
    mario16Sound(SND_JUMP);
  }
  // 松开跳跃键就截断上升速度，实现“按得越久跳得越高”
  if (!jumpHeld && vy_ < -5.0f && !jumpCut_) {
    vy_ *= 0.55f;
    jumpCut_ = true;
  }

  // ---- 水平移动与碰撞 ----
  px_ += vx_ * dt;
  if (px_ < 0.0f) {
    px_ = 0.0f;
    vx_ = 0.0f;
  }
  if (rectSolid(px_, py_, (float)kPlayerW, (float)kPlayerH)) {
    if (vx_ > 0.0f) {
      int tx = (int)floorf(px_ + (float)kPlayerW - 0.001f);
      px_ = (float)tx - (float)kPlayerW;
    } else {
      int tx = (int)floorf(px_ + 0.001f);
      px_ = (float)(tx + 1);
    }
    vx_ = 0.0f;
  }

  // ---- 竖直移动与碰撞 ----
  vy_ += GRAV * dt;
  if (in.down & KEY_DOWN) vy_ += 16.0f * dt;   // 快速下落
  if (vy_ > MAX_FALL) vy_ = MAX_FALL;
  py_ += vy_ * dt;
  onGround_ = false;
  if (rectSolid(px_, py_, (float)kPlayerW, (float)kPlayerH)) {
    if (vy_ > 0.0f) {
      int ty = (int)floorf(py_ + (float)kPlayerH - 0.001f);
      py_ = (float)ty - (float)kPlayerH;
      onGround_ = true;
      jumpCut_ = false;
    } else if (vy_ < 0.0f) {
      int ty = (int)floorf(py_ + 0.001f);
      py_ = (float)(ty + 1);
    }
    vy_ = 0.0f;
  }

  collectCoins();
  updateEnemies(dt);
  checkEnemyHit();
  updateParticles(dt);
  if (state_ != ST_PLAY) return;

  // ---- 掉进坑里 ----
  if (py_ > (float)kPanelH + 1.0f) {
    killPlayer();
    return;
  }

  // ---- 到达旗杆 ----
  if (flagX_ >= 0 && px_ + (float)kPlayerW >= (float)flagX_ + 0.5f) {
    winLevel();
    return;
  }

  // ---- 摄像机 ----
  float targetCam = px_ + (float)kPlayerW * 0.5f - 6.0f;
  float maxCam = (float)(levelW_ - kPanelW);
  if (targetCam < 0.0f) targetCam = 0.0f;
  if (targetCam > maxCam) targetCam = maxCam;
  cam_ += (targetCam - cam_) * fminf(1.0f, 12.0f * dt);
}

void Game::updateEnemies(float dt) {
  for (int i = 0; i < enemyCount_; ++i) {
    Enemy& e = enemies_[i];
    if (!e.alive) {
      if (e.squash > 0.0f) e.squash -= dt;
      continue;
    }

    // 水平
    e.x += e.vx * dt;
    if (rectSolid(e.x, e.y, 2.0f, 2.0f)) {
      e.x -= e.vx * dt;
      e.vx = -e.vx;
    }

    // 竖直
    e.vy += GRAV * dt;
    if (e.vy > MAX_FALL) e.vy = MAX_FALL;
    e.y += e.vy * dt;
    if (rectSolid(e.x, e.y, 2.0f, 2.0f)) {
      if (e.vy > 0.0f) {
        int ty = (int)floorf(e.y + 2.0f - 0.001f);
        e.y = (float)ty - 2.0f;
      } else if (e.vy < 0.0f) {
        int ty = (int)floorf(e.y + 0.001f);
        e.y = (float)(ty + 1);
      }
      e.vy = 0.0f;
    }

    if (e.y > (float)kPanelH + 2.0f) e.alive = false;
  }
}

void Game::collectCoins() {
  int x0 = (int)floorf(px_ + 0.001f);
  int x1 = (int)floorf(px_ + (float)kPlayerW - 0.001f);
  int y0 = (int)floorf(py_ + 0.001f);
  int y1 = (int)floorf(py_ + (float)kPlayerH - 0.001f);
  for (int ty = y0; ty <= y1; ++ty) {
    if (ty < 0 || ty >= kPanelH) continue;
    for (int tx = x0; tx <= x1; ++tx) {
      if (tx < 0 || tx >= levelW_) continue;
      char& c = map_[ty * levelW_ + tx];
      if (c == 'o') {
        c = '.';
        ++coins_;
        score_ = (uint16_t)(score_ + 100);
        mario16Sound(SND_COIN);
        spawnParticles((float)tx + 0.5f, (float)ty + 0.5f, 255, 210, 40, 4);
      }
    }
  }
}

void Game::checkEnemyHit() {
  for (int i = 0; i < enemyCount_; ++i) {
    Enemy& e = enemies_[i];
    if (!e.alive) continue;
    bool overlap = px_ < e.x + 2.0f && px_ + (float)kPlayerW > e.x &&
                   py_ < e.y + 2.0f && py_ + (float)kPlayerH > e.y;
    if (!overlap) continue;

    // 从上面踩下去
    bool stomp = vy_ > 0.5f && (py_ + (float)kPlayerH) < e.y + 1.20f;
    if (stomp) {
      e.alive = false;
      e.squash = 0.30f;
      vy_ = -13.0f;
      jumpCut_ = true;
      score_ = (uint16_t)(score_ + 200);
      mario16Sound(SND_STOMP);
      spawnParticles(e.x + 1.0f, e.y + 0.5f, 200, 140, 60, 5);
      continue;
    }

    if (invuln_ > 0.0f) continue;
    killPlayer();
    return;
  }
}

void Game::killPlayer() {
  if (state_ != ST_PLAY) return;
  mario16Sound(SND_DIE);
  if (lives_ > 0) --lives_;
  setState(ST_DEAD);
  spawnParticles(px_ + 1.0f, py_ + 1.5f, 255, 80, 50, 6);
}

void Game::winLevel() {
  if (state_ != ST_PLAY) return;
  score_ = (uint16_t)(score_ + 500);
  mario16Sound(SND_WIN);
  setState(ST_WIN);
  for (int i = 0; i < 10; ++i) {
    spawnParticles(px_ + 1.0f, py_ + 1.5f, 255, 220, 80, 1);
  }
}

void Game::updateParticles(float dt) {
  int i = 0;
  while (i < partCount_) {
    Particle& p = parts_[i];
    p.vy += 28.0f * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.life -= dt;
    if (p.life <= 0.0f) {
      parts_[i] = parts_[--partCount_];
    } else {
      ++i;
    }
  }
}

void Game::spawnParticles(float x, float y, uint8_t r, uint8_t g, uint8_t b, int n) {
  for (int i = 0; i < n && partCount_ < kMaxParticles; ++i) {
    Particle& p = parts_[partCount_++];
    float a = (float)i * 2.39996f + clock_ * 5.0f;
    p.x = x;
    p.y = y;
    p.vx = cosf(a) * 3.2f;
    p.vy = sinf(a) * 3.2f - 2.5f;
    p.life0 = 0.35f + 0.08f * (float)(i % 3);
    p.life = p.life0;
    p.r = r;
    p.g = g;
    p.b = b;
  }
}

// ------------------------------------------------------------------ 碰撞

bool Game::solidTile(int tx, int ty) const {
  if (tx < 0 || tx >= levelW_) return true;   // 关卡左右是墙
  if (ty < 0 || ty >= kPanelH) return false;  // 上方和下方是空的
  char c = map_[ty * levelW_ + tx];
  return c == '#' || c == '=' || c == 'p';
}

bool Game::rectSolid(float x, float y, float w, float h) const {
  int x0 = (int)floorf(x + 0.001f);
  int x1 = (int)floorf(x + w - 0.001f);
  int y0 = (int)floorf(y + 0.001f);
  int y1 = (int)floorf(y + h - 0.001f);
  for (int ty = y0; ty <= y1; ++ty) {
    for (int tx = x0; tx <= x1; ++tx) {
      if (solidTile(tx, ty)) return true;
    }
  }
  return false;
}

// ------------------------------------------------------------------ 渲染

void Game::clear(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < kPanelW * kPanelH; ++i) {
    fb_[i * 3 + 0] = r;
    fb_[i * 3 + 1] = g;
    fb_[i * 3 + 2] = b;
  }
}

void Game::px(int x, int y, uint8_t r, uint8_t g, uint8_t b) {
  Rgb c;
  c.r = r;
  c.g = g;
  c.b = b;
  putPx(fb_, x, y, c);
}

void Game::dim(uint8_t k) {
  for (int i = 0; i < kPanelW * kPanelH; ++i) {
    uint8_t* p = fb_ + i * 3;
    p[0] = (uint8_t)((p[0] * k) >> 8);
    p[1] = (uint8_t)((p[1] * k) >> 8);
    p[2] = (uint8_t)((p[2] * k) >> 8);
  }
}

void Game::render(uint8_t* rgb) {
  switch (state_) {
    case ST_TITLE:
      drawTitle();
      break;
    case ST_GAMEOVER:
      clear(0, 0, 0);
      drawGameOverScreen();
      break;
    default:
      drawWorld();
      break;
  }

  switch (state_) {
    case ST_READY:
      drawReadyScreen();
      break;
    case ST_PAUSE:
      drawPauseScreen();
      break;
    case ST_DEAD:
      drawDeadScreen();
      break;
    case ST_WIN:
      drawWinScreen();
      break;
    default:
      break;
  }
  memcpy(rgb, fb_, sizeof(fb_));
}

void Game::drawWorld() {
  for (int y = 0; y < kPanelH; ++y) {
    float t = (float)y / (float)(kPanelH - 1);
    Rgb sky = mix(SKY_TOP, SKY_BOT, t);
    for (int x = 0; x < kPanelW; ++x) putPx(fb_, x, y, sky);
  }

  int cam = (int)lroundf(cam_);
  for (int sy = 0; sy < kPanelH; ++sy) {
    for (int sx = 0; sx < kPanelW; ++sx) {
      int wx = cam + sx;
      if (wx < 0 || wx >= levelW_) continue;
      char c = map_[sy * levelW_ + wx];
      switch (c) {
        case '#':
          putPx(fb_, sx, sy, sy == 14 ? GRASS : DIRT);
          break;
        case '=':
          putPx(fb_, sx, sy, ((wx * 7 + sy * 3) % 3 == 0) ? BRICK2 : BRICK);
          break;
        case 'p': {
          bool leftEdge = (wx == 0) || (map_[sy * levelW_ + wx - 1] != 'p');
          putPx(fb_, sx, sy, leftEdge ? PIPE_DARK : PIPE);
          break;
        }
        case 'o': {
          float s = 0.55f + 0.45f * (0.5f + 0.5f * sinf(clock_ * 6.0f + (float)wx * 0.7f));
          putPx(fb_, sx, sy, fade(COIN, s));
          break;
        }
        case 'F':
          putPx(fb_, sx, sy, POLE);
          break;
        default:
          break;
      }
    }
  }

  // 旗面
  if (flagX_ >= 0) {
    int fx = flagX_ - cam;
    for (int dy = 0; dy < 2; ++dy) {
      for (int dx = 1; dx <= 3; ++dx) {
        putPx(fb_, fx + dx, 6 + dy, (dx == 1 && dy == 0) ? WHITE : CLOTH);
      }
    }
  }

  drawEnemies();
  drawParticles();

  if (state_ == ST_PLAY || state_ == ST_READY || state_ == ST_PAUSE) {
    drawPlayerSprite();
  }
}

void Game::drawPlayerSprite() {
  // 复活后的短暂无敌：只在游戏进行中闪烁
  if (state_ == ST_PLAY && invuln_ > 0.0f && ((int)(clock_ * 20.0f) % 2) == 0) return;

  int sx = (int)lroundf(px_ - cam_);
  int sy = (int)lroundf(py_);

  putPx(fb_, sx, sy, CAP);
  putPx(fb_, sx + 1, sy, CAP);

  if (face_ > 0) {
    putPx(fb_, sx, sy + 1, CAP);
    putPx(fb_, sx + 1, sy + 1, SKIN);
  } else {
    putPx(fb_, sx, sy + 1, SKIN);
    putPx(fb_, sx + 1, sy + 1, CAP);
  }

  putPx(fb_, sx, sy + 2, OVERALL);
  putPx(fb_, sx + 1, sy + 2, OVERALL);
}

void Game::drawEnemies() {
  for (int i = 0; i < enemyCount_; ++i) {
    Enemy& e = enemies_[i];
    int sx = (int)lroundf(e.x - cam_);
    int sy = (int)lroundf(e.y);
    if (!e.alive) {
      if (e.squash > 0.0f) {
        putPx(fb_, sx, sy + 1, GOOMBA_FOOT);
        putPx(fb_, sx + 1, sy + 1, GOOMBA_FOOT);
      }
      continue;
    }
    putPx(fb_, sx, sy, GOOMBA);
    putPx(fb_, sx + 1, sy, GOOMBA);
    putPx(fb_, sx, sy + 1, GOOMBA_FOOT);
    putPx(fb_, sx + 1, sy + 1, GOOMBA_FOOT);
  }
}

void Game::drawParticles() {
  for (int i = 0; i < partCount_; ++i) {
    const Particle& p = parts_[i];
    Rgb c;
    c.r = p.r;
    c.g = p.g;
    c.b = p.b;
    putPx(fb_, (int)lroundf(p.x - cam_), (int)lroundf(p.y), fade(c, p.life / p.life0));
  }
}

// ------------------------------------------------------------------ 文字

void Game::drawChar(int x, int y, char c, uint8_t r, uint8_t g, uint8_t b) {
  const uint8_t* rows = glyphRows(c);
  for (int gy = 0; gy < 5; ++gy) {
    uint8_t bits = rows[gy];
    for (int gx = 0; gx < 3; ++gx) {
      if (bits & (4 >> gx)) px(x + gx, y + gy, r, g, b);
    }
  }
}

void Game::drawCharScaled(int x, int y, char c, int scale, uint8_t r, uint8_t g, uint8_t b) {
  const uint8_t* rows = glyphRows(c);
  for (int gy = 0; gy < 5; ++gy) {
    uint8_t bits = rows[gy];
    for (int gx = 0; gx < 3; ++gx) {
      if (!(bits & (4 >> gx))) continue;
      for (int dy = 0; dy < scale; ++dy) {
        for (int dx = 0; dx < scale; ++dx) {
          px(x + gx * scale + dx, y + gy * scale + dy, r, g, b);
        }
      }
    }
  }
}

void Game::drawText(int x, int y, const char* s, uint8_t r, uint8_t g, uint8_t b) {
  for (const char* p = s; *p; ++p) {
    drawChar(x, y, *p, r, g, b);
    x += 4;
  }
}

void Game::drawTextScaled(int x, int y, const char* s, int scale, uint8_t r, uint8_t g, uint8_t b) {
  for (const char* p = s; *p; ++p) {
    drawCharScaled(x, y, *p, scale, r, g, b);
    x += 4 * scale;
  }
}

void Game::drawMarquee(const char* s, float x, int y, uint8_t r, uint8_t g, uint8_t b) {
  float cur = x;
  for (const char* p = s; *p; ++p) {
    int xi = (int)lroundf(cur);
    if (xi > -4 && xi < kPanelW) drawChar(xi, y, *p, r, g, b);
    cur += 4.0f;
  }
}

// -------------------------------------------------------------- 各个画面

void Game::drawTitle() {
  for (int y = 0; y < kPanelH; ++y) {
    float t = (float)y / (float)(kPanelH - 1);
    Rgb sky = mix(SKY_TOP, SKY_BOT, t);
    for (int x = 0; x < kPanelW; ++x) putPx(fb_, x, y, sky);
  }
  for (int x = 0; x < kPanelW; ++x) {
    putPx(fb_, x, 14, GRASS);
    putPx(fb_, x, 15, DIRT);
  }

  // 站在原地的小马里奥
  putPx(fb_, 2, 11, CAP);
  putPx(fb_, 3, 11, CAP);
  putPx(fb_, 2, 12, CAP);
  putPx(fb_, 3, 12, SKIN);
  putPx(fb_, 2, 13, OVERALL);
  putPx(fb_, 3, 13, OVERALL);

  // 上下浮动的金币
  int bob = (int)lroundf(sinf(clock_ * 4.0f) * 1.2f);
  putPx(fb_, 11, 7 + bob, fade(COIN, 0.85f + 0.15f * sinf(clock_ * 8.0f)));

  const char* msg = "SUPER MARIO 16 * A=START * ";
  float width = (float)strlen(msg) * 4.0f;
  float phase = fmodf(clock_ * 20.0f, width + 20.0f);
  drawMarquee(msg, 16.0f - phase, 1, GOLD.r, GOLD.g, GOLD.b);
}

void Game::drawReadyScreen() {
  if (stateT_ < 1.35f) {
    int n = 3 - (int)(stateT_ / 0.45f);
    if (n < 1) n = 1;
    char buf[2] = {(char)('0' + n), 0};
    drawCharScaled(5, 3, buf[0], 2, GOLD.r, GOLD.g, GOLD.b);
  } else {
    drawTextScaled(1, 3, "GO", 2, GOLD.r, GOLD.g, GOLD.b);
  }
}

void Game::drawPauseScreen() {
  dim(96);
  if (((int)(clock_ * 4.0f) % 2) == 0) {
    drawText(0, 9, "STOP", WHITE.r, WHITE.g, WHITE.b);
  }
}

void Game::drawDeadScreen() {
  if (stateT_ > 0.7f) return;
  if (((int)(stateT_ * 14.0f) % 2) == 0) {
    for (int i = 0; i < kPanelW * kPanelH; ++i) {
      fb_[i * 3 + 0] = 220;
      fb_[i * 3 + 1] = 30;
      fb_[i * 3 + 2] = 20;
    }
  }
}

void Game::drawGameOverScreen() {
  drawText(0, 2, "GAME", RED.r, RED.g, RED.b);
  bool blink = ((int)(clock_ * 3.0f) % 2) == 0;
  if (blink) {
    drawText(0, 8, "OVER", WHITE.r, WHITE.g, WHITE.b);
  } else {
    drawText(0, 8, "OVER", GOLD.r, GOLD.g, GOLD.b);
  }
}

void Game::drawWinScreen() {
  dim(110);
  drawText(2, 2, "WIN", GOLD.r, GOLD.g, GOLD.b);

  // 金币数：居中显示
  char buf[8];
  int n = coins_ > 999 ? 999 : coins_;
  int len = 0;
  if (n == 0) {
    buf[len++] = '0';
  } else {
    char tmp[8];
    int t = 0;
    while (n > 0 && t < 7) {
      tmp[t++] = (char)('0' + n % 10);
      n /= 10;
    }
    while (t > 0) buf[len++] = tmp[--t];
  }
  buf[len] = 0;
  int tw = len * 4 - 1;
  drawText((kPanelW - tw) / 2, 11, buf, WHITE.r, WHITE.g, WHITE.b);
}

}  // namespace mario16
