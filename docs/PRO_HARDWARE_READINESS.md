# Pro首次实机部署就绪审查（2026-11-05）

## 结论：READY_FOR_HARDWARE

含义严格限定：采用下列**显式兼容配置**及相互匹配的新固件/APK，可以进入用户授权后的只读备份、布局核对和首次受控设备验证。不是立即无条件刷写许可，不是默认GPU配置已修好，不是当前100款或全系统已物理验收。未发现本范围内尚未处理的P0软件阻断；已知P1代码断链已修复，语音环境以实际验证过的配置绕开已复现错误。

**禁止在本轮执行：刷写、擦除NVS、改分区、安装APK。任何新的设备写入均需用户另行明确授权。**

## 1. 软件门槛与遗留边界

- 开发分支保持`arcade-100-audit-and-elevation`；原基线`ccbc28f`，以本轮最终提交和构建产物记录为准，不合并main。
- ESP-IDF5.5.4实际完整构建；分区为16MB双6MiB App，布局未更改。APK2.0.2(14)构建、签名和网页资产一致性检查；不把源码提交等同手机已安装。
- 核心控制/鉴权/回执、语音/记忆/视觉/音乐逻辑有针对回归；真实模型及声学合成文件验证与假设备边界分别记录。
- 本机未加兼容配置的HF2.4/transformers4.46.3导入冲突及cuDNN native abort仍是已知事实。不得直接沿用stock GPU运行方式；下述兼容profile是本结论的必要条件。
- C++主机模拟、Python假控制器、JVM回环、Chromium都不是实板、手机、音质或电源验收。

正式PCM使用经配对认证的v2握手，旧历史指南中的v1不可直接沿用。新版APK、固件和PC版本应匹配；当前协议以network_audio.py/.cc及PHASE_A_NETWORK.md为准。

## 2. 经验证的PC运行配置

使用`C:\Users\Liu\anaconda3\envs\ai_cv_env\python.exe`（3.10.20），现有Torch2.5.1+cu121、transformers4.46.3、faster-whisper1.2.1和原角色权重。共享包与CUDA不在本轮改写。为避免污染，使用独立目录中的HF0.36覆盖包；约束见`pc-agent-vision/requirements-voice-constraints.txt`。不能把约束文件当完整模型/语音安装器。

本轮实际验证的目录是`C:\Users\Liu\.codex\cache\tasks\20261105-pro-final-audit`。后续可创建新的专属runtime目录，按同样方式准备与复核，不把本机私有模型/参考音频上传GitHub。

```powershell
$py = 'C:\Users\Liu\anaconda3\envs\ai_cv_env\python.exe'
$repo = 'C:\workspace\Intelligent-Lighting-Control-System-Pro'
$runtime = 'C:\Users\Liu\.codex\cache\tasks\20261105-pro-final-audit'
# 本轮overlay已存在。另建目录时，按文档准备兼容包而非修改共享环境：
# & $py -m pip install --no-deps --target "$runtime/runtime-overlay" huggingface-hub==0.36.0
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = "$runtime/runtime-overlay;$repo/pc-agent-vision"
$env:KURISU_CACHE_DIR = "$runtime/runtime"
New-Item -ItemType Directory -Force -Path "$runtime/tmp" | Out-Null
$env:TMP = "$runtime/tmp"
$env:TEMP = "$runtime/tmp"
$env:KURISU_AUDIO_TRANSPORT = 'wifi'
$env:KURISU_ASR_DEVICE = 'cpu'
$env:KURISU_TTS_CUDNN = '0'
$env:OPENAI_BASE_URL = 'http://127.0.0.1:11434/v1'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:KURISU_LLM_BACKEND = 'ollama'
& $py -B "$repo/scripts/pro_deployment_preflight.py"
```

preflight只核查模块、文件和配置；PASSED不是模型加载/整机或硬件通过。`KURISU_ASR_DEVICE=cpu`避免当前CTranslate/CUDA兼容路径，TTS仍可用CUDA运算但本进程cuDNN关闭；不更换角色模型/声线或信号处理。该后端选项会作用于同一Torch进程，尚未声称适用于任意其他模型/环境。

Ollama需由操作者正常启动现有`kurisu`模型，且端点与聊天/翻译一致。默认不绑定公网。模型不在时网页应降级显示，不伪造回答。语音失败后保持静音，不启用微软或电脑扬声器替身。

