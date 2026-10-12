#include "command_dispatcher.h"
#include "display_manager.h"
#include "audio_hal.h"
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <cJSON.h>
#include <esp_log.h>
#include <driver/usb_serial_jtag.h>

static const char* TAG = "CmdDispatcher";

static void SendReply(const char* msg)
{
    if (!msg) return;
    usb_serial_jtag_write_bytes(msg, strlen(msg), pdMS_TO_TICKS(100));
    printf("%s", msg);
    fflush(stdout);
}

CommandDispatcher& CommandDispatcher::GetInstance()
{
    static CommandDispatcher instance;
    return instance;
}

CommandDispatcher::CommandDispatcher()
    : task_handle_(nullptr),
      mic_task_handle_(nullptr),
      is_running_(false),
      mic_streaming_(false)
{
}

CommandDispatcher::~CommandDispatcher()
{
    is_running_ = false;
    mic_streaming_ = false;
    if (task_handle_) {
        vTaskDelete(task_handle_);
        task_handle_ = nullptr;
    }
    if (mic_task_handle_) {
        vTaskDelete(mic_task_handle_);
        mic_task_handle_ = nullptr;
    }
}
void CommandDispatcher::SetMicStreaming(bool enabled)
{
    mic_streaming_ = enabled;
    AudioHAL::GetInstance().EnableMic(enabled);
    ESP_LOGI(TAG, "Mic streaming toggled: %s", enabled ? "ENABLED" : "DISABLED");
}

esp_err_t CommandDispatcher::StartSerialTask(UBaseType_t priority, BaseType_t core_id)
{
    if (is_running_) return ESP_OK;

    is_running_ = true;
    BaseType_t ret = xTaskCreatePinnedToCore(
        SerialTaskTrampoline,
        "serial_cmd_task",
        8192,
        this,
        priority,
        &task_handle_,
        core_id
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create serial command task!");
        is_running_ = false;
        return ESP_FAIL;
    }

    // 启动后台麦克风音频流上传任务 (同样绑定至 Core 0，不抢占 Core 1 渲染任务)
    xTaskCreatePinnedToCore(
        MicTaskTrampoline,
        "mic_stream_task",
        4096,
        this,
        priority > 1 ? priority - 1 : 1,
        &mic_task_handle_,
        core_id
    );

    ESP_LOGI(TAG, "Serial & Mic command tasks started on Core %d", (int)core_id);
    return ESP_OK;
}

void CommandDispatcher::SerialTaskTrampoline(void* arg)
{
    CommandDispatcher* dispatcher = static_cast<CommandDispatcher*>(arg);
    dispatcher->SerialTaskLoop();
}

void CommandDispatcher::MicTaskTrampoline(void* arg)
{
    CommandDispatcher* dispatcher = static_cast<CommandDispatcher*>(arg);
    dispatcher->MicTaskLoop();
}

