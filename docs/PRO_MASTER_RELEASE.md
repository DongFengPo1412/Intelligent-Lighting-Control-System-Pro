# Intelligent Lighting Control System Pro — 正式版本发布与部署清册

**发布版本**：Pro v2.3.1 Master Frozen Release  
**发布时间**：2026年11月11日  
**代码基线 Commit**：[`4bc9e39`](https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro/commit/4bc9e39) 及后续 Master 闭环  

---

## 一、可执行交付物与校验哈希矩阵

| 交付组件 | 产物文件名与路径 | 版本标识 | 文件大小 | SHA-256 校验和 |
| :--- | :--- | :---: | :---: | :--- |
| **ESP32-S3 生产固件** | `firmware-s3/build/s3_led_matrix_test.bin` | `v2.3.1-pro` | 1,605,424 字节 | `4A1C0F1E0A76C811FD46355AA675911201A6E6FCCEBAB4254868EBBD7B429715` |
| **Android 生产客户端** | `android-app/Kurisu_Amadeus_v2.2.0_pro.apk` | `2.2.0 (30)` | 2,845,153 字节 | `E6D92232205EBE5AB066F65B473D913C27DD789A810D825AC76E8BC43E5EA78B` |
| **Jetson 独立开发包** | `jetson-nano.zip` | `v2.3.1` | 23,921 字节 | `D18E91880B8F13E88C688515C2B2A1B48D4DF1E79694C175F832BFB63E14732C` |

---

## 二、ESP32-S3 固件烧录指南

> [!IMPORTANT]
> 烧录严格限定于用户应用分区 `ota_0` (`0x20000`)，严禁擦除 Bootloader、分区表或 NVS 数据区。

```bash
# 使用 ESP-IDF 官方工具 esptool 进行极速 App-only 烧录
python -m esptool -p COM9 -b 460800 --chip esp32s3 write_flash 0x20000 firmware-s3/build/s3_led_matrix_test.bin

# 烧录后回读校验命令
python -m esptool -p COM9 -b 460800 --chip esp32s3 read_flash 0x20000 1605424 readback.bin
Get-FileHash -Algorithm SHA256 firmware-s3/build/s3_led_matrix_test.bin, readback.bin
```

---

## 三、PC 端上位机服务启动

### 1. 运行依赖
* 操作系统：Windows 10/11 64-bit 或 Linux Ubuntu 20.04/22.04
* Python 环境：Python 3.10
* 本地 AI：Ollama 服务运行并加载 `kurisu` 模型

### 2. 启动命令
```bash
cd C:\workspace\Intelligent-Lighting-Control-System-Pro\pc-agent-vision
python web_server.py
```
服务将在本机 `http://0.0.0.0:8080` 启动，并在局域网 UDP 端口 `8890` 广播服务供手机自动发现与配对。

---

## 四、Android 客户端升级

直接将 `android-app/Kurisu_Amadeus_v2.2.0_pro.apk` 安装或传至手机：
```bash
adb install -r android-app/Kurisu_Amadeus_v2.2.0_pro.apk
```
应用保持原有官方 keystore 签名，直接覆盖旧版并保留历史配对密钥。

