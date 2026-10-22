# Git 与本地配置

本项目仓库是 https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro 。按项目所有者要求，直接在 `main` 开发，完成并验证一个可回退节点后提交、推送到 `origin main`，不额外创建功能分支。不强推，不覆盖他人提交；推送前检查远程进度。

2026-10-23：组员指尖模块已接入正式源码、模式26、track/track_cal、显示任务和构建。新增高阶功能与原SRS差异见 [PRO_FEATURES](PRO_FEATURES.md)，已完成离线构建与测试，尚未上板验收。

## Wi-Fi 配置

复制 `firmware-s3/main/wifi_config.example.h` 为同目录的 `wifi_config.private.h`，设置自己的 2.4 GHz 热点及板端 AP 参数后再编译。私有头文件已被 `.gitignore` 的 `*.private.*` 规则忽略。现有电脑上的连接设置已迁入这个本地文件，没有改变；示例中的值仅为占位符。

不要提交真实网络密码、API密钥、设备地址状态、诊断录音、语音缓存、私有运行依赖、模型权重或构建目录。构建、录音、日志和测试产物保存在仓库外的任务专用缓存；持久记忆与人脸登记在配置的应用数据目录。Git提交只保存可审查的源码、依赖声明、测试和项目说明。

## 验证

离线回归检查：

```powershell
python scripts/test_interaction_regressions.py
python scripts/test_semantic_control.py
```

真实模型语义检查使用 `scripts/test_semantic_control.py --live`；它仅调用本地 Ollama，不驱动灯板或播放声音。

`scripts/test_board_ack.py --silent` 会操作真实设备，运行前应停止占用 COM9/UDP 8888 的完整服务；其他音频诊断脚本也可能打开硬件或发声，不能不加区分地批量执行。

独立声学唤醒的依赖和官方模型来源见 `VOICE_CONTROL_RECOVERY.md`；私有依赖版本固定在 `pc-agent-vision/requirements-wake.txt`。这些运行文件不随源码仓库上传。

2026-10-21的历史记录包含当时的烧录、板端检查、模型用例及用户星空/波纹语音反馈，见 `VOICE_CONTROL_RECOVERY.md`。2026-10-23新增连续轮次与其他高阶代码仅做离线验证；不能把历史实测外推到本次修订。实机测试或有声对比必须另行安排，并先向用户说明。
