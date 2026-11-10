#include "jetson_uart.h"
#include "command_dispatcher.h"
#include "display_manager.h"
#include "arcade_manager.h"
#include "canvas_protocol.h"
#include <cJSON.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

#if defined(ESP_PLATFORM)
#include <esp_log.h>
#endif

namespace jetson {

static const char* TAG = "JetsonUart";

JetsonUart& JetsonUart::GetInstance() {
    static JetsonUart instance;
    return instance;
}

JetsonUart::JetsonUart() {
#if defined(ESP_PLATFORM)
    tx_mutex_ = xSemaphoreCreateMutex();
#endif
}

JetsonUart::~JetsonUart() {
    is_running_ = false;
#if defined(ESP_PLATFORM)
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
#endif
}

esp_err_t JetsonUart::Init(uart_port_t port, gpio_num_t rx_pin, gpio_num_t tx_pin, int baud_rate) {
    port_ = port;
    rx_pin_ = rx_pin;
    tx_pin_ = tx_pin;
    baud_rate_ = baud_rate;

#if defined(ESP_PLATFORM)
    uart_config_t uart_config{};
    uart_config.baud_rate = baud_rate_;
    uart_config.data_bits = UART_DATA_8_BITS;
    uart_config.parity    = UART_PARITY_DISABLE;
    uart_config.stop_bits = UART_STOP_BITS_1;
    uart_config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    uart_config.rx_flow_ctrl_thresh = 0;
    uart_config.source_clk = UART_SCLK_DEFAULT;

    esp_err_t err = uart_param_config(port_, &uart_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "uart_param_config failed: %s", esp_err_to_name(err));
        return err;
    }

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
#else
    initialized_ = true;
    return 0;
#endif
}

esp_err_t JetsonUart::StartTask(UBaseType_t priority, BaseType_t core_id) {
    if (!initialized_) {
#if defined(ESP_PLATFORM)
        ESP_LOGE(TAG, "Cannot start Jetson UART task: driver not initialized");
#endif
        return -1;
    }
    if (is_running_) {
        return 0;
    }

    is_running_ = true;
#if defined(ESP_PLATFORM)
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
#else
    return 0;
#endif
}

void JetsonUart::UartTaskTrampoline(void* arg) {
    static_cast<JetsonUart*>(arg)->UartTaskLoop();
}

