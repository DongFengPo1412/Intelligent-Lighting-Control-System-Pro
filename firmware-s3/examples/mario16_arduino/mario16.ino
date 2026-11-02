/*
 * mario16.ino —— 16x16 WS2812 灯板上的迷你超级马里奥（ESP32-S3 / ESP32）
 *
 * 玩法：手机通过 BLE 发送按键 → 板子跑横版卷轴马里奥 → 灯板显示。
 *      也可以直接用 USB 串口（115200）发同样的文本命令来控制，方便调试。
 *
 * 依赖（Arduino IDE 库管理器）：
 *   * FastLED（3.6 及以上）
 *   * ESP32 Arduino 核心 2.0.x 或 3.x（需自带 BLE 库，默认已包含）
 *
 * 接线：
 *   灯板 DIN -> GPIO4（见 LED_PIN），5V / GND 与灯板共地；
 *   256 颗 WS2812 全白约 15A，务必用独立 5V 电源，并加 1000uF 电容。
 *
 * 手机端：phone/controller.html 用 Web Bluetooth 连 "MARIO16"。
 * BLE 协议（Nordic UART Service）：
 *   服务 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
 *   写入 6E400002-...（手机 -> 板子）   通知 6E400003-...（板子 -> 手机）
 *
 * 命令（文本行，\n 结尾）。两种写法等价，手机页面用的是更短的简写：
 *
 *   按键（按住/松开，每次 2 个字符）：
 *     L1 L0  左        R1 R0  右
 *     U1 U0  上(跳)    D1 D0  下
 *     A1 A0  跳        B1 B0  加速跑
 *     S1 S0  开始/暂停 X1 X0  选择
 *     例：按下跳跃 = "A1"，松开 = "A0"
 *
 *   控制命令（# 开头）：
 *     #R        回到标题重开
 *     #P        暂停 / 继续
 *     #T        灯板测试图案（校准方向用），6 秒后自动返回
 *     #B80      亮度 0-255
 *     #?        立刻回一条状态
 *
 *   JSON 写法（方便用 nRF Connect 等蓝牙调试 App 手打）：
 *     {"cmd":"key","k":"left","v":1}
 *     {"cmd":"reset"} / {"cmd":"pause"} / {"cmd":"test"} / {"cmd":"ping"}
 *     {"cmd":"bright","v":80}
 */

#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(ARDUINO_ARCH_ESP32)
#error "本固件依赖 ESP32 Arduino 核心（ESP32 / ESP32-S3 / ESP32-C3 均可）"
#endif

#include <FastLED.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

#include "mario_game.h"

// ============================== 用户配置 ==============================
#ifndef LED_PIN
#define LED_PIN 4           // 灯板 DIN 接的 GPIO（ESP32-S3 常用 4/5/18/48）
#endif
#ifndef NUM_LEDS
#define NUM_LEDS 256
#endif
#ifndef LED_BRIGHTNESS
#define LED_BRIGHTNESS 60   // 0-255，60 大约是 23% 亮度，够亮又不爆电流
#endif
#ifndef MATRIX_SERPENTINE
#define MATRIX_SERPENTINE 1 // 1 = 蛇形走线（大多数 16x16 面板）
#endif
#ifndef MATRIX_FLIP_X
#define MATRIX_FLIP_X 0     // 左右镜像
#endif
#ifndef MATRIX_FLIP_Y
#define MATRIX_FLIP_Y 0     // 上下镜像
#endif
#ifndef BUZZER_PIN
#define BUZZER_PIN -1       // 有源/无源蜂鸣器接的 GPIO，-1 表示不装
#endif
#ifndef BLE_DEVICE_NAME
#define BLE_DEVICE_NAME "MARIO16"
#endif

#define NUS_SERVICE_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_RX_UUID      "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
#define NUS_TX_UUID      "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

// ============================== 全局对象 ==============================
static CRGB leds[NUM_LEDS];
static uint8_t frameBuf[16 * 16 * 3];
static mario16::Game game;

static BLECharacteristic* txChar = nullptr;
static volatile bool bleConnected = false;
static uint32_t lastNotifyMs = 0;

// 从 BLE 中断/任务里写进来的命令字节
static const size_t kRxCap = 256;
static volatile uint8_t rxBuf[kRxCap];
static volatile size_t rxHead = 0;
static volatile size_t rxTail = 0;
static portMUX_TYPE rxMux = portMUX_INITIALIZER_UNLOCKED;

// 按键状态
static volatile uint16_t gDown = 0;
static volatile uint16_t gPressed = 0;
static portMUX_TYPE keyMux = portMUX_INITIALIZER_UNLOCKED;

// 灯板测试模式
static bool testMode = false;
static uint32_t testStartMs = 0;
static uint32_t testEndMs = 0;