void CommandDispatcher::MicTaskLoop()
{
    const size_t chunk_samples = 240;
    int16_t mic_buf[chunk_samples];
    uint8_t packet[4 + chunk_samples * sizeof(int16_t)];
    packet[0] = 0x55;
    packet[1] = 0xAA;

    int err_cnt = 0;
    while (is_running_) {
        if (mic_streaming_) {
            size_t samples_read = 0;
            esp_err_t ret = AudioHAL::GetInstance().ReadMic(mic_buf, chunk_samples, &samples_read, 200);
            if (ret == ESP_OK && samples_read > 0) {
                uint16_t payload_bytes = (uint16_t)(samples_read * sizeof(int16_t));
                packet[2] = (payload_bytes >> 8) & 0xFF;
                packet[3] = payload_bytes & 0xFF;
                memcpy(&packet[4], mic_buf, payload_bytes);
                usb_serial_jtag_write_bytes(packet, 4 + payload_bytes, pdMS_TO_TICKS(50));
            } else {
                if (++err_cnt % 50 == 1) {
                    ESP_LOGW(TAG, "ReadMic failed: %s, read=%u", esp_err_to_name(ret), (unsigned)samples_read);
                }
                vTaskDelay(pdMS_TO_TICKS(20));
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
    vTaskDelete(NULL);
}

void CommandDispatcher::SerialTaskLoop()
{
    ESP_LOGI(TAG, "Serial command listening loop entered (USB-Serial-JTAG Hardware Driver).");

    usb_serial_jtag_driver_config_t config = {
        .tx_buffer_size = 512,
        .rx_buffer_size = 4096,
    };
    esp_err_t err = usb_serial_jtag_driver_install(&config);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "usb_serial_jtag_driver_install: %s (might already be installed)", esp_err_to_name(err));
    }

    char line_buf[256];
    int line_idx = 0;
    uint8_t rx_buf[512];

    enum AudioRxState {
        STATE_TEXT = 0,
        STATE_AUDIO_SYNC2,
        STATE_AUDIO_LEN1,
        STATE_AUDIO_LEN2,
        STATE_AUDIO_PAYLOAD
    };
    AudioRxState rx_state = STATE_TEXT;
    uint16_t audio_expected_len = 0;
    uint16_t audio_received_len = 0;
    static uint8_t audio_payload[2048];

    while (is_running_) {
        int bytes_read = usb_serial_jtag_read_bytes(rx_buf, sizeof(rx_buf), pdMS_TO_TICKS(10));
        if (bytes_read > 0) {
            for (int i = 0; i < bytes_read; i++) {
                uint8_t b = rx_buf[i];

                switch (rx_state) {
                    case STATE_TEXT:
                        if (b == 0xAA) {
                            rx_state = STATE_AUDIO_SYNC2;
                        } else if (b == '\n' || b == '\r') {
                            if (line_idx > 0) {
                                line_buf[line_idx] = '\0';
                                ProcessLine(line_buf);
                                line_idx = 0;
                            }
                        } else if (line_idx < (int)sizeof(line_buf) - 1) {
                            line_buf[line_idx++] = (char)b;
                        }
                        break;

                    case STATE_AUDIO_SYNC2:
                        if (b == 0x55) {
                            rx_state = STATE_AUDIO_LEN1;
                        } else {
                            // 0xAA 不是帧头，回退处理
                            if (line_idx < (int)sizeof(line_buf) - 2) {
                                line_buf[line_idx++] = (char)0xAA;
                                line_buf[line_idx++] = (char)b;
                            }
                            rx_state = STATE_TEXT;
                        }
                        break;

                    case STATE_AUDIO_LEN1:
                        audio_expected_len = ((uint16_t)b) << 8;
                        rx_state = STATE_AUDIO_LEN2;
                        break;

                    case STATE_AUDIO_LEN2:
                        audio_expected_len |= (uint16_t)b;
                        audio_received_len = 0;
                        if (audio_expected_len == 0 || audio_expected_len > sizeof(audio_payload)) {
                            // 异常长度，重置状态
                            rx_state = STATE_TEXT;
                        } else {
                            rx_state = STATE_AUDIO_PAYLOAD;
                        }
                        break;

                    case STATE_AUDIO_PAYLOAD: {
                        size_t needed = audio_expected_len - audio_received_len;
                        size_t available = bytes_read - i;
                        size_t take = (needed < available) ? needed : available;
                        memcpy(&audio_payload[audio_received_len], &rx_buf[i], take);
                        audio_received_len += take;
                        i += (take - 1); // for-loop 自增 i++
                        if (audio_received_len >= audio_expected_len) {
                            size_t sample_count = audio_received_len / sizeof(int16_t);
                            AudioHAL::GetInstance().PlayMonoPcm((const int16_t*)audio_payload, sample_count);
                            rx_state = STATE_TEXT;
                        }
                        break;
                    }
                }
            }
        }
    }

    vTaskDelete(NULL);
}

void CommandDispatcher::SendStatus()
{
    DisplayManager& dm = DisplayManager::GetInstance();
    int mode = (int)dm.GetMode();
    bool cd_active = dm.IsCountdownActive();
    uint32_t cd_rem = dm.GetCountdownRemainingSeconds();

    char status_buf[160];
    snprintf(status_buf, sizeof(status_buf),
             "{\"type\":\"status\",\"mode\":%d,\"countdown_active\":%s,\"countdown_remaining\":%u}\r\n",
             mode, cd_active ? "true" : "false", (unsigned int)cd_rem);
    SendReply(status_buf);
}

void CommandDispatcher::ProcessLine(const char* line)
{
    if (!line || strlen(line) == 0) return;

    // 去除前导空白
    while (*line == ' ' || *line == '\t') line++;
    if (*line == '\0') return;

    ESP_LOGI(TAG, ">>> [收到外部指令]: %s", line);

    // 1. 旧版音乐频谱流 (兼容中阶 "f,beat,b0,b1...")
    if (strncmp(line, "f,", 2) == 0) {
        DisplayManager::GetInstance().FeedSpectrumSerial(line);
        return;
    }

    // 2. JSON 格式指令
    if (*line == '{') {
        if (ProcessJsonCommand(line)) {
            SendReply("{\"status\":\"ok\"}\r\n");
            return;
        }
    }

    // 3. 极速纯文本短语指令
    if (ProcessTextCommand(line)) {
        SendReply("{\"status\":\"ok\"}\r\n");
        return;
    }

    ESP_LOGW(TAG, "Unrecognized command: %s", line);
    SendReply("{\"status\":\"error\",\"msg\":\"unknown_command\"}\r\n");
}

bool CommandDispatcher::ProcessJsonCommand(const char* json_str)
{
    cJSON* root = cJSON_Parse(json_str);
    if (!root) {
        ESP_LOGE(TAG, "JSON parse error: %s", json_str);
        return false;
    }

    cJSON* cmd_item = cJSON_GetObjectItem(root, "cmd");
    if (!cmd_item || !cJSON_IsString(cmd_item)) {
        cJSON_Delete(root);
        return false;
    }

    const char* cmd = cmd_item->valuestring;
    DisplayManager& dm = DisplayManager::GetInstance();

    // {"cmd":"countdown", "seconds":60}
    if (strcasecmp(cmd, "countdown") == 0) {
        cJSON* sec_item = cJSON_GetObjectItem(root, "seconds");
        if (sec_item && cJSON_IsNumber(sec_item)) {
            dm.StartCountdown((uint32_t)sec_item->valueint);
            cJSON_Delete(root);
            return true;
        }
    }
    // {"cmd":"stop_countdown"}
    else if (strcasecmp(cmd, "stop_countdown") == 0) {
        dm.StopCountdown();
        cJSON_Delete(root);
        return true;
    }
    // {"cmd":"mode", "val":4}
    else if (strcasecmp(cmd, "mode") == 0) {
        cJSON* val_item = cJSON_GetObjectItem(root, "val");
        if (val_item && cJSON_IsNumber(val_item)) {
            dm.SetMode(val_item->valueint);
            cJSON_Delete(root);
            return true;
        }
    }
    // {"cmd":"brightness", "val":20}
    else if (strcasecmp(cmd, "brightness") == 0) {
        cJSON* val_item = cJSON_GetObjectItem(root, "val");
        if (val_item && cJSON_IsNumber(val_item)) {
            dm.SetBrightness((uint8_t)val_item->valueint);
            cJSON_Delete(root);
            return true;
        }
    }
    // {"cmd":"status"}
    else if (strcasecmp(cmd, "status") == 0) {
        SendStatus();
        cJSON_Delete(root);
        return true;
    }
    // {"cmd":"beep"}
    else if (strcasecmp(cmd, "beep") == 0) {
        AudioHAL::GetInstance().PlayBeep(1000, 200);
        cJSON_Delete(root);
        return true;
    }
    // {"cmd":"mic", "enable":true}
    else if (strcasecmp(cmd, "mic") == 0) {
        cJSON* en_item = cJSON_GetObjectItem(root, "enable");
        if (en_item && cJSON_IsBool(en_item)) {
            SetMicStreaming(cJSON_IsTrue(en_item));
            cJSON_Delete(root);
            return true;
        }
    }
    // {"cmd":"game", "name":"snake", "dx":1, "dy":0}
    else if (strcasecmp(cmd, "game") == 0) {
        cJSON* name_item = cJSON_GetObjectItem(root, "name");
        if (name_item && cJSON_IsString(name_item)) {
            if (strcasecmp(name_item->valuestring, "snake") == 0) {
                cJSON* dx = cJSON_GetObjectItem(root, "dx");
                cJSON* dy = cJSON_GetObjectItem(root, "dy");
                if (dx && dy) {
                    dm.SnakeMove(dx->valueint, dy->valueint);
                    cJSON_Delete(root);
                    return true;
                }
            } else if (strcasecmp(name_item->valuestring, "tetris") == 0) {
                cJSON* act = cJSON_GetObjectItem(root, "action");
                if (act && cJSON_IsString(act)) {
                    if (strcasecmp(act->valuestring, "left") == 0) dm.TetrisMove(-1);
                    else if (strcasecmp(act->valuestring, "right") == 0) dm.TetrisMove(1);
                    else if (strcasecmp(act->valuestring, "rot") == 0) dm.TetrisRotate();
                    else if (strcasecmp(act->valuestring, "drop") == 0) dm.TetrisDrop();
                    cJSON_Delete(root);
                    return true;
                }
            }
        }
    }

    cJSON_Delete(root);
    return false;
}

bool CommandDispatcher::ProcessTextCommand(const char* text_str)
{
    DisplayManager& dm = DisplayManager::GetInstance();

    // 1. 倒计时: "countdown 60" / "cd 60"
    int seconds = 0;
    if (sscanf(text_str, "countdown %d", &seconds) == 1 ||
        sscanf(text_str, "cd %d", &seconds) == 1) {
        dm.StartCountdown((uint32_t)seconds);
        return true;
    }
    if (strcasecmp(text_str, "stop_countdown") == 0 || strcasecmp(text_str, "stop_cd") == 0) {
        dm.StopCountdown();
        return true;
    }

    // 2. 模式数字切换: "mode 23"
    int mode_num = -1;
    if (sscanf(text_str, "mode %d", &mode_num) == 1) {
        dm.SetMode(mode_num);
        return true;
    }

    // 3. 模式快捷英文别名
    if (strcasecmp(text_str, "off") == 0)           { dm.SetMode(DisplayMode::OFF); return true; }
    if (strcasecmp(text_str, "rainbow") == 0)       { dm.SetMode(DisplayMode::RAINBOW_WAVE); return true; }
    if (strcasecmp(text_str, "aurora") == 0)        { dm.SetMode(DisplayMode::AURORA_BREATHE); return true; }
    if (strcasecmp(text_str, "meteor") == 0)        { dm.SetMode(DisplayMode::METEOR_TRAIL); return true; }
    if (strcasecmp(text_str, "stars") == 0)         { dm.SetMode(DisplayMode::TWINKLE_STARS); return true; }
    if (strcasecmp(text_str, "cycle") == 0)         { dm.SetMode(DisplayMode::COLOR_CYCLE); return true; }
    if (strcasecmp(text_str, "rain") == 0)          { dm.SetMode(DisplayMode::MATRIX_RAIN); return true; }
    if (strcasecmp(text_str, "ripple") == 0)        { dm.SetMode(DisplayMode::CENTER_RIPPLE); return true; }
    if (strcasecmp(text_str, "smile") == 0)         { dm.SetMode(DisplayMode::FACE_SMILE); return true; }
    if (strcasecmp(text_str, "cry") == 0)           { dm.SetMode(DisplayMode::FACE_CRY); return true; }
    if (strcasecmp(text_str, "neutral") == 0)       { dm.SetMode(DisplayMode::FACE_NEUTRAL); return true; }
    if (strcasecmp(text_str, "dynamic") == 0)       { dm.SetMode(DisplayMode::FACE_DYNAMIC); return true; }
    if (strcasecmp(text_str, "spectrum") == 0)      { dm.SetMode(DisplayMode::AUDIO_SPECTRUM); return true; }
    if (strcasecmp(text_str, "snake") == 0)         { dm.SetMode(DisplayMode::SNAKE_GAME); return true; }
    if (strcasecmp(text_str, "tetris") == 0)        { dm.SetMode(DisplayMode::TETRIS_GAME); return true; }
    if (strcasecmp(text_str, "fire") == 0)          { dm.SetMode(DisplayMode::CYBER_FIRE); return true; }
    if (strcasecmp(text_str, "matrix") == 0)        { dm.SetMode(DisplayMode::MATRIX_RAIN_PRO); return true; }
    if (strcasecmp(text_str, "beep") == 0)          { AudioHAL::GetInstance().PlayBeep(1000, 200); return true; }
    if (strcasecmp(text_str, "mic on") == 0)        { SetMicStreaming(true); return true; }
    if (strcasecmp(text_str, "mic off") == 0)       { SetMicStreaming(false); return true; }

    // 4. 亮度微调: "brightness 25" / "b 25"
    int br = 0;
    if (sscanf(text_str, "brightness %d", &br) == 1 || sscanf(text_str, "b %d", &br) == 1) {
        dm.SetBrightness((uint8_t)br);
        return true;
    }

    // 5. 状态查询: "status"
    if (strcasecmp(text_str, "status") == 0) {
        SendStatus();
        return true;
    }

    // 6. 游戏快速指令
    int dx = 0, dy = 0;
    if (sscanf(text_str, "snake %d %d", &dx, &dy) == 2) {
        dm.SnakeMove(dx, dy);
        return true;
    }
    if (strcasecmp(text_str, "tetris left") == 0)  { dm.TetrisMove(-1); return true; }
    if (strcasecmp(text_str, "tetris right") == 0) { dm.TetrisMove(1); return true; }
    if (strcasecmp(text_str, "tetris rot") == 0)   { dm.TetrisRotate(); return true; }
    if (strcasecmp(text_str, "tetris drop") == 0)  { dm.TetrisDrop(); return true; }

    return false;
}