第三方GPT-SoVITS会写相对`GPT_SoVITS/configs`。运行正式服务前，将当前目录置于上述专属runtime目录，使用绝对脚本路径启动，避免第三方配置写入源码目录：

```powershell
Set-Location -LiteralPath $runtime
# 取得设备操作授权、完成下列备份/配对后，才运行真实设备服务：
# & $py -B "$repo/pc-agent-vision/web_server.py"
```

不要在此处自动启用摄像头或更改用户数据目录。个人记忆/脸库/校准仍在既有`KURISU_DATA_DIR`/LocalAppData；测试用隔离目录不能替代真实记忆库。LAN增强模式按[既有配对与Origin指南](PHASE_A_NETWORK.md)显式配置监听地址、访问令牌和来源，默认127.0.0.1不会被手机远程访问。

真实联动样例已经通过：当前VoiceListener构造器实际加载KWS/CPU Whisper，VoiceEngine实际加载原权重并生成双语WAV；共同驻留的Ollama→动态翻译→TTS→PCM也通过。该样例文本21.078秒、TTS12.281秒，不是稳定性能指标，不能宣称恢复中阶延迟。性能与实际声学质量尚待测量，不作为无限改写软件的理由。

## 3. 授权前准备（仅方案）

1. 人工确认真实开发板型号/Flash容量/PSRAM、供电和USB数据线，现场核对串口，不沿用历史COM9。
2. 确认安全启动/Flash加密状态及当前固件版本。若加密或无法恢复，停止套用普通备份/迁移流程。
3. 用户授权后先做只读完整Flash备份（确认16MiB后是0x1000000字节）及当前真实分区表、NVS备份，文件在仓库外；记录地址/大小/工具版本/SHA256，保留可恢复原件。不要打印或提交含Wi-Fi/配对/个人资料的备份。
4. 根据**实际旧表**核对新布局，不能因为源码是16MB就认为板上相同。旧布局不同时先制定逐分区迁移/恢复清单，再取得写入授权；不靠全片擦除规避问题。
5. 保留旧bootloader/分区表/otadata/app/NVS恢复地址、下载模式操作与可用USB恢复工具。备份存在不等于恢复已经实测。

当前新布局：NVS0x9000/0x6000、otadata0xf000/0x2000、phy0x11000/0x1000、ota_0 0x20000/0x600000、ota_1 0x620000/0x600000、storage0xc20000/0x3d0000。未经核对不可只刷App BIN。旧数据迁移与OTA回滚本轮未执行。

## 4. 授权后的首次受控顺序

1. 先确认安全供电、共地、数据方向和默认亮度20。软件限幅不替代电流、电压、温升及末端压降测量，不提高默认亮度。
2. 部署前单独取得准确的写入/安装授权。启动时可能有扬声器提示音，应提前告知用户；本轮没有进行任何听音。
3. 采集启动日志：显示/UDP/PCM/mic任务真实状态、内部堆/PSRAM/各任务栈。只见AP或网页不能判定整机健康；缺任务、音频初始化错误、栈接近耗尽或分配失败均停止扩大验收。新增安全降级允许灯控继续，但不将缺音频标为整机通过。
4. USB本地读取设备配对凭据，配置APK及PC受限令牌；不从UDP获取密钥。使用可信私人LAN/AP，明文协议没有加密防窃听保证。
5. 关闭PC后验证APK独立基本灯效、参数、倒计时、桌宠与代表街机，含Mario右+跳/独立释键、Pong双人。新版状态必须回读，不把请求已发当操作成功。
6. 再启动匹配的PC兼容profile，检查板载麦克风/KWS/ASR→语义→真实ACK→中日角色声线→恢复收音/连续轮次。只在此时按用户反馈验音色，不把静音生成文件当实际播放。
7. 独立启用摄像头、做校准，验证手动模式优先和停机释放；不替换为电脑麦克风或启发式情绪准确率宣传。
8. 测试本地曲库/MIR、音频与游戏音效优先/抢占/恢复；断网500ms释键/1000ms暂停及显式恢复；随后安排至少30分钟墙钟稳定性和正常退出/重新上电的高分恢复。

实机项目逐项写入验收矩阵新记录，不能直接把当前NOT_TESTED全部翻成通过。若出现新的真实P0/P1，修复复现问题；其余P2保留一次统一清单，不新增无限软件阶段。完成授权前的本轮软件收尾后停止。