static uint32_t lastStepUs = 0;

// ============================== 灯板映射 ==============================
// 坐标: x 0..15 从左到右, y 0..15 从上到下
// 如果画面上下颠倒/左右镜像，改上面的 MATRIX_FLIP_X / MATRIX_FLIP_Y；
// 如果画面像“打乱的斜纹”，多半是蛇形/逐行不一致，改 MATRIX_SERPENTINE。
static inline uint16_t XY(uint8_t x, uint8_t y) {
  uint8_t px = MATRIX_FLIP_X ? (uint8_t)(15 - x) : x;
  uint8_t py = MATRIX_FLIP_Y ? (uint8_t)(15 - y) : y;
  if (MATRIX_SERPENTINE && (py & 1)) px = (uint8_t)(15 - px);
  return (uint16_t)py * 16u + px;
}

// ============================== 声音 ==============================
#if BUZZER_PIN >= 0
static uint32_t buzzerOffMs = 0;

static void buzzerSetup() {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BUZZER_PIN, 2000, 8);
#else
  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER_PIN, 0);
#endif
}

static void buzzerTone(uint16_t freq, uint16_t ms) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWriteTone(BUZZER_PIN, freq);
#else
  ledcWriteTone(0, freq);
#endif
  buzzerOffMs = millis() + ms;
}

static void buzzerTick() {
  if (buzzerOffMs != 0 && (int32_t)(millis() - buzzerOffMs) >= 0) {
    buzzerOffMs = 0;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWriteTone(BUZZER_PIN, 0);
#else
    ledcWriteTone(0, 0);
#endif
  }
}

// 覆盖 mario_game.cpp 里的 weak 空实现
void mario16Sound(uint8_t id) {
  switch (id) {
    case mario16::SND_JUMP:  buzzerTone(620, 90); break;
    case mario16::SND_COIN:  buzzerTone(1320, 70); break;
    case mario16::SND_STOMP: buzzerTone(220, 90); break;
    case mario16::SND_DIE:   buzzerTone(180, 450); break;
    case mario16::SND_WIN:   buzzerTone(990, 500); break;
    case mario16::SND_START: buzzerTone(880, 120); break;
    case mario16::SND_PAUSE: buzzerTone(440, 80); break;
    default: break;
  }
}
#else
static inline void buzzerSetup() {}
static inline void buzzerTick() {}
#endif

// ============================== 输入 ==============================
static int keyBitFromChar(char c) {
  switch (c) {
    case 'l': case 'L': return mario16::KEY_LEFT;
    case 'r': case 'R': return mario16::KEY_RIGHT;
    case 'u': case 'U': return mario16::KEY_UP;
    case 'd': case 'D': return mario16::KEY_DOWN;
    case 'a': case 'A': return mario16::KEY_A;
    case 'b': case 'B': return mario16::KEY_B;
    case 's': case 'S': return mario16::KEY_START;
    case 'x': case 'X': return mario16::KEY_SELECT;
    default: return -1;
  }
}

static int keyBitFromName(const char* name) {
  if (!strcmp(name, "left")) return mario16::KEY_LEFT;
  if (!strcmp(name, "right")) return mario16::KEY_RIGHT;
  if (!strcmp(name, "up")) return mario16::KEY_UP;
  if (!strcmp(name, "down")) return mario16::KEY_DOWN;
  if (!strcmp(name, "a") || !strcmp(name, "jump")) return mario16::KEY_A;
  if (!strcmp(name, "b") || !strcmp(name, "run")) return mario16::KEY_B;
  if (!strcmp(name, "start") || !strcmp(name, "pause")) return mario16::KEY_START;
  if (!strcmp(name, "select")) return mario16::KEY_SELECT;
  return -1;
}

static void setKey(int bit, bool down) {
  if (bit < 0) return;
  uint16_t mask = (uint16_t)bit;
  portENTER_CRITICAL(&keyMux);
  if (down) {
    if (!(gDown & mask)) gPressed |= mask;
    gDown |= mask;
  } else {
    gDown &= (uint16_t)~mask;
  }
  portEXIT_CRITICAL(&keyMux);
}

// ============================== JSON 迷你解析 ==============================
static const char* jsonFind(const char* s, const char* key) {
  char pat[24];
  snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char* p = strstr(s, pat);
  if (p == nullptr) return nullptr;
  p += strlen(pat);
  while (*p == ' ' || *p == ':' || *p == '\t') ++p;
  return p;
}

static bool jsonInt(const char* s, const char* key, int* out) {
  const char* p = jsonFind(s, key);
  if (p == nullptr) return false;
  *out = atoi(p);
  return true;
}

