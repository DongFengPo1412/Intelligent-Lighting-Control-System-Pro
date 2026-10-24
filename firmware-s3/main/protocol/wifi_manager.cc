#include "wifi_manager.h"
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <esp_log.h>
#include <esp_wifi.h>
#include <esp_event.h>
#include <esp_netif.h>
#include <nvs_flash.h>
#include <cJSON.h>
#include "command_dispatcher.h"
#include "display_manager.h"
#include "board_led.h"
#include "audio_hal.h"

static const char* TAG = "WifiMgr";

WifiManager& WifiManager::GetInstance()
{
    static WifiManager instance;
    return instance;
}

WifiManager::WifiManager()
    : udp_port_(8888),
      is_sta_connected_(false),
      is_ap_active_(false),
      udp_task_handle_(nullptr),
      reconnect_timer_(nullptr)
{
    memset(sta_ssid_, 0, sizeof(sta_ssid_));
    memset(sta_password_, 0, sizeof(sta_password_));
    memset(ap_ssid_, 0, sizeof(ap_ssid_));
    memset(ap_password_, 0, sizeof(ap_password_));
    strncpy(sta_ip_, "0.0.0.0", sizeof(sta_ip_) - 1);
    strncpy(ap_ip_, "192.168.4.1", sizeof(ap_ip_) - 1);
}

WifiManager::~WifiManager()
{
}

void WifiManager::WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data)
{
    WifiManager* self = static_cast<WifiManager*>(arg);

    if (event_base == WIFI_EVENT) {
        if (event_id == WIFI_EVENT_AP_START) {
            self->is_ap_active_ = true;
            ESP_LOGI(TAG, "===============================================================");
            ESP_LOGI(TAG, "★★★ [全时 WiFi SoftAP 独立热点已就绪] ★★★");
            ESP_LOGI(TAG, ">>> 热点名称 (SSID): %s", self->ap_ssid_);
            ESP_LOGI(TAG, ">>> 连接密码请查看本地 Wi-Fi 配置文件");
            ESP_LOGI(TAG, ">>> 默认网关 IP    : %s (固定)", self->ap_ip_);
            ESP_LOGI(TAG, ">>> 局域网控制端口 : UDP %u", self->udp_port_);
            ESP_LOGI(TAG, ">>> 无论外接电源供电、热点是否开启，WiFi 通信恒定在线！");
            ESP_LOGI(TAG, "===============================================================");
        } else if (event_id == WIFI_EVENT_AP_STACONNECTED) {
            wifi_event_ap_staconnected_t* event = (wifi_event_ap_staconnected_t*)event_data;
            ESP_LOGI(TAG, ">>> [客户端已接入板端 AP]: MAC=%02x:%02x:%02x:%02x:%02x:%02x, AID=%d",
                     event->mac[0], event->mac[1], event->mac[2], event->mac[3], event->mac[4], event->mac[5], event->aid);
        } else if (event_id == WIFI_EVENT_AP_STADISCONNECTED) {
            wifi_event_ap_stadisconnected_t* event = (wifi_event_ap_stadisconnected_t*)event_data;
            ESP_LOGI(TAG, ">>> [客户端已断开板端 AP]: MAC=%02x:%02x:%02x:%02x:%02x:%02x",
                     event->mac[0], event->mac[1], event->mac[2], event->mac[3], event->mac[4], event->mac[5]);
        } else if (event_id == WIFI_EVENT_STA_START) {
            ESP_LOGI(TAG, ">>> [WiFi STA 启动]: 正在搜寻并连接热点 '%s'...", self->sta_ssid_);
            esp_wifi_connect();
        } else if (event_id == WIFI_EVENT_STA_DISCONNECTED) {
            auto* disconnected = static_cast<wifi_event_sta_disconnected_t*>(event_data);
            self->is_sta_connected_ = false;
            strncpy(self->sta_ip_, "0.0.0.0", sizeof(self->sta_ip_) - 1);

            static uint32_t retry_cnt = 0;
            if (++retry_cnt % 6 == 1) {
                ESP_LOGI(TAG, ">>> [WiFi STA 重连]: SSID=%s, reason=%u, AP=%s",
                         self->sta_ssid_, (unsigned)disconnected->reason, self->ap_ssid_);
            }
            // Do not block the shared ESP event loop while waiting to reconnect.
            esp_timer_stop(self->reconnect_timer_);
            esp_timer_start_once(self->reconnect_timer_, 3000000);
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = static_cast<ip_event_got_ip_t*>(event_data);
        esp_ip4addr_ntoa(&event->ip_info.ip, self->sta_ip_, sizeof(self->sta_ip_));
        self->is_sta_connected_ = true;
        esp_timer_stop(self->reconnect_timer_);
        ESP_LOGI(TAG, "===============================================================");
        ESP_LOGI(TAG, "★★★ [热点局域网 STA 连接成功] ★★★");
        ESP_LOGI(TAG, ">>> 板端分配局域网 IP: %s", self->sta_ip_);
        ESP_LOGI(TAG, ">>> 局域网控制 UDP 端口: %u", self->udp_port_);
        ESP_LOGI(TAG, "===============================================================");

        // 连网成功后向局域网广播一条 Hello 报文
        int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
        if (sock >= 0) {
            int broadcast = 1;
            setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));
            struct sockaddr_in dest_addr;
            dest_addr.sin_family = AF_INET;
            dest_addr.sin_port = htons(self->udp_port_);
            dest_addr.sin_addr.s_addr = htonl(INADDR_BROADCAST);
            char beacon[160];
            snprintf(beacon, sizeof(beacon),
                     "{\"event\":\"board_online\",\"sta_ip\":\"%s\",\"ap_ip\":\"%s\",\"port\":%u}\n",
                     self->sta_ip_, self->ap_ip_, self->udp_port_);
            sendto(sock, beacon, strlen(beacon), 0, (struct sockaddr*)&dest_addr, sizeof(dest_addr));
            close(sock);
        }
    }
}

