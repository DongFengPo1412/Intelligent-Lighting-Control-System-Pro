# 统一 Web / Android 界面

2026-10-25：原首页与 Pro 控制台合并为一个前端。正式入口为 `/`；旧 `/pro.html`（包括 `#musicLibrary`）跳转至同一界面。没有新增第二套后端、音频链路或固件。

## 页面与使用

| 页面 | 内容 |
| --- | --- |
| 概览 | 红莉栖主题欢迎页、实际帧预览、快捷灯效、文字／板载语音对话、亮度与音量 |
| 灯光 | 全部直接模式、分类、2D／3D 实际帧预览、倒计时、世界线彩蛋、像素草稿与 JSON 导入导出 |
| 音乐 | 电脑本地曲库、中文歌名／歌手搜索、分页点播、上一首／下一首／停止、顺序／随机、单曲／列表循环、音乐光环／频谱切换、临时上传／直链 |
| 互动 | 蛇与方块触控手柄、聚焦后的键盘方向键、手动／自适应难度、主动启用的电脑视觉、视线校准与人脸登记 |
| 设置 | 服务与灯板连接、电脑曲库目录、记忆查看／删除、资料导入、状态诊断与主动播放自检提示 |

桌面采用侧栏；850 CSS 像素及以下采用底部导航，650 及以下主要卡片单列。支持键盘焦点、减少动画偏好和页面缩放。所有字体、图标与插画随项目提供，界面加载不依赖外部字体服务。

预览只画 `/api/pro/frame` 返回的像素；屏幕曝光、光晕与显示器亮度不代表灯珠实际观感。没有回读时显示等待／暂停，不用独立动画冒充在线设备。服务、灯板、模拟服务分别标示。世界线数字是作品彩蛋，不是测量结果。灯光滑块对应现有固件的 0–60 档值，扬声器滑块对应 0–100 音量。

对话灵感按钮只填写输入框，点击发送才执行。实际语音仍由板载麦克风和电脑服务承担。支持 SpeechRecognition 的安全浏览器上下文可额外显示浏览器听写按钮，仅填入文字，由浏览器提供识别服务；Android 外壳不使用此入口，也不请求手机麦克风权限。加载页面不会启动音乐、摄像头或自检声音。

视觉仍使用电脑摄像头，不是手机摄像头；视线校准宜在电脑浏览器上进行。人脸登记会保存电脑本地样本，需用户主动点击。曲库目录也是电脑目录，手机只是遥控器。

## Android 同源

`android-app/build_apk.py` 在构建时直接复制 `pc-agent-vision/web_app/`，排除历史 APK。旧 `android-app/assets/www` 维护副本已移除，避免修改两套界面。主机选择保存后总是打开 `/`，兼容迁移原有 `/pro.html` 配置。网页连接按钮在 APK 内调用原生连接设置；支持 DNS-SD 发现。

原生外壳处理系统栏／刘海边距、明确的文件选择、像素画布另存为，以及主页面连接失败时的同源离线外壳。离线不表示能控制硬件或独立运行模型。局域网服务需继续运行在电脑上。[构建说明](../android-app/README.md)。

Android 15 的系统栏适配参考 [Android 官方 edge-to-edge 文档](https://developer.android.com/develop/ui/views/layout/edge-to-edge)，WebView 行为参考 [Android 官方 WebView 文档](https://developer.android.com/develop/ui/views/layout/webapps/webview)。调试签名 APK 不等于正式发布版，物理手机安装、系统键盘／刘海、服务发现和文件选择尚需在目标手机验收。

## 视觉方向与素材

主题以牧濑红莉栖为主：深赭红发色、红领带与咖啡棕外套，搭配炭灰背景和暖珊瑚色操作按钮；保留未来道具研究所、LabMem 004 和 1.048596% 世界线彩蛋。参考角色资料来自 [作品官网](https://steinsgate.jp/sgflash.html) 和 [角川动画作品页](https://kadokawa-animation.jp/lineup/steinsgate)。界面为本项目实现，人物插画为新生成的主题素材，非官方授权原画；没有下载第三方角色图重新冒充原创。

新增插画为 `pc-agent-vision/web_app/assets/kurisu-hero.png`，imagegen 新图生成模式，无参考图、无二次修改。生成时要求透明背景，实际交付含暖色背景，界面采用 CSS 蒙版融合。原有 `kurisu.png` 未改动。最终生成提示词如下：

> Create one polished transparent-background character illustration asset for a personal Steins;Gate-themed smart lighting controller dashboard. Subject: Makise Kurisu from Steins;Gate, recognizable adult young scientist, long deep auburn red hair with subtle dark red shadows, violet-blue eyes, calm confident slightly curious expression, white collared shirt, vivid red necktie, classic tan brown jacket worn loosely over the shoulders, black shorts only partly visible. Tasteful nonsexual portrait, from head to upper thighs, no cropping of the hair/head, balanced natural anatomy. Three-quarter view slightly turned toward the viewer's left so she can sit on the right side of a website hero and look toward its text. High-quality anime editorial illustration, refined clean linework, restrained cel shading, soft warm amber rim light and burgundy accents, elegant and intelligent rather than cutesy. The character alone, no desk, no laboratory background, no frame, no text, no logo, no interface, no glow cloud, no checkerboard. Genuine transparent background and clean alpha edges. Compact vertical composition, useful as a responsive web hero cutout.

## 本次验证边界

已检查 JavaScript 语法、统一入口全部本地资源交付；服务／曲库／交付回归共 46 项，45 项通过，1 项可选 WASM 引擎测试因未配置而跳过。浏览器检查覆盖 320／390／768／1280 像素宽度，五页导航无横向溢出，模拟服务中检查灯效回读、中文曲库检索与点播／停止、倒计时、游戏手柄和像素画布／3D 切换。正式服务上已只读确认设备连接、2236 首曲库和实际灯板帧预览。Android 调试包完成编译、签名及打包资源与网页源的一致性检查。没有以模拟播放代替实际听音验收，没有重新打开摄像头或烧录固件；沿用此前已验收的音频和音乐随动链路。本次前端改动仍需用户在真实手机上确认操作手感。