static bool jsonStr(const char* s, const char* key, char* out, size_t n) {
  const char* p = jsonFind(s, key);
  if (p == nullptr || n == 0) return false;
  if (*p == '"') ++p;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < n) out[i++] = *p++;
  out[i] = 0;
  return i > 0;
}

// ============================== 灯板测试 ==============================
static void startPanelTest(uint32_t ms) {
  testMode = true;
  testStartMs = millis();
  testEndMs = testStartMs + ms;
}

static void renderPanelTest() {
  uint32_t t = millis() - testStartMs;
  CRGB qTL(110, 0, 0), qTR(0, 110, 0), qBL(0, 0, 110), qBR(70, 70, 70);
  for (int y = 0; y < 16; ++y) {
    for (int x = 0; x < 16; ++x) {
      CRGB c = (y < 8) ? (x < 8 ? qTL : qTR) : (x < 8 ? qBL : qBR);
      if (((x + y + (int)(t / 120)) % 16) == 0) c = CRGB(200, 200, 200);
      leds[XY((uint8_t)x, (uint8_t)y)] = c;
    }
  }
  if (((t / 400) % 2) == 0) leds[XY(0, 0)] = CRGB(255, 200, 0);
  if (((t / 400) % 2) == 1) leds[XY(15, 15)] = CRGB(255, 200, 0);
}

// ============================== 命令处理 ==============================
static void handleCommand(char* s) {
  while (*s == ' ' || *s == '\t') ++s;
  size_t n = strlen(s);
  while (n > 0 && (s[n - 1] == ' ' || s[n - 1] == '\t' || s[n - 1] == '\r')) s[--n] = 0;
  if (n == 0) return;

  if (s[0] == '#') {
    switch (s[1]) {
      case 'R': case 'r':
        game.resetAll();
        Serial.println("[cmd] reset");
        break;
      case 'P': case 'p':
        game.togglePause();
        break;
      case 'T': case 't':
        startPanelTest(6000);
        break;
      case '?':
        lastNotifyMs = 0;
        break;
      case 'B': case 'b': {
        int v = atoi(s + 2);
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        FastLED.setBrightness((uint8_t)v);
        break;
      }
      default:
        break;
    }
    return;
  }

  if (s[0] == '{') {
    char cmd[16];
    if (!jsonStr(s, "cmd", cmd, sizeof(cmd))) return;
    if (!strcmp(cmd, "key")) {
      char k[16];
      if (!jsonStr(s, "k", k, sizeof(k))) return;
      int v = 1;
      jsonInt(s, "v", &v);
      setKey(keyBitFromName(k), v != 0);
    } else if (!strcmp(cmd, "reset") || !strcmp(cmd, "restart")) {
      game.resetAll();
      Serial.println("[cmd] reset");
    } else if (!strcmp(cmd, "pause")) {
      game.togglePause();
    } else if (!strcmp(cmd, "bright")) {
      int v = LED_BRIGHTNESS;
      if (jsonInt(s, "v", &v)) {
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        FastLED.setBrightness((uint8_t)v);
      }
    } else if (!strcmp(cmd, "test")) {
      startPanelTest(6000);
    } else if (!strcmp(cmd, "ping")) {
      lastNotifyMs = 0;
    }
    return;
  }

  // 简写: L1 / A0 / S1 ...
  if (n >= 2) {
    int bit = keyBitFromChar(s[0]);
    if (bit >= 0) {
      setKey(bit, s[1] != '0');
      return;
    }
  }

  // 第二套简写: "left 1" / "a 0"
  char name[16];
  int v = 1;
  if (sscanf(s, "%15s %d", name, &v) >= 1) {
    int bit = keyBitFromName(name);
    if (bit >= 0) setKey(bit, v != 0);
  }
}

// ============================== 接收缓冲 ==============================
static void rxPush(const uint8_t* data, size_t len) {
  portENTER_CRITICAL(&rxMux);
  for (size_t i = 0; i < len; ++i) {
    size_t next = (rxHead + 1) % kRxCap;
    if (next == rxTail) break;  // 缓冲区满，丢弃
    rxBuf[rxHead] = data[i];
    rxHead = next;
  }
  portEXIT_CRITICAL(&rxMux);
}

static void pollRing() {
  static char line[192];
  static size_t len = 0;
  for (;;) {
    uint8_t b = 0;
    bool got = false;
    portENTER_CRITICAL(&rxMux);
    if (rxTail != rxHead) {
      b = rxBuf[rxTail];
      rxTail = (rxTail + 1) % kRxCap;
      got = true;
    }
    portEXIT_CRITICAL(&rxMux);
    if (!got) return;

    if (b == '\n' || b == '\r') {
      if (len > 0) {
        line[len] = 0;
        handleCommand(line);
        len = 0;
      }
    } else if (len < sizeof(line) - 1) {
      line[len++] = (char)b;
    } else {
      len = 0;
    }
  }
}