esp_err_t WifiManager::InitAndConnect(const char* sta_ssid, const char* sta_password,
                                     const char* ap_ssid, const char* ap_password,
                                     uint16_t udp_port)
{
    if (sta_ssid) strncpy(sta_ssid_, sta_ssid, sizeof(sta_ssid_) - 1);
    if (sta_password) strncpy(sta_password_, sta_password, sizeof(sta_password_) - 1);
    if (ap_ssid) strncpy(ap_ssid_, ap_ssid, sizeof(ap_ssid_) - 1);
    if (ap_password) strncpy(ap_password_, ap_password, sizeof(ap_password_) - 1);
    udp_port_ = udp_port;

    // 1. 初始化 NVS 存储区 (WiFi 协议栈必需)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // 2. 初始化网络接口与系统事件分发循环 (同时创建 STA 与 AP 双接口)
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    esp_netif_create_default_wifi_ap();

    // 3. 配置 WiFi 驱动栈
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_timer_create_args_t reconnect_args = {};
    reconnect_args.callback = [](void*) { esp_wifi_connect(); };
    reconnect_args.name = "wifi_reconnect";
    ESP_ERROR_CHECK(esp_timer_create(&reconnect_args, &reconnect_timer_));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &WifiManager::WifiEventHandler,
                                                        this,
                                                        nullptr));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &WifiManager::WifiEventHandler,
                                                        this,
                                                        nullptr));

    // 4. 配置 STA (热点连接端)
    wifi_config_t sta_config = {};
    strncpy((char*)sta_config.sta.ssid, sta_ssid_, sizeof(sta_config.sta.ssid));
    strncpy((char*)sta_config.sta.password, sta_password_, sizeof(sta_config.sta.password));
    sta_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    sta_config.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;
    sta_config.sta.pmf_cfg.capable = true;
    sta_config.sta.pmf_cfg.required = false;

    // 5. 配置 SoftAP (全时自主热点端)
    wifi_config_t ap_config = {};
    strncpy((char*)ap_config.ap.ssid, ap_ssid_, sizeof(ap_config.ap.ssid));
    strncpy((char*)ap_config.ap.password, ap_password_, sizeof(ap_config.ap.password));
    ap_config.ap.ssid_len = strlen(ap_ssid_);
    ap_config.ap.channel = 1;
    ap_config.ap.max_connection = 4;
    ap_config.ap.authmode = (strlen(ap_password_) >= 8) ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    // 6. 启动独立后台 UDP 局域网监听任务 (分配至 Core 0，优先级 4)
    xTaskCreatePinnedToCore(
        WifiManager::UdpServerTaskTrampoline,
        "wifi_udp_srv",
        8192,
        this,
        4,
        &udp_task_handle_,
        0
    );

    return ESP_OK;
}

void WifiManager::UdpServerTaskTrampoline(void* arg)
{
    static_cast<WifiManager*>(arg)->UdpServerTaskLoop();
}

