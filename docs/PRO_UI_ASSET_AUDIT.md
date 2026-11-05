# Amadeus 界面资产审查（2026-11-05）

本次逐一查看实际图片，并核对 Git 引入记录及 `docs/UNIFIED_WEB.md`。文件名、相似角色外观与公开仓库均不构成官方授权证据。本轮没有下载网络角色插画，没有修改已确认的16×16桌宠素材。

| 资产 | 实际内容与用途 | 可查来源 | 处理与边界 |
| --- | --- | --- | --- |
| `pc-agent-vision/web_app/assets/kurisu-hero.png` | 红棕长发、白衬衫、红领带、棕外套的红莉栖主题插画；首页、头像 | Git `8557696`；UNIFIED_WEB 保存了 imagegen 生成方式与提示词 | 保留；生成素材，非官方原画或官方授权证明。实际有暖色背景，采用现有蒙版，未宣称透明抠图。 |
| `pc-agent-vision/web_app/assets/kurisu.png` | 红棕发侧脸简化图；当前页面未引用 | Git `32c4a0c`；没有查到作者/授权原件 | 保留历史文件；来源及发布许可未核实，不称为原创或官方素材。 |
| `pc-agent-vision/web_app/assets/icon.png` | 航天器图标，与本次Amadeus主题不符 | Git `32c4a0c`；没有查到授权原件 | 当前 favicon/PWA 不再引用；保留历史文件，没有擅自删除。 |
| `android-app/res/mipmap-*/ic_launcher*.png` | 同一航天器图案的原生多尺寸图标 | 旧工程资源；没有查到独立许可证据 | Manifest 不再引用，改为下面的原创矢量图。旧文件仍保留，构建中可能仍含未引用资源；本轮不宣称已完成全部历史素材许可清理。 |
| `pc-agent-vision/web_app/assets/amadeus.svg` | 本项目代码绘制的A字母、仪表圆环、琥珀刻线 | 本次源代码 | 用作favicon/PWA；不含外部插画，不称为官方Amadeus商标。 |
| `android-app/res/drawable/amadeus.xml` | 上述图形的Android矢量版本 | 本次源代码 | 用作APK普通/圆形图标，不依赖来源不明的航天器图片。 |
| 页面内SVG图标、CSS背景与数字仪表 | 原有本地代码图形及本次暗红/暖琥珀排版 | index.html/style.css及Git历史 | 保留现有体系；未引入第三方图标包或外部字体文件。 |

保留的角色题材与历史素材不等于获得作品IP的再分发授权。发布范围或商业使用前，尚需核对角色权利及未知历史图片来源。本报告只陈述证据，不代替授权文件。

网页与APK共用同一份HTML/CSS/JS与100款简介。已用实际Chrome检查360×800、390×844、844×390、1440×1000，五页无横向溢出；完整简介不裁切，选卡摘要允许折叠。Android实机触摸、安全区及图标观感仍待安装后验收。截图是软件界面，不是物理LED照片。
