#include "jetson_uart.h"
#include "command_dispatcher.h"
#include "display_manager.h"
#include "arcade_manager.h"
#include <cJSON.h>
#include <esp_log.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

namespace jetson {

static const char* TAG = "JetsonUart";

JetsonUart& JetsonUart::GetInstance() {
    static JetsonUart instance;
    return instance;
}

JetsonUart::JetsonUart() {
    tx_mutex_ = xSemaphoreCreateMutex();
}

JetsonUart::~JetsonUart() {
    is_running_ = false;
    if (task_handle_) {
        vTaskDelete(task_handle_);
        task_handle_ = nullptr;
    }
    if (initialized_) {
        uart_driver_delete(port_);
        initialized_ = false;
    }
    if (tx_mutex_) {
        vSemaphoreDelete(tx_mutex_);
        tx_mutex_ = nullptr;
    }
}

esp_err_t JetsonUart::Init(uart_port_t port, gpio_num_t rx_pin, gpio_num_t tx_pin, int baud_rate) {
    port_ = port;
    rx_pin_ = rx_pin;
    tx_pin_ = tx_pin;
    baud_rate_ = baud_rate;

    uart_config_t uart_config = {
        .baud_rate = baud_rate_,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .rx_flow_ctrl_thresh = 0,
        .source_clk = UART_SCLK_DEFAULT,
        .flags = 0,
    };

    esp_err_t err = uart_param_config(port_, &uart_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_param_config failed: %s", esp_err_to_name(err));
        return err;
    }

    // Explicit pin routing: TX = tx_pin (GPIO9), RX = rx_pin (GPIO8)
    err = uart_set_pin(port_, tx_pin_, rx_pin_, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_set_pin (TX=%d, RX=%d) failed: %s", (int)tx_pin_, (int)rx_pin_, esp_err_to_name(err));
        return err;
    }

    constexpr int rx_buf_size = 2048;
    constexpr int tx_buf_size = 2048;
    err = uart_driver_install(port_, rx_buf_size, tx_buf_size, 0, nullptr, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_driver_install failed: %s", esp_err_to_name(err));
        return err;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "Jetson UART initialized on Port %d: RX=GPIO%d, TX=GPIO%d, Baud=%d, 8N1 (No Flow Control)",
             (int)port_, (int)rx_pin_, (int)tx_pin_, baud_rate_);
    return ESP_OK;
}

esp_err_t JetsonUart::StartTask(UBaseType_t priority, BaseType_t core_id) {
    if (!initialized_) {
        ESP_LOGE(TAG, "Cannot start Jetson UART task: driver not initialized");
        return ESP_ERR_INVALID_STATE;
    }
    if (is_running_) {
        return ESP_OK;
    }

    is_running_ = true;
    BaseType_t ret = xTaskCreatePinnedToCore(
        UartTaskTrampoline,
        "jetson_uart_rx",
        4096,
        this,
        priority,
        &task_handle_,
        core_id
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create Jetson UART task!");
        is_running_ = false;
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Jetson UART background worker started on Core %d (priority=%d)", (int)core_id, (int)priority);
    return ESP_OK;
}

void JetsonUart::UartTaskTrampoline(void* arg) {
    static_cast<JetsonUart*>(arg)->UartTaskLoop();
}

void JetsonUart::UartTaskLoop() {
    uint8_t chunk[256];
    char reply_buf[1024];

    ESP_LOGI(TAG, "Jetson UART listening loop entered.");

    while (is_running_) {
        // Read incoming bytes with 20ms timeout; if Jetson is disconnected or idle, gracefully yields
        int bytes_read = uart_read_bytes(port_, chunk, sizeof(chunk), pdMS_TO_TICKS(20));
        if (bytes_read <= 0) {
            continue;
        }

        receiver_.FeedBytes(
            chunk,
            bytes_read,
            [this, &reply_buf](const char* frame) {
                rx_frames_++;
                reply_buf[0] = '\0';
                ProcessCommand(frame, reply_buf, sizeof(reply_buf));
                if (reply_buf[0] != '\0') {
                    SendLine(reply_buf);
                }
            },
            [this, &reply_buf](size_t max_bytes) {
                rx_errors_++;
                ESP_LOGW(TAG, "Jetson frame exceeded max length %zu, discarding tail until newline", max_bytes);
                snprintf(reply_buf, sizeof(reply_buf),
                         "{\"status\":\"error\",\"error\":\"frame_overflow\",\"max_bytes\":%zu}",
                         max_bytes);
                SendLine(reply_buf);
            }
        );
    }

    vTaskDelete(nullptr);
}

esp_err_t JetsonUart::SendRaw(const void* data, size_t len) {
    if (!initialized_ || !data || len == 0) return ESP_ERR_INVALID_STATE;

    if (tx_mutex_) xSemaphoreTake(tx_mutex_, portMAX_DELAY);
    int written = uart_write_bytes(port_, data, len);
    if (tx_mutex_) xSemaphoreGive(tx_mutex_);

    if (written < 0) return ESP_FAIL;
    return ESP_OK;
}

esp_err_t JetsonUart::SendLine(const char* line) {
    if (!line) return ESP_ERR_INVALID_ARG;
    size_t len = strlen(line);
    if (len == 0) return ESP_OK;

    if (tx_mutex_) xSemaphoreTake(tx_mutex_, portMAX_DELAY);
    uart_write_bytes(port_, line, len);
    uart_write_bytes(port_, "\n", 1);
    tx_frames_++;
    if (tx_mutex_) xSemaphoreGive(tx_mutex_);

    return ESP_OK;
}

void JetsonUart::ProcessCommand(const char* line, char* out_reply, size_t out_reply_size) {
    if (!line || !out_reply || out_reply_size == 0) return;
    out_reply[0] = '\0';

    // Strip leading whitespace
    while (*line && isspace((unsigned char)*line)) line++;
    if (!*line) return;

    // Extract potential req_id from JSON
    cJSON* root = cJSON_Parse(line);
    cJSON* req_id_item = nullptr;
    char req_id_str[64] = {0};

    if (root) {
        req_id_item = cJSON_GetObjectItemCaseSensitive(root, "req_id");
        if (!req_id_item) req_id_item = cJSON_GetObjectItemCaseSensitive(root, "id");
        if (req_id_item) {
            if (cJSON_IsString(req_id_item) && req_id_item->valuestring) {
                snprintf(req_id_str, sizeof(req_id_str), "%s", req_id_item->valuestring);
            } else if (cJSON_IsNumber(req_id_item)) {
                snprintf(req_id_str, sizeof(req_id_str), "%lld", (long long)req_id_item->valuedouble);
            }
        }
    }

    auto append_req_id = [&](cJSON* reply_json) {
        if (req_id_str[0] != '\0' && reply_json) {
            if (req_id_item && cJSON_IsNumber(req_id_item)) {
                cJSON_AddNumberToObject(reply_json, "req_id", req_id_item->valuedouble);
            } else {
                cJSON_AddStringToObject(reply_json, "req_id", req_id_str);
            }
        }
    };

    if (root) {
        cJSON* cmd_item = cJSON_GetObjectItemCaseSensitive(root, "cmd");
        if (!cmd_item) cmd_item = cJSON_GetObjectItemCaseSensitive(root, "action");
        const char* cmd = (cmd_item && cJSON_IsString(cmd_item)) ? cmd_item->valuestring : "";

        if (!strcasecmp(cmd, "ping")) {
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddBoolToObject(resp, "pong", true);
            cJSON_AddStringToObject(resp, "version", kProtocolVersion);
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "get_status") || !strcasecmp(cmd, "status")) {
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddStringToObject(resp, "version", kProtocolVersion);
            cJSON_AddStringToObject(resp, "board", "esp32s3_pro");
            cJSON_AddNumberToObject(resp, "mode", static_cast<int>(DisplayManager::GetInstance().GetMode()));
            cJSON_AddNumberToObject(resp, "brightness", DisplayManager::GetInstance().GetBrightness());
            cJSON_AddBoolToObject(resp, "mic_streaming", CommandDispatcher::GetInstance().IsMicStreaming());
            cJSON_AddNumberToObject(resp, "arcade_active", arcade::ArcadeManager::GetInstance().IsActive() ? 1 : 0);
            cJSON_AddNumberToObject(resp, "arcade_game_id", arcade::ArcadeManager::GetInstance().GetCurrentGameId());
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "version")) {
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddStringToObject(resp, "version", kProtocolVersion);
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else {
            // Business commands whitelist check:
            // Only forward agreed commands to CommandDispatcher:
            // mode, brightness, b, board_led, led, arcade, pet, kurisu, countdown, stop_countdown, stop_cd, beep, key
            bool allowed = false;
            const char* const kAllowedCmds[] = {
                "mode", "brightness", "b", "board_led", "led", "arcade",
                "pet", "kurisu", "countdown", "stop_countdown", "stop_cd", "beep", "key"
            };
            for (const auto& a : kAllowedCmds) {
                if (!strcasecmp(cmd, a)) {
                    allowed = true;
                    break;
                }
            }

            bool ok = false;
            if (allowed) {
                ok = CommandDispatcher::GetInstance().ProcessLine(line, false, true);
            }

            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", ok ? "ok" : "error");
            cJSON_AddBoolToObject(resp, "executed", ok);
            if (!allowed) {
                cJSON_AddStringToObject(resp, "error", "unauthorized_command");
            } else if (!ok) {
                cJSON_AddStringToObject(resp, "error", "command_rejected");
            }
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        }
        cJSON_Delete(root);
        return;
    }

    // Fallback: Plain text parsing (e.g. "ping", "status", "mode 1", "countdown 60", "stop_countdown")
    if (!strcasecmp(line, "ping")) {
        snprintf(out_reply, out_reply_size, "{\"status\":\"ok\",\"pong\":true,\"version\":\"%s\"}", kProtocolVersion);
    } else if (!strcasecmp(line, "status") || !strcasecmp(line, "get_status")) {
        snprintf(out_reply, out_reply_size,
                 "{\"status\":\"ok\",\"version\":\"%s\",\"board\":\"esp32s3_pro\",\"mode\":%d,\"brightness\":%d}",
                 kProtocolVersion,
                 static_cast<int>(DisplayManager::GetInstance().GetMode()),
                 DisplayManager::GetInstance().GetBrightness());
    } else if (!strcasecmp(line, "version")) {
        snprintf(out_reply, out_reply_size, "{\"status\":\"ok\",\"version\":\"%s\"}", kProtocolVersion);
    } else {
        bool allowed = false;
        if (!strncmp(line, "f,", 2)) {
            allowed = true; // Spectrum
        } else {
            const char* const kAllowedPrefixes[] = {
                "mode ", "brightness ", "b ", "board_led ", "led ", "countdown ", "arcade "
            };
            for (const auto& p : kAllowedPrefixes) {
                if (!strncasecmp(line, p, strlen(p))) {
                    allowed = true;
                    break;
                }
            }
            if (!allowed) {
                const char* const kAllowedExact[] = {
                    "pet", "kurisu", "stop_countdown", "stop_cd", "beep",
                    "snake", "tetris", "fire", "matrix", "spectrum"
                };
                for (const auto& e : kAllowedExact) {
                    if (!strcasecmp(line, e)) {
                        allowed = true;
                        break;
                    }
                }
            }
        }

        if (allowed) {
            bool ok = CommandDispatcher::GetInstance().ProcessLine(line, false, true);
            if (ok) {
                snprintf(out_reply, out_reply_size, "{\"status\":\"ok\",\"executed\":true,\"cmd\":\"%s\"}", line);
            } else {
                snprintf(out_reply, out_reply_size, "{\"status\":\"error\",\"error\":\"command_rejected\",\"cmd\":\"%s\"}", line);
            }
        } else {
            snprintf(out_reply, out_reply_size, "{\"status\":\"error\",\"error\":\"unauthorized_command\",\"cmd\":\"%s\"}", line);
        }
    }
}

} // namespace jetson