void WifiManager::UdpServerTaskLoop()
{
    // Keep recent results so lost ACKs can be retried without restarting a timer
    // or repeating a game move. IDs are scoped to the sending host.
    struct CachedReply {
        uint32_t sender;
        char id[65];
        uint32_t command_hash;
        TickType_t tick;
        char response[512];
    };
    static CachedReply recent[16] = {};
    size_t next_reply = 0;
    static char rx_buffer[4096];
    struct sockaddr_in server_addr = {};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(udp_port_);

    int sock = -1;
    TickType_t last_beacon_tick = 0;

    while (1) {
        // 创建 UDP 套接字
        if (sock < 0) {
            sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
            if (sock < 0) {
                ESP_LOGE(TAG, "创建 UDP 套接字失败，500ms 后重试");
                vTaskDelay(pdMS_TO_TICKS(500));
                continue;
            }

            int reuse = 1;
            setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

            int broadcast = 1;
            setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));

            // 设置 250ms 超时，便于维持周期性心跳 beacon
            struct timeval tv;
            tv.tv_sec = 0;
            tv.tv_usec = 250000;
            setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

            int err = bind(sock, (struct sockaddr*)&server_addr, sizeof(server_addr));
            if (err < 0) {
                ESP_LOGE(TAG, "绑定 UDP 端口 %u 失败，errno=%d", udp_port_, errno);
                close(sock);
                sock = -1;
                vTaskDelay(pdMS_TO_TICKS(1000));
                continue;
            }
            ESP_LOGI(TAG, ">>> [全时 UDP 局域网服务就绪]: 端口 %u 监听中 (STA IP: %s, AP IP: %s)",
                     udp_port_, sta_ip_, ap_ip_);
        }

        // 周期性 (每 2 秒) 向全网发送心跳 Beacon 报文
        TickType_t now_tick = xTaskGetTickCount();
        if ((now_tick - last_beacon_tick) >= pdMS_TO_TICKS(2000)) {
            last_beacon_tick = now_tick;

            char beacon[192];
            int mode_val = (int)DisplayManager::GetInstance().GetMode();
            snprintf(beacon, sizeof(beacon),
                     "{\"event\":\"beacon\",\"device\":\"Kurisu-Matrix\",\"sta_ip\":\"%s\",\"sta_connected\":%s,\"ap_ip\":\"%s\",\"port\":%u,\"mode\":%d}\n",
                     sta_ip_, is_sta_connected_ ? "true" : "false", ap_ip_, udp_port_, mode_val);

            // 1. 发送到 SoftAP 子网广播 (192.168.4.255:8888)
            struct sockaddr_in ap_dest;
            ap_dest.sin_family = AF_INET;
            ap_dest.sin_port = htons(udp_port_);
            ap_dest.sin_addr.s_addr = inet_addr("192.168.4.255");
            sendto(sock, beacon, strlen(beacon), 0, (struct sockaddr*)&ap_dest, sizeof(ap_dest));

            // 2. 如果 STA 已连网，发送到全局局域网广播 (255.255.255.255:8888)
            if (is_sta_connected_) {
                struct sockaddr_in sta_dest;
                sta_dest.sin_family = AF_INET;
                sta_dest.sin_port = htons(udp_port_);
                sta_dest.sin_addr.s_addr = htonl(INADDR_BROADCAST);
                sendto(sock, beacon, strlen(beacon), 0, (struct sockaddr*)&sta_dest, sizeof(sta_dest));
            }
        }

        struct sockaddr_in source_addr;
        socklen_t socklen = sizeof(source_addr);
        int len = recvfrom(sock, rx_buffer, sizeof(rx_buffer) - 1, 0, (struct sockaddr*)&source_addr, &socklen);

        if (len < 0) {
            // 超时继续轮询
            continue;
        }

        rx_buffer[len] = '\0';

        // 去除末尾换行符并执行指令
        while (len > 0 && (rx_buffer[len - 1] == '\r' || rx_buffer[len - 1] == '\n' || rx_buffer[len - 1] == ' ')) {
            rx_buffer[--len] = '\0';
        }

        if (len > 0) {
            char sender_ip[16];
            inet_ntoa_r(source_addr.sin_addr, sender_ip, sizeof(sender_ip));
            ESP_LOGD(TAG, "[WiFi UDP 来自 %s]: %s", sender_ip, rx_buffer);

            cJSON* envelope = cJSON_Parse(rx_buffer);
            if (envelope && cJSON_GetObjectItem(envelope, "event")) {
                cJSON_Delete(envelope); // Ignore our own broadcast beacons.
                continue;
            }
            cJSON* id_item = envelope ? cJSON_GetObjectItem(envelope, "request_id") : nullptr;
            cJSON* command_item = envelope ? cJSON_GetObjectItem(envelope, "command") : nullptr;
            const bool wrapped = id_item || command_item;
            const char* id = cJSON_IsString(id_item) ? id_item->valuestring : "";
            bool valid_envelope = !wrapped || (
                strlen(id) > 0 && strlen(id) <= 64 &&
                strspn(id, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") == strlen(id) &&
                cJSON_IsString(command_item) && command_item->valuestring[0]);
            if (!valid_envelope) id = "";
            const char* command = wrapped && valid_envelope ? command_item->valuestring : rx_buffer;
            uint32_t hash = 2166136261u;
            for (const unsigned char* p = (const unsigned char*)command; *p; ++p) hash = (hash ^ *p) * 16777619u;

            const char* cached = nullptr;
            bool conflict = false;
            if (wrapped && valid_envelope) {
                for (const auto& entry : recent) {
                    if (entry.sender == source_addr.sin_addr.s_addr && strcmp(entry.id, id) == 0 &&
                        xTaskGetTickCount() - entry.tick < pdMS_TO_TICKS(30000)) {
                        if (entry.command_hash == hash) cached = entry.response;
                        else conflict = true;
                        break;
                    }
                }
            }
            if (cached) {
                sendto(sock, cached, strlen(cached), 0, (struct sockaddr*)&source_addr, sizeof(source_addr));
                cJSON_Delete(envelope);
                continue;
            }

            bool ok = valid_envelope && !conflict && CommandDispatcher::GetInstance().ProcessLine(command, false);
            auto& dm = DisplayManager::GetInstance();
            auto& dispatcher = CommandDispatcher::GetInstance();
            cJSON* parsed_command=cJSON_Parse(command);
            cJSON* parsed_name=parsed_command?cJSON_GetObjectItem(parsed_command,"cmd"):nullptr;
            bool frame_query=cJSON_IsString(parsed_name)&&!strcmp(parsed_name->valuestring,"frame");
            cJSON_Delete(parsed_command);
            char ack[512];
            snprintf(ack, sizeof(ack),
                     "{\"request_id\":\"%s\",\"status\":\"%s\",\"error\":\"%s\",\"mode\":%d,\"countdown_active\":%s,\"countdown_remaining\":%u,\"mic_streaming\":%s,\"volume\":%d,\"audio_rx\":%u,\"audio_played\":%u,\"audio_dropped\":%u,\"audio_errors\":%u,\"audio_stack_free\":%u}\n",
                     id, ok ? "ok" : "error", ok ? "" : (conflict ? "request_id_conflict" : "invalid_command"),
                     (int)dm.GetMode(), dm.IsCountdownActive() ? "true" : "false",
                     (unsigned)dm.GetCountdownRemainingSeconds(),
                     dispatcher.IsMicStreaming() ? "true" : "false", AudioHAL::GetInstance().GetVolume(),
                     (unsigned)dispatcher.AudioReceived(), (unsigned)dispatcher.AudioPlayed(),
                     (unsigned)dispatcher.AudioDropped(), (unsigned)dispatcher.AudioErrors(),
                     (unsigned)dispatcher.AudioStackFree());
            if(ok&&frame_query) {
                static char hex[1537],frame_ack[2304];
                uint32_t frame_id=dm.SnapshotFrame(hex,sizeof(hex));
                cJSON* frame=cJSON_Parse(ack);
                cJSON_AddStringToObject(frame,"pixels",hex);
                cJSON_AddNumberToObject(frame,"frame_id",frame_id);
                cJSON_AddStringToObject(frame,"frame_source","hardware_pwm");
                if(cJSON_PrintPreallocated(frame,frame_ack,sizeof(frame_ack),false))
                    sendto(sock,frame_ack,strlen(frame_ack),0,(struct sockaddr*)&source_addr,sizeof(source_addr));
                cJSON_Delete(frame);cJSON_Delete(envelope);continue;
            }
            if (wrapped && valid_envelope && !conflict) {
                auto& entry = recent[next_reply++ % 16];
                entry.sender = source_addr.sin_addr.s_addr;
                snprintf(entry.id, sizeof(entry.id), "%s", id);
                entry.command_hash = hash;
                entry.tick = xTaskGetTickCount();
                snprintf(entry.response, sizeof(entry.response), "%s", ack);
            }
            sendto(sock, ack, strlen(ack), 0, (struct sockaddr*)&source_addr, sizeof(source_addr));
            cJSON_Delete(envelope);
        }
    }

    if (sock >= 0) {
        close(sock);
    }
    vTaskDelete(nullptr);
}