static void drainSerial() {
  int avail = Serial.available();
  if (avail <= 0) return;
  uint8_t tmp[64];
  int n = 0;
  while (avail-- > 0 && n < (int)sizeof(tmp)) tmp[n++] = (uint8_t)Serial.read();
  if (n > 0) rxPush(tmp, (size_t)n);
}

// ============================== BLE ==============================
class MarioServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer*) override {
    bleConnected = true;
    lastNotifyMs = 0;
    Serial.println("[BLE] 手机已连接");
  }

  void onDisconnect(BLEServer*) override {
    bleConnected = false;
    game.setPaused(true);
    portENTER_CRITICAL(&keyMux);
    gDown = 0;
    gPressed = 0;
    portEXIT_CRITICAL(&keyMux);
    Serial.println("[BLE] 手机断开，重新广播");
    BLEDevice::startAdvertising();
  }
};

class MarioRxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* c) override {
    std::string v = c->getValue();
    if (!v.empty()) rxPush((const uint8_t*)v.data(), v.size());
  }
};

static void bleInit() {
  BLEDevice::init(BLE_DEVICE_NAME);
  BLEDevice::setMTU(247);

  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new MarioServerCallbacks());

  BLEService* svc = server->createService(NUS_SERVICE_UUID);

  txChar = svc->createCharacteristic(NUS_TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  txChar->addDescriptor(new BLE2902());

  BLECharacteristic* rx = svc->createCharacteristic(
      NUS_RX_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new MarioRxCallbacks());

  svc->start();

  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(NUS_SERVICE_UUID);
  adv->setScanResponse(true);
  adv->setMinPreferred(0x06);
  BLEDevice::startAdvertising();

  Serial.printf("[BLE] 广播中，设备名 %s\n", BLE_DEVICE_NAME);
}

static void notifyStatus(bool force = false) {
  if (!bleConnected || txChar == nullptr) return;
  uint32_t now = millis();
  if (!force && now - lastNotifyMs < 250) return;
  lastNotifyMs = now;

  mario16::Status s = game.status();
  char buf[96];
  snprintf(buf, sizeof(buf), "{\"s\":%u,\"l\":%u,\"c\":%u,\"st\":%u,\"p\":%u}\n", (unsigned)s.score,
           (unsigned)s.lives, (unsigned)s.coins, (unsigned)s.state, (unsigned)s.progress);
  txChar->setValue((uint8_t*)buf, strlen(buf));
  txChar->notify();
}

// ============================== 主流程 ==============================
void setup() {
  Serial.begin(115200);
  delay(150);
  Serial.println();
  Serial.println("=== 16x16 MARIO (WS2812) ===");
  Serial.printf("LED_PIN=%d  NUM_LEDS=%d  SERPENTINE=%d  FLIP_X=%d  FLIP_Y=%d\n", LED_PIN, NUM_LEDS,
                MATRIX_SERPENTINE, MATRIX_FLIP_X, MATRIX_FLIP_Y);

  FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(LED_BRIGHTNESS);
  FastLED.clear(true);

  buzzerSetup();

  game.begin();
  game.render(frameBuf);   // 先画一帧标题画面

  bleInit();

  lastStepUs = micros();
  Serial.println("[game] 准备就绪：手机连 BLE，或串口直接发 L1 / A1 测试");
}

void loop() {
  drainSerial();
  pollRing();
  buzzerTick();

  uint32_t nowUs = micros();
  if (nowUs - lastStepUs < 20000) {  // 约 50fps；FastLED.show() 本身要 7~8ms
    delay(1);
    return;
  }
  float dt = (float)(nowUs - lastStepUs) / 1000000.0f;
  lastStepUs = nowUs;
  if (dt > 0.05f) dt = 0.05f;

  uint16_t down, pressed;
  portENTER_CRITICAL(&keyMux);
  down = gDown;
  pressed = gPressed;
  gPressed = 0;
  portEXIT_CRITICAL(&keyMux);

  // 灯板测试模式
  if (testMode) {
    if ((int32_t)(millis() - testEndMs) >= 0) {
      testMode = false;
    } else {
      renderPanelTest();
      FastLED.show();
      notifyStatus();
      return;
    }
  }

  mario16::Input in;
  in.down = down;
  in.pressed = pressed;

  game.update(dt, in);
  game.render(frameBuf);

  for (int y = 0; y < 16; ++y) {
    for (int x = 0; x < 16; ++x) {
      const uint8_t* p = frameBuf + (y * 16 + x) * 3;
      leds[XY((uint8_t)x, (uint8_t)y)] = CRGB(p[0], p[1], p[2]);
    }
  }
  FastLED.show();

  notifyStatus();
}