void JetsonUart::UartTaskLoop() {
    uint8_t chunk[256];
    char reply_buf[1024];

#if defined(ESP_PLATFORM)
    ESP_LOGI(TAG, "Jetson UART listening loop entered.");

    while (is_running_) {
        int bytes_read = uart_read_bytes(port_, chunk, sizeof(chunk), pdMS_TO_TICKS(20));

        uint32_t now = get_current_millis();

        // 1. Input watchdog: auto-release held arcade keys if inactive for >500ms
        if (held_keys_ != 0 && (now - last_input_time_ms_ > 500)) {
            ReleaseHeldKeys();
            ESP_LOGW(TAG, "Input watchdog: auto-released held arcade keys after 500ms silence");
        }

        // 2. Canvas incomplete frame timeout
        canvas::CanvasAssembler::GetInstance().CheckTimeout(now, 500);

        // 3. Binary frame parser timeout check (>200ms)
        receiver_.CheckTimeout(now, [this, &reply_buf](size_t err_code) {
            rx_errors_++;
            snprintf(reply_buf, sizeof(reply_buf),
                     "{\"status\":\"error\",\"type\":\"bin_frame\",\"error\":\"binary_timeout\"}");
            SendLine(reply_buf);
        });

        // 4. Session timeout check (>15s)
        if (session_state_ == SessionState::ACTIVE && (now - last_session_ping_ms_ > 15000)) {
            session_state_ = SessionState::EXPIRED;
            ESP_LOGW(TAG, "Jetson vision session expired (>15s inactivity)");
        }

        if (bytes_read <= 0) {
            continue;
        }

        receiver_.FeedBytes(
            chunk,
            bytes_read,
            [this, &reply_buf](const char* text_frame) {
                rx_frames_++;
                reply_buf[0] = '\0';
                ProcessCommand(text_frame, reply_buf, sizeof(reply_buf));
                if (reply_buf[0] != '\0') {
                    SendLine(reply_buf);
                }
            },
            [this, &reply_buf](const canvas::BinaryHeader& header, const uint8_t* payload) {
                rx_frames_++;
                reply_buf[0] = '\0';
                ProcessBinaryFrame(header, payload, reply_buf, sizeof(reply_buf));
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
#endif
}

esp_err_t JetsonUart::SendRaw(const void* data, size_t len) {
    if (!initialized_ || !data || len == 0) return -1;

#if defined(ESP_PLATFORM)
    if (tx_mutex_) xSemaphoreTake(tx_mutex_, portMAX_DELAY);
    int written = uart_write_bytes(port_, data, len);
    if (tx_mutex_) xSemaphoreGive(tx_mutex_);

    if (written < 0) return ESP_FAIL;
    return ESP_OK;
#else
    return 0;
#endif
}

esp_err_t JetsonUart::SendLine(const char* line) {
    if (!line) return -1;
    size_t len = strlen(line);
    if (len == 0) return 0;

#if defined(ESP_PLATFORM)
    if (tx_mutex_) xSemaphoreTake(tx_mutex_, portMAX_DELAY);
    uart_write_bytes(port_, line, len);
    uart_write_bytes(port_, "\n", 1);
    tx_frames_++;
    if (tx_mutex_) xSemaphoreGive(tx_mutex_);

    return ESP_OK;
#else
    tx_frames_++;
    return 0;
#endif
}

void JetsonUart::SetSession(const char* session_id) {
    if (session_id && session_id[0] != '\0') {
        snprintf(session_id_, sizeof(session_id_), "%s", session_id);
    } else {
        session_id_[0] = '\0';
    }
}

void JetsonUart::ClearSession() {
    session_id_[0] = '\0';
    session_state_ = SessionState::IDLE;
    ReleaseHeldKeys();
}

void JetsonUart::StartSession(const char* session_id, uint16_t initial_seq) {
    if (session_id && session_id[0] != '\0') {
        SetSession(session_id);
    }
    session_state_ = SessionState::ACTIVE;
    session_start_ms_ = get_current_millis();
    last_session_ping_ms_ = session_start_ms_;
    last_input_time_ms_ = session_start_ms_;
    canvas::CanvasAssembler::GetInstance().ResetSequence(initial_seq);
    ReleaseHeldKeys();
}

void JetsonUart::StopSession() {
    session_state_ = SessionState::STOPPED;
    ReleaseHeldKeys();
    canvas::CanvasAssembler::GetInstance().Reset();
    DisplayManager& dm = DisplayManager::GetInstance();
    // 跨来源画布所有权保护：仅当画布模式确实属于 Jetson 且无人工手动覆盖时才安全回退至彩虹波
    if (!dm.IsManualOverrideActive() &&
        dm.GetMode() == DisplayMode::PIXEL_CANVAS &&
        dm.GetCanvasSource() == DisplayManager::CanvasSource::JETSON) {
        dm.SetMode(DisplayMode::RAINBOW_WAVE);
        dm.SetCanvasSource(DisplayManager::CanvasSource::NONE);
    }
}

bool JetsonUart::PingSession() {
    if (GetSessionState() == SessionState::ACTIVE) {
        last_session_ping_ms_ = get_current_millis();
        return true;
    }
    return false;
}

bool JetsonUart::IsManualOverrideActive() const {
    return DisplayManager::GetInstance().IsManualOverrideActive();
}

void JetsonUart::SetManualOverride(bool active) {
    DisplayManager::GetInstance().SetManualOverride(active);
}

void JetsonUart::ReleaseHeldKeys() {
    if (held_keys_ != 0) {
        DisplayManager::GetInstance().ArcadeInput(0, 0);
        held_keys_ = 0;
    }
}

void JetsonUart::ProcessBinaryFrame(const canvas::BinaryHeader& header, const uint8_t* payload,
                                   char* out_reply, size_t out_reply_size) {
    if (!out_reply || out_reply_size == 0) return;
    out_reply[0] = '\0';

    JetsonUart& ju = GetInstance();
    SessionState state = ju.GetSessionState();
    if (state == SessionState::STOPPED || state == SessionState::EXPIRED) {
        cJSON* resp = cJSON_CreateObject();
        cJSON_AddStringToObject(resp, "status", "error");
        cJSON_AddStringToObject(resp, "type", "bin_frame");
        cJSON_AddNumberToObject(resp, "frame_id", header.frame_seq);
        cJSON_AddBoolToObject(resp, "committed", false);
        cJSON_AddBoolToObject(resp, "displayed", false);
        cJSON_AddNumberToObject(resp, "received_bytes", 0);
        cJSON_AddBoolToObject(resp, "mode_overridden", DisplayManager::GetInstance().IsManualOverrideActive());
        cJSON_AddStringToObject(resp, "error", (state == SessionState::STOPPED) ? "session_stopped" : "session_expired");
        char* rendered = cJSON_PrintUnformatted(resp);
        if (rendered) {
            snprintf(out_reply, out_reply_size, "%s", rendered);
            cJSON_free(rendered);
        }
        cJSON_Delete(resp);
        return;
    }

    auto res = canvas::CanvasAssembler::GetInstance().ProcessBinaryFrame(header, payload);

    DisplayManager& dm = DisplayManager::GetInstance();
    bool manual_overridden = dm.IsManualOverrideActive();
    bool displayed = res.committed && !manual_overridden && (dm.GetMode() == DisplayMode::PIXEL_CANVAS);

    cJSON* resp = cJSON_CreateObject();
    cJSON_AddStringToObject(resp, "status", res.success ? "ok" : "error");
    cJSON_AddStringToObject(resp, "type", "bin_frame");
    cJSON_AddNumberToObject(resp, "frame_id", res.frame_id);
    cJSON_AddBoolToObject(resp, "committed", res.committed);
    cJSON_AddBoolToObject(resp, "displayed", displayed);
    cJSON_AddNumberToObject(resp, "received_bytes", res.received_bytes);
    cJSON_AddBoolToObject(resp, "mode_overridden", manual_overridden);
    if (!res.success && res.error_msg) {
        cJSON_AddStringToObject(resp, "error", res.error_msg);
    }

    char* rendered = cJSON_PrintUnformatted(resp);
    if (rendered) {
        snprintf(out_reply, out_reply_size, "%s", rendered);
        cJSON_free(rendered);
    }
    cJSON_Delete(resp);
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
            DisplayManager& dm = DisplayManager::GetInstance();
            JetsonUart& ju = GetInstance();
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddStringToObject(resp, "version", kProtocolVersion);
            cJSON_AddStringToObject(resp, "board", "esp32s3_pro");
            cJSON_AddNumberToObject(resp, "mode", static_cast<int>(dm.GetMode()));
            cJSON_AddNumberToObject(resp, "brightness", dm.GetBrightness());
            cJSON_AddBoolToObject(resp, "mic_streaming", CommandDispatcher::GetInstance().IsMicStreaming());
            cJSON_AddNumberToObject(resp, "arcade_active", arcade::ArcadeManager::GetInstance().IsActive() ? 1 : 0);
            cJSON_AddNumberToObject(resp, "arcade_game_id", arcade::ArcadeManager::GetInstance().GetCurrentGameId());
            cJSON_AddBoolToObject(resp, "canvas_active", dm.GetMode() == DisplayMode::PIXEL_CANVAS);
            cJSON_AddNumberToObject(resp, "held_keys", ju.held_keys_);
            cJSON_AddNumberToObject(resp, "canvas_frames", canvas::CanvasAssembler::GetInstance().GetCommittedFrames());
            if (ju.session_id_[0] != '\0') {
                cJSON_AddStringToObject(resp, "session_id", ju.session_id_);
            }
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
        } else if (!strcasecmp(cmd, "get_capabilities") || !strcasecmp(cmd, "capabilities")) {
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddStringToObject(resp, "version", kProtocolVersion);

            cJSON* feats = cJSON_CreateArray();
            const char* const kFeats[] = {
                "mode_switch", "brightness", "board_led", "fingertip_tracker", "light_sandbox",
                "desk_pet", "celebrate", "pet_context", "arcade_100", "pixel_canvas",
                "canvas_chunk", "canvas_binary", "difficulty", "performance", "mir", "gamma",
                "session_control", "key_release"
            };
            for (const auto* f : kFeats) {
                cJSON_AddItemToArray(feats, cJSON_CreateString(f));
            }
            cJSON_AddItemToObject(resp, "features", feats);

            cJSON* disp = cJSON_CreateObject();
            cJSON_AddNumberToObject(disp, "width", 16);
            cJSON_AddNumberToObject(disp, "height", 16);
            cJSON_AddStringToObject(disp, "color_format", "rgb888");
            cJSON_AddNumberToObject(disp, "canvas_mode", 29);
            cJSON_AddNumberToObject(disp, "fingertip_mode", 26);
            cJSON_AddNumberToObject(disp, "sandbox_mode", 27);
            cJSON_AddNumberToObject(disp, "pet_mode", 17);
            cJSON_AddItemToObject(resp, "display", disp);

            cJSON* uart = cJSON_CreateObject();
            cJSON_AddNumberToObject(uart, "baud", 115200);
            cJSON_AddNumberToObject(uart, "rx_pin", 8);
            cJSON_AddNumberToObject(uart, "tx_pin", 9);
            cJSON_AddNumberToObject(uart, "max_json_line", kMaxLineLength);
            cJSON_AddStringToObject(uart, "binary_magic", "0x55AA4346");
            cJSON_AddItemToObject(resp, "uart", uart);

            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "release_input")) {
            GetInstance().ReleaseHeldKeys();
            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddBoolToObject(resp, "released", true);
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "session")) {
            cJSON* act_item = cJSON_GetObjectItemCaseSensitive(root, "action");
            const char* act = (act_item && cJSON_IsString(act_item)) ? act_item->valuestring : "";
            cJSON* sid_item = cJSON_GetObjectItemCaseSensitive(root, "session_id");
            if (!sid_item) sid_item = cJSON_GetObjectItemCaseSensitive(root, "id");
            const char* sid = (sid_item && cJSON_IsString(sid_item)) ? sid_item->valuestring : "";

            cJSON* resp = cJSON_CreateObject();
            if (!strcasecmp(act, "start") || !strcasecmp(act, "resume")) {
                uint16_t initial_seq = 0;
                cJSON* seq_item = cJSON_GetObjectItemCaseSensitive(root, "initial_seq");
                if (!seq_item) seq_item = cJSON_GetObjectItemCaseSensitive(root, "seq");
                if (seq_item && cJSON_IsNumber(seq_item)) {
                    initial_seq = (uint16_t)seq_item->valueint;
                }
                GetInstance().StartSession(sid, initial_seq);

                DisplayManager& dm = DisplayManager::GetInstance();
                bool manual_active = dm.IsManualOverrideActive();
                // Human user control priority: Jetson UART cannot unilaterally clear manual override.
                // If human user set manual mode on App/Web, manual_override remains protected.
                cJSON* mode_item = cJSON_GetObjectItemCaseSensitive(root, "mode");
                bool mode_executed = false;
                if (mode_item) {
                    if (manual_active) {
                        mode_executed = false;
                    } else {
                        mode_executed = true;
                        if (cJSON_IsNumber(mode_item)) {
                            dm.SetMode((uint8_t)mode_item->valueint);
                        } else if (cJSON_IsString(mode_item)) {
                            const char* m = mode_item->valuestring;
                            if (!strcasecmp(m, "fingertip") || !strcasecmp(m, "track")) {
                                dm.SetMode(26);
                            } else if (!strcasecmp(m, "sandbox") || !strcasecmp(m, "hand")) {
                                dm.SetMode(27);
                            } else if (!strcasecmp(m, "canvas") || !strcasecmp(m, "pixel")) {
                                dm.SetMode(29);
                            } else if (!strcasecmp(m, "pet") || !strcasecmp(m, "kurisu")) {
                                dm.SetMode(17);
                            }
                        }
                    }
                }
                cJSON_AddStringToObject(resp, "status", "ok");
                cJSON_AddBoolToObject(resp, "active", true);
                cJSON_AddStringToObject(resp, "session_id", GetInstance().session_id_);
                cJSON_AddBoolToObject(resp, "mode_overridden", dm.IsManualOverrideActive());
                if (mode_item) {
                    cJSON_AddBoolToObject(resp, "mode_executed", mode_executed);
                }
            } else if (!strcasecmp(act, "stop")) {
                GetInstance().StopSession();
                cJSON_AddStringToObject(resp, "status", "ok");
                cJSON_AddBoolToObject(resp, "active", false);
                cJSON_AddStringToObject(resp, "session_state", "stopped");
            } else if (!strcasecmp(act, "heartbeat") || !strcasecmp(act, "ping")) {
                bool ok = GetInstance().PingSession();
                if (ok) {
                    GetInstance().last_input_time_ms_ = get_current_millis();
                    cJSON_AddStringToObject(resp, "status", "ok");
                    cJSON_AddBoolToObject(resp, "heartbeat", true);
                    cJSON_AddBoolToObject(resp, "active", true);
                    cJSON_AddBoolToObject(resp, "mode_overridden", DisplayManager::GetInstance().IsManualOverrideActive());
                } else {
                    cJSON_AddStringToObject(resp, "status", "error");
                    cJSON_AddStringToObject(resp, "error", (GetInstance().GetSessionState() == SessionState::STOPPED) ? "session_stopped" : "session_expired");
                    cJSON_AddBoolToObject(resp, "active", false);
                }
            } else {
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", "unknown_session_action");
            }
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "mode")) {
            cJSON* val_item = cJSON_GetObjectItemCaseSensitive(root, "val");
            if (!val_item) val_item = cJSON_GetObjectItemCaseSensitive(root, "mode");
            cJSON* resp = cJSON_CreateObject();
            if (!val_item || !cJSON_IsNumber(val_item)) {
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", "missing_mode");
                cJSON_AddBoolToObject(resp, "executed", false);
            } else {
                int m = val_item->valueint;
                DisplayManager& dm = DisplayManager::GetInstance();
                bool overridden = dm.IsManualOverrideActive();
                if (overridden) {
                    // Suppressed by active manual control from PC/mobile user
                    cJSON_AddStringToObject(resp, "status", "ok");
                    cJSON_AddBoolToObject(resp, "executed", false);
                    cJSON_AddBoolToObject(resp, "mode_overridden", true);
                    cJSON_AddNumberToObject(resp, "current_mode", static_cast<int>(dm.GetMode()));
                } else {
                    dm.SetMode(m);
                    // Crucial: Jetson autonomous mode change does NOT trigger manual override
                    cJSON_AddStringToObject(resp, "status", "ok");
                    cJSON_AddBoolToObject(resp, "executed", true);
                    cJSON_AddBoolToObject(resp, "mode_overridden", false);
                    cJSON_AddNumberToObject(resp, "mode", m);
                }
            }
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "canvas_chunk")) {
            JetsonUart& ju = GetInstance();
            SessionState state = ju.GetSessionState();
            if (state == SessionState::STOPPED || state == SessionState::EXPIRED) {
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", (state == SessionState::STOPPED) ? "session_stopped" : "session_expired");
                cJSON_AddBoolToObject(resp, "committed", false);
                cJSON_AddBoolToObject(resp, "displayed", false);
                append_req_id(resp);
                char* rendered = cJSON_PrintUnformatted(resp);
                if (rendered) {
                    snprintf(out_reply, out_reply_size, "%s", rendered);
                    cJSON_free(rendered);
                }
                cJSON_Delete(resp);
                cJSON_Delete(root);
                return;
            }
            auto* frame_item = cJSON_GetObjectItemCaseSensitive(root, "frame_id");
            if (!frame_item) frame_item = cJSON_GetObjectItemCaseSensitive(root, "frame");
            auto* chunk_item = cJSON_GetObjectItemCaseSensitive(root, "chunk_idx");
            if (!chunk_item) chunk_item = cJSON_GetObjectItemCaseSensitive(root, "chunk");
            auto* total_item = cJSON_GetObjectItemCaseSensitive(root, "total_chunks");
            if (!total_item) total_item = cJSON_GetObjectItemCaseSensitive(root, "total");
            auto* offset_item = cJSON_GetObjectItemCaseSensitive(root, "offset");
            auto* hex_item = cJSON_GetObjectItemCaseSensitive(root, "hex");
            auto* crc_item = cJSON_GetObjectItemCaseSensitive(root, "crc");
            auto* commit_item = cJSON_GetObjectItemCaseSensitive(root, "commit");
            auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");

            cJSON* resp = cJSON_CreateObject();
            if (!frame_item || !cJSON_IsNumber(frame_item) ||
                !offset_item || !cJSON_IsNumber(offset_item) ||
                !hex_item || !cJSON_IsString(hex_item)) {
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", "missing_chunk_params");
            } else {
                uint16_t frame_id = (uint16_t)frame_item->valueint;
                uint16_t chunk_idx = chunk_item ? (uint16_t)chunk_item->valueint : 0;
                uint16_t total_chunks = total_item ? (uint16_t)total_item->valueint : 1;
                uint16_t offset = (uint16_t)offset_item->valueint;
                const char* hex_str = hex_item->valuestring;
                size_t hex_len = strlen(hex_str);

                if (hex_len == 0 || (hex_len % 2) != 0) {
                    cJSON_AddStringToObject(resp, "status", "error");
                    cJSON_AddStringToObject(resp, "error", "invalid_hex_length");
                } else if (hex_len / 2 > 384 || (hex_len / 2 + offset > 768)) {
                    cJSON_AddStringToObject(resp, "status", "error");
                    cJSON_AddStringToObject(resp, "error", "chunk_bounds_overflow");
                } else if (total_chunks == 0 || total_chunks > 16 || chunk_idx >= total_chunks) {
                    cJSON_AddStringToObject(resp, "status", "error");
                    cJSON_AddStringToObject(resp, "error", "invalid_chunk_indices");
                } else {
                    size_t byte_len = hex_len / 2;
                    uint8_t chunk_bytes[384];
                    bool hex_ok = true;
                    auto hex_val = [](char c) -> int {
                        if (c >= '0' && c <= '9') return c - '0';
                        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
                        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
                        return -1;
                    };
                    for (size_t i = 0; i < byte_len; ++i) {
                        int h1 = hex_val(hex_str[i * 2]);
                        int h2 = hex_val(hex_str[i * 2 + 1]);
                        if (h1 < 0 || h2 < 0) {
                            hex_ok = false;
                            break;
                        }
                        chunk_bytes[i] = (uint8_t)(h1 * 16 + h2);
                    }

                    if (!hex_ok) {
                        cJSON_AddStringToObject(resp, "status", "error");
                        cJSON_AddStringToObject(resp, "error", "invalid_hex_chars");
                    } else {
                        uint16_t expected_crc = (crc_item && cJSON_IsNumber(crc_item)) ? (uint16_t)crc_item->valueint : 0;
                        bool commit_now = commit_item ? cJSON_IsTrue(commit_item) : false;
                        bool auto_mode = auto_item ? cJSON_IsTrue(auto_item) : true;
                        bool manual_overridden = DisplayManager::GetInstance().IsManualOverrideActive();
                        if (manual_overridden) {
                            auto_mode = false;
                        }

                        auto res = canvas::CanvasAssembler::GetInstance().FeedChunk(
                            frame_id, chunk_idx, total_chunks, offset, chunk_bytes, byte_len,
                            expected_crc, commit_now, auto_mode
                        );

                        DisplayManager& dm = DisplayManager::GetInstance();
                        bool displayed = res.committed && !manual_overridden && (dm.GetMode() == DisplayMode::PIXEL_CANVAS);

                        cJSON_AddStringToObject(resp, "status", res.success ? "ok" : "error");
                        cJSON_AddNumberToObject(resp, "frame_id", res.frame_id);
                        cJSON_AddNumberToObject(resp, "chunk_idx", chunk_idx);
                        cJSON_AddBoolToObject(resp, "committed", res.committed);
                        cJSON_AddBoolToObject(resp, "displayed", displayed);
                        cJSON_AddNumberToObject(resp, "received_bytes", res.received_bytes);
                        cJSON_AddBoolToObject(resp, "mode_overridden", manual_overridden);
                        if (!res.success && res.error_msg) {
                            cJSON_AddStringToObject(resp, "error", res.error_msg);
                        }
                    }
                }
            }
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "clear_canvas") || !strcasecmp(cmd, "canvas_clear")) {
            SessionState state = GetInstance().GetSessionState();
            if (state == SessionState::STOPPED || state == SessionState::EXPIRED) {
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", (state == SessionState::STOPPED) ? "session_stopped" : "session_expired");
                cJSON_AddBoolToObject(resp, "cleared", false);
                append_req_id(resp);
                char* rendered = cJSON_PrintUnformatted(resp);
                if (rendered) {
                    snprintf(out_reply, out_reply_size, "%s", rendered);
                    cJSON_free(rendered);
                }
                cJSON_Delete(resp);
                return;
            }

            uint8_t r = 0, g = 0, b = 0;
            auto* r_item = cJSON_GetObjectItemCaseSensitive(root, "r");
            auto* g_item = cJSON_GetObjectItemCaseSensitive(root, "g");
            auto* b_item = cJSON_GetObjectItemCaseSensitive(root, "b");
            if (r_item && cJSON_IsNumber(r_item)) r = (uint8_t)r_item->valueint;
            if (g_item && cJSON_IsNumber(g_item)) g = (uint8_t)g_item->valueint;
            if (b_item && cJSON_IsNumber(b_item)) b = (uint8_t)b_item->valueint;
            auto* auto_item = cJSON_GetObjectItemCaseSensitive(root, "auto_mode");
            bool auto_mode = auto_item ? cJSON_IsTrue(auto_item) : false;

            canvas::CanvasAssembler::GetInstance().Clear(r, g, b, auto_mode);

            cJSON* resp = cJSON_CreateObject();
            cJSON_AddStringToObject(resp, "status", "ok");
            cJSON_AddBoolToObject(resp, "cleared", true);
            append_req_id(resp);
            char* rendered = cJSON_PrintUnformatted(resp);
            if (rendered) {
                snprintf(out_reply, out_reply_size, "%s", rendered);
                cJSON_free(rendered);
            }
            cJSON_Delete(resp);
        } else if (!strcasecmp(cmd, "arcade")) {
            cJSON* act_item = cJSON_GetObjectItemCaseSensitive(root, "action");
            const char* act = (act_item && cJSON_IsString(act_item)) ? act_item->valuestring : "";

            SessionState state = GetInstance().GetSessionState();
            if (strcasecmp(act, "status") != 0 && (state == SessionState::STOPPED || state == SessionState::EXPIRED)) {
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", (state == SessionState::STOPPED) ? "session_stopped" : "session_expired");
                cJSON_AddBoolToObject(resp, "executed", false);
                append_req_id(resp);
                char* rendered = cJSON_PrintUnformatted(resp);
                if (rendered) {
                    snprintf(out_reply, out_reply_size, "%s", rendered);
                    cJSON_free(rendered);
                }
                cJSON_Delete(resp);
                return;
            }

            if (!strcasecmp(act, "status")) {
                auto& am = arcade::ArcadeManager::GetInstance();
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", "ok");
                cJSON_AddBoolToObject(resp, "active", am.IsActive());
                cJSON_AddNumberToObject(resp, "game_id", am.GetCurrentGameId());
                if (am.IsActive()) {
                    cJSON_AddStringToObject(resp, "game_name", am.GetCurrentGameName() ? am.GetCurrentGameName() : "");
                    cJSON_AddNumberToObject(resp, "control_type", static_cast<int>(am.GetCurrentControlType()));
                    auto s = am.GetCurrentStatus();
                    cJSON_AddNumberToObject(resp, "score", s.score);
                    cJSON_AddNumberToObject(resp, "high_score", s.high_score);
                    cJSON_AddNumberToObject(resp, "lives", s.lives);
                    cJSON_AddNumberToObject(resp, "state", s.state);
                }
                append_req_id(resp);
                char* rendered = cJSON_PrintUnformatted(resp);
                if (rendered) {
                    snprintf(out_reply, out_reply_size, "%s", rendered);
                    cJSON_free(rendered);
                }
                cJSON_Delete(resp);
            } else {
                // If action is input, record held keys and timestamp for watchdog auto-release
                if (!strcasecmp(act, "input")) {
                    cJSON* down_item = cJSON_GetObjectItemCaseSensitive(root, "down");
                    if (down_item && cJSON_IsNumber(down_item)) {
                        GetInstance().held_keys_ = (uint16_t)down_item->valueint;
                        GetInstance().last_input_time_ms_ = get_current_millis();
                    }
                }

                bool ok = CommandDispatcher::GetInstance().ProcessLine(line, false, true, false);
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", ok ? "ok" : "error");
                cJSON_AddBoolToObject(resp, "executed", ok);
                if (!ok) {
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
        } else {
            // Strict Security Whitelist Check:
            // Explicitly reject prohibited commands
            const char* const kDisallowedCmds[] = {
                "pair", "control_token", "token", "reboot", "restart",
                "factory_reset", "reset_nvs", "erase_flash", "write_flash",
                "mic_export", "audio_capture", "ota"
            };
            bool disallowed = false;
            for (const auto& d : kDisallowedCmds) {
                if (!strcasecmp(cmd, d)) {
                    disallowed = true;
                    break;
                }
            }

            if (disallowed) {
                cJSON* resp = cJSON_CreateObject();
                cJSON_AddStringToObject(resp, "status", "error");
                cJSON_AddStringToObject(resp, "error", "unauthorized_command");
                cJSON_AddBoolToObject(resp, "executed", false);
                append_req_id(resp);
                char* rendered = cJSON_PrintUnformatted(resp);
                if (rendered) {
                    snprintf(out_reply, out_reply_size, "%s", rendered);
                    cJSON_free(rendered);
                }
                cJSON_Delete(resp);
            } else {
                // Allowed Business Commands Whitelist
                const char* const kAllowedCmds[] = {
                    "mode", "brightness", "b", "board_led", "led", "arcade",
                    "pet", "kurisu", "countdown", "stop_countdown", "stop_cd", "beep", "key",
                    "track_cal", "track", "hand", "pet_context", "celebrate",
                    "difficulty", "performance", "mir", "pixel", "canvas", "gamma"
                };
                bool allowed = false;
                for (const auto& a : kAllowedCmds) {
                    if (!strcasecmp(cmd, a)) {
                        allowed = true;
                        break;
                    }
                }

                // If session is stopped or expired, reject visual and canvas commands
                JetsonUart& ju = GetInstance();
                SessionState state = ju.GetSessionState();
                if (state == SessionState::STOPPED || state == SessionState::EXPIRED) {
                    if (!strcasecmp(cmd, "track") || !strcasecmp(cmd, "hand") ||
                        !strcasecmp(cmd, "pet_context") || !strcasecmp(cmd, "face") ||
                        !strcasecmp(cmd, "track_cal") || !strcasecmp(cmd, "pixel") ||
                        !strcasecmp(cmd, "canvas") || !strcasecmp(cmd, "clear_canvas") ||
                        !strcasecmp(cmd, "arcade")) {
                        cJSON* resp = cJSON_CreateObject();
                        cJSON_AddStringToObject(resp, "status", "error");
                        cJSON_AddStringToObject(resp, "error", (state == SessionState::STOPPED) ? "session_stopped" : "session_expired");
                        cJSON_AddBoolToObject(resp, "executed", false);
                        append_req_id(resp);
                        char* rendered = cJSON_PrintUnformatted(resp);
                        if (rendered) {
                            snprintf(out_reply, out_reply_size, "%s", rendered);
                            cJSON_free(rendered);
                        }
                        cJSON_Delete(resp);
                        cJSON_Delete(root);
                        return;
                    }
                }

                bool ok = false;
                if (allowed) {
                    ok = CommandDispatcher::GetInstance().ProcessLine(line, false, true, false);
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
        }
        cJSON_Delete(root);
        return;
    }

    // Fallback: Plain text parsing (e.g. "ping", "status", "mode 1", "countdown 60", "release_input")
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
    } else if (!strcasecmp(line, "release_input")) {
        GetInstance().ReleaseHeldKeys();
        snprintf(out_reply, out_reply_size, "{\"status\":\"ok\",\"released\":true}");
    } else {
        // Disallowed plain text commands
        if (!strcasecmp(line, "reboot") || !strcasecmp(line, "restart") ||
            !strcasecmp(line, "factory_reset") || !strcasecmp(line, "pair")) {
            snprintf(out_reply, out_reply_size, "{\"status\":\"error\",\"error\":\"unauthorized_command\",\"cmd\":\"%s\"}", line);
            return;
        }

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
            bool ok = CommandDispatcher::GetInstance().ProcessLine(line, false, true, false);
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
