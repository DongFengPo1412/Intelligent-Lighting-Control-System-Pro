#include "command_dispatcher.h"
#include "display_manager.h"
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <cJSON.h>
#include <esp_log.h>

static const char* TAG = "CmdDispatcher";

CommandDispatcher& CommandDispatcher::GetInstance()
{
    static CommandDispatcher instance;
    return instance;
}

CommandDispatcher::CommandDispatcher()
    : task_handle_(nullptr),
      is_running_(false)
{
}

CommandDispatcher::~CommandDispatcher()
{
    is_running_ = false;
    if (task_handle_) {
        vTaskDelete(task_handle_);
        task_handle_ = nullptr;
    }
}

esp_err_t CommandDispatcher::StartSerialTask(UBaseType_t priority, BaseType_t core_id)
{
    if (is_running_) return ESP_OK;

    is_running_ = true;
    BaseType_t ret = xTaskCreatePinnedToCore(
        SerialTaskTrampoline,
        "serial_cmd_task",
        4096,
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

    ESP_LOGI(TAG, "Serial command task started on Core %d (priority %d)", (int)core_id, (int)priority);
    return ESP_OK;
}

void CommandDispatcher::SerialTaskTrampoline(void* arg)
{
    CommandDispatcher* dispatcher = static_cast<CommandDispatcher*>(arg);
    dispatcher->SerialTaskLoop();
}

void CommandDispatcher::SerialTaskLoop()
{
    ESP_LOGI(TAG, "Serial command listening loop entered.");

    char buf[256];
    int idx = 0;

    while (is_running_) {
        int c = fgetc(stdin);
        if (c != EOF && c > 0) {
            if (c == '\n' || c == '\r') {
                if (idx > 0) {
                    buf[idx] = '\0';
                    ProcessLine(buf);
                    idx = 0;
                }
            } else if (idx < (int)sizeof(buf) - 1) {
                buf[idx++] = (char)c;
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(10));
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

    printf("{\"type\":\"status\",\"mode\":%d,\"countdown_active\":%s,\"countdown_remaining\":%u}\r\n",
           mode, cd_active ? "true" : "false", (unsigned int)cd_rem);
    fflush(stdout);
}

void CommandDispatcher::ProcessLine(const char* line)
{
    if (!line || strlen(line) == 0) return;

    // 去除前导空白
    while (*line == ' ' || *line == '\t') line++;
    if (*line == '\0') return;

    // 1. 旧版音乐频谱流 (兼容中阶 "f,beat,b0,b1...")
    if (strncmp(line, "f,", 2) == 0) {
        DisplayManager::GetInstance().FeedSpectrumSerial(line);
        return;
    }

    // 2. JSON 格式指令
    if (*line == '{') {
        if (ProcessJsonCommand(line)) {
            printf("{\"status\":\"ok\"}\r\n");
            fflush(stdout);
            return;
        }
    }

    // 3. 极速纯文本短语指令
    if (ProcessTextCommand(line)) {
        printf("{\"status\":\"ok\"}\r\n");
        fflush(stdout);
        return;
    }

    ESP_LOGW(TAG, "Unrecognized command: %s", line);
    printf("{\"status\":\"error\",\"msg\":\"unknown_command\"}\r\n");
    fflush(stdout);
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
