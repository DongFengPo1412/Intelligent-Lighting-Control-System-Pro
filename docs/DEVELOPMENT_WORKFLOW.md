# Git 与本地配置

本项目仓库是 https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro 。按项目所有者要求，直接在 `main` 开发，完成并验证一个可回退节点后提交、推送到 `origin main`，不额外创建功能分支。不强推，不覆盖他人提交；推送前检查远程进度。

本次交接版本包含先前已存在的工作区改动和本轮修复。根目录指尖追踪源码与 `INTEGRATION.md` 单独保留为待集成资料，当前运行固件没有模式 26，不能把这些文件当成已完成的指尖功能。

## Wi-Fi 配置

复制 `firmware-s3/main/wifi_config.example.h` 为同目录的 `wifi_config.private.h`，设置自己的 2.4 GHz 热点及板端 AP 参数后再编译。私有头文件已被 `.gitignore` 的 `*.private.*` 规则忽略。现有电脑上的连接设置已迁入这个本地文件，没有改变；示例中的值仅为占位符。

不要提交真实网络密码、API 密钥、`.device_state.json`、`.voice_diagnostics`、`.voice_cache`、`.runtime_deps`、模型权重或构建目录。构建和录音产物保存在本机，Git 提交保存可审查的源码、依赖版本、测试和验证说明。

## 验证

离线回归检查：

```powershell
python scripts/test_interaction_regressions.py
python scripts/test_semantic_control.py
```

真实模型语义检查使用 `scripts/test_semantic_control.py --live`；它仅调用本地 Ollama，不驱动灯板或播放声音。

`scripts/test_board_ack.py --silent` 会操作真实设备，运行前应停止占用 COM9/UDP 8888 的完整服务；其他音频诊断脚本也可能打开硬件或发声，不能不加区分地批量执行。

独立声学唤醒的依赖和官方模型来源见 `VOICE_CONTROL_RECOVERY.md`；私有依赖版本固定在 `pc-agent-vision/requirements-wake.txt`。这些运行文件不随源码仓库上传。

本轮已有固件编译、烧录、74 项硬件检查、30 项真实模型语义检查及用户星空/波纹语音验收记录，详见 `VOICE_CONTROL_RECOVERY.md`。当前保留每轮重新唤醒的交互策略，连续对话尚未改动。
