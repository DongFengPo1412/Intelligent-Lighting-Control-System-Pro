#pragma once

#include <stdint.h>
#include <esp_err.h>
#include <esp_event.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

class WifiManager {
public:
    static WifiManager& GetInstance();

    // 初始化全时 WiFi (APSTA 双模并发):
    // 1. SoftAP: 恒定启动广播 "Kurisu-Matrix-AP"，IP: 192.168.4.1 (无热点/无路由器也能100%直连通信)
    // 2. Station: 自动搜寻并连入本地配置指定的热点，获取局域网 IP
    // 3. UDP 8888: 监听并处理来自电脑上位机和手机 Web/App 的双向指令
    // 4. 定时心跳广播: 每 2 秒向局域网广播 beacon 报文，上位机自动捕获板端 IP
    esp_err_t InitAndConnect(const char* sta_ssid,
                             const char* sta_password,
                             const char* ap_ssid,
                             const char* ap_password,
                             uint16_t udp_port = 8888);

    // 查询当前 WiFi 连通状态
    bool IsStaConnected() const { return is_sta_connected_; }
    bool IsApActive() const { return is_ap_active_; }
    bool IsConnected() const { return is_sta_connected_ || is_ap_active_; }

    // 获取当前板端局域网 IPv4 字符串
    const char* GetStaIp() const { return sta_ip_; }
    const char* GetApIp() const { return ap_ip_; }
    const char* GetActiveIp() const { return is_sta_connected_ ? sta_ip_ : ap_ip_; }
    const char* GetIpString() const { return GetActiveIp(); }
    uint16_t GetUdpPort() const { return udp_port_; }

private:
    WifiManager();
    ~WifiManager();

    WifiManager(const WifiManager&) = delete;
    WifiManager& operator=(const WifiManager&) = delete;

    static void WifiEventHandler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data);
    static void UdpServerTaskTrampoline(void* arg);
    void UdpServerTaskLoop();

    char sta_ssid_[33];
    char sta_password_[65];
    char ap_ssid_[33];
    char ap_password_[65];
    char sta_ip_[16];
    char ap_ip_[16];
    uint16_t udp_port_;
    volatile bool is_sta_connected_;
    volatile bool is_ap_active_;
    TaskHandle_t udp_task_handle_;
    esp_timer_handle_t reconnect_timer_;
};
