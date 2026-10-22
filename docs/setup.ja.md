# Pro 導入と操作

[简体中文](setup.zh-CN.md) · [English](setup.en.md) · **日本語** · [プロジェクト概要](../README_JA.md)

[構成](#structure) · [ハードウェア](#hardware) · [ファームウェア](#firmware) · [PCとモデル](#pc) · [操作](#operation) · [検査](#verification)

公開ネットワーク例を使った隔離ESP-IDF 5.5.4ビルドが成功し、イメージは874800バイトです。実C++エンジン11件とPython制御・資源解放9件が通過しました。C++は模擬時計・LED HAL、Pythonはシリアル・UDP・マイク・モデル未接続です。書込、録音、発音、新たな実機受入試験は行っておらず、過去の聴感・実機記録は本修正版の評価ではありません。

<a id="structure"></a>

## 構成と外部ファイル

```text
.
├── firmware-s3/
│   ├── CMakeLists.txt
│   ├── sdkconfig.defaults
│   ├── diagnostics/
│   └── main/
│       ├── main.cc
│       ├── CMakeLists.txt
│       ├── idf_component.yml
│       ├── wifi_config.example.h
│       ├── audio/
│       ├── display/
│       └── protocol/
├── pc-agent-vision/
│   ├── web_server.py
│   ├── kurisu_agent.py
│   ├── semantic_control.py
│   ├── voice_listener.py
│   ├── voice_engine.py
│   ├── wake_detector.py
│   ├── light_controller.py
│   ├── wifi_gateway.py
│   ├── Modelfile.kurisu
│   ├── requirements-wake.txt
│   ├── web_app/
│   └── faces/
├── android-app/
├── scripts/
├── tests/
├── docs/
└── INTEGRATION.md
```

主要構成で、独立視覚・周波数プログラムも`pc-agent-vision`です。モデル、秘密設定、`.runtime_deps`、キャッシュ、診断録音、ビルドは配布しません。既存の顔画像は過去の追跡リソースで、各利用者向け学習済みデータではありません。新規登録はローカルに保持し、今回は既存画像を追加・削除しません。

<a id="hardware"></a>

## ハードウェアと接続

| 部品 | 現在の設定 | 確認事項 |
| :--- | :--- | :--- |
| 主制御 | ESP32-S3、USB Serial/JTAG、Wi-Fi APSTA。 | 旧ディレクトリ名だけで型番を確定せず、8 MB Flashの既定も物理的根拠ではありません。 |
| パネル | 1枚16×16 WS2812B、256灯、GRB、GPIO17→DIN。 | 正面左上DIN、行ごと蛇行。黒データ2個は実LED258個を意味しません。 |
| INMP441 | WS4/SCK5/DIN6、I2S_NUM_1、16 kHz。 | 実モジュールの電源・GND・音声チャネルを確認。 |
| MAX98357Aとスピーカー | DOUT7/BCLK15/LRCK16、I2S_NUM_0、16 kHzの32ビット2スロット。 | モジュールが増幅を担い、インピーダンスや電源容量はコードから決まりません。 |
| 基板RGB | GPIO48、別RMT、DMAなし。 | 実ボードの搭載を確認。 |
| PC USB | 標準Serial/JTAG、VID/PID 303A:1001、なければCOM9。 | ポートは環境依存。音声は給電だけでなくデータ線が必要。 |
| Wi-Fi | UDP8888、STAとSoftAP共存。 | 到達できる同一ネットワーク、秘密設定、ログの実アドレス。 |

電源、レベル変換、配線、電圧降下、全体電流の完全な統制記録はありません。輝度20／上限60は5 V/1.2 A制限ではありません。実ハードに合わせ電源・共通GND・信号を設計し、輝度を容量保証とは扱いません。

<a id="firmware"></a>

## ファームウェア設定とビルド

主依存はIDF>=5.0、`espressif/led_strip:^3.0.2`、最近の確認可能な記録は**ESP-IDF v5.5.4**です。下限を満たすすべての版での成功は未確認です。既定ESP32-S3、8 MB Flash、Octal PSRAMは実ボードに照合します。ローカルsdkconfigとlockは追跡しません。

[wifi_config.example.h](../firmware-s3/main/wifi_config.example.h)を同じ場所の`wifi_config.private.h`へコピーし、STA/AP情報をローカル設定します。`.gitignore`で除外され、元PCの情報を公共文書へ写しません。

ESP-IDF端末でリポジトリのルートから：

```powershell
cd firmware-s3
idf.py --version
idf.py menuconfig
idf.py -DPRO_MATRIX_DIAGNOSTIC=OFF -DPRO_HAIR_CALIBRATION=OFF build
idf.py -p COMx flash monitor
```

新設定で対象未選択なら既存設定を保存して`idf.py set-target esp32s3`を行います。`COMx`を実ポートへ換え、占有するPCサービスを止めて書込みます。起動は17、輝度20、音量70です。

`PRO_MATRIX_DIAGNOSTIC=ON`はネット・音声なしの配線診断です。`PRO_HAIR_CALIBRATION=ON`はちらつきで不採用となった独立実験で、同時有効にはできません。日常運用は両方OFFとし、通常再現で旧調色や生成器を動かす必要はありません。

<a id="pc"></a>

## PC環境・モデル・依存

現在の本機環境はWindows/Python **3.10.20**です。ASRはCPU代替がありますが、GPT-SoVITSはCUDA設定です。全体の固定requirementsがなく、新環境の1回導入を保証しません。

| 機能 | 依存・リソース | 範囲 |
| :--- | :--- | :--- |
| 制御・Web | pyserial、NumPy、aiohttp、入口はTorch・音声も読みます。 | モデル依存を切り離した最小制御サーバーではありません。 |
| ASR/VAD | Torch、faster-whisper、webrtcvad、Whisper `base`。 | 初回取得は通信が必要な場合があり、ローカル推論と同梱は別です。 |
| 音響起動 | `sherpa-onnx==1.13.8`、`sherpa-onnx-core==1.13.8`、`models/wake_kws`。 | [記録](VOICE_CONTROL_RECOVERY.md)を参照。モデル・私有依存は未追跡。 |
| 言語モデル | Ollama、`qwen2.5:7b`、`Modelfile.kurisu`。 | 人格設定で、独自LLM学習ではありません。 |
| TTS | NumPy、SciPy、GPT-SoVITS、BERT/HuBERT、キャラクター重み・参照、任意noisereduce。 | Torch/CUDA互換環境が必要で、モデルは配布しません。 |
| 任意視覚 | OpenCV contrib、MediaPipe `solutions`、Torch。 | 別起動しAPIを確認、OpenCV重複導入を避けます。 |
| 任意周波数表示 | PyAudio、NumPy、利用可能な音声入力。 | 自動回線ループバックやスマートフォン入力ではありません。 |

言語モデル準備は学習ではなくダウンロードです：

```powershell
ollama pull qwen2.5:7b
ollama create kurisu -f pc-agent-vision/Modelfile.kurisu
ollama list
```

Ollamaの`http://localhost:11434`を確認します。既定`OPENAI_BASE_URL`は`http://localhost:11434/v1`ですが、意味計画はOllamaを明示要求し、別の互換APIへ換えても全経路は保証しません。

ウェイク依存は既存の隔離構成へ入れ、モデルは別途準備します：

```powershell
python -m pip install --target pc-agent-vision/.runtime_deps -r pc-agent-vision/requirements-wake.txt
```

`wake_kws`には`tokens.txt`と`wake_detector.py`命名のepoch-12 INT8 encoder/decoder/joinerが必要です。キーワードは初期化時に生成し、資源不足・不一致は自動起動を無効にして、自由転写へ後退しません。

TTSは`models/GPT-SoVITS`、`models/pretrained_models/chinese-roberta-wwm-ext-large`、`chinese-hubert-base`、`models/kurisu_tts/{kurisu-e15.ckpt,kurisu_e4_s972.pth,prompt_shy.wav}`を使います。ルートの別`GPT_SoVITS`では自動代替できません。出典と依存を合わせ、重み不在で合成再現済みとはしません。

<a id="operation"></a>

## 起動と機能操作

USBとUDP8888を別サービスが使用していないことを確認し、主要入口は1本にします。Web起動はモデル・ハード・キャッシュを初期化し、接続確認音が鳴る場合があります。

```powershell
python pc-agent-vision/web_server.py
```

PCは`http://localhost:8080`、スマートフォンはログのPC LANアドレスを使います。`/api/status`の`wifi.wifi_online`、`audio_usb_connected`、`board_audio_recent`、`wake_detector_ready`とエラーを確認します。サービス、基板、音声の接続は別で、初期ラベルやアニメーションは実機証明ではありません。

ウェイク→必要時応答→完全な1命令→基板確認→中日応答→待機です。色、星／波紋、計時、輝度／音量を試し、次は再ウェイクが必要です。再生中はマイク送信を止め、同時聴取しません。

Webでモード、直接輝度、音量、タイマー、ゲームを操作します。ファームウェア0–60、PCは1–60へ制限、意味解析の百分率は最大60換算で、20は20%ではありません。タイマーは秒数を指定し、25選択だけで開始を期待しません。ゲームS/dropは1マス下降です。

AndroidのAPKと[ソース](../android-app)はWebViewで、PC URL設定が必要です。作者環境のJDK17/Android35パスを適合させます。内蔵assetsは古い場合があり、オフラインUIはPCモデルや通信の代わりになりません。再パッケージは既定手順にしません。

以下はカメラ・音声を占有したり実機を操作します。競合を停止し、個別起動します：

```powershell
python pc-agent-vision/vision_gesture.py
python pc-agent-vision/vision_face.py
python pc-agent-vision/vision_tracker.py
python pc-agent-vision/audio_visualizer.py
```

全行を同時起動しません。手はq/Esc、顔はS/T/Q、背景視覚・周波数はCtrl+Cです。顔挨拶は発声し得て、周波数はPC入力を使います。旧`b 150`は範囲外なので[既知問題](technical-notes.ja.md#vision-audio)を参照し、終了表示で成功と扱いません。ルート指先は正式モードではありません。

<a id="verification"></a>

## 検査と切分け

以下は実機を開かず全モデルも読まない検査で、NumPy/SciPyの互換環境で行います：

```powershell
python scripts/test_interaction_regressions.py
python scripts/test_semantic_control.py
python -m unittest discover -s tests -p test_kurisu_palette.py
node --check pc-agent-vision/web_app/app.js
node --check android-app/assets/www/app.js
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/matrix_layout_test.cpp
xtensa-esp32s3-elf-g++ -std=c++14 -fsyntax-only tests/srgb_transfer_test.cpp
```

`test_semantic_control.py --live`はOllamaのみですが、`test_board_ack.py --silent`は実LEDを操作します。総合試験はモデル、マイク、表示変更、音声を扱い得るため、一括実行しません。過去の書込・声光確認と今回のオフライン結果は[技術ノート](technical-notes.ja.md#implementation-status)で区別します。

| 現象 | 確認箇所 |
| :--- | :--- |
| Webは開くがLED不変 | UDP、ビーコン、ACK/requestID。HTTPだけで実機確認とはしません。 |
| Wi-Fiはあるが音声なし | USBデータ、PCM、最近の基板音声、KWS/Whisper/TTS。 |
| 成功文だけで動かない | 構造化計画とACK、古いスクリプト・説明と現行通信の差。 |
| 毎回ウェイクが必要 | 現行の単発方針で、連続会話が修正済みではありません。 |
| Webと実物が異なる | Canvasは独立で読戻しなし、キャラクター図も異なります。 |
| 色が目標に合わない | 部位配色と実物評価。自動生成検査は目視合格ではありません。 |
| 採音と再生が干渉 | 停止の所有、サンプル差分、破棄・エラー・スタック。PC書込みだけでは不十分です。 |


倒計時は1–86400の整数秒を指定する専用命令を使います。直接モードは0–24のうち18を除き、時間なしの25はPC・ツールSchema・ファームウェアで拒否します。独立のジェスチャー・周波数スクリプトはWi-Fi制御状態を確認し、有効な輝度20へ戻します。USB音声接続は制御の前提ではありませんが、カメラ・モードの統一調停は未実装です。

公開ネットワーク例を使った隔離ESP-IDF 5.5.4ビルドが成功し、イメージは874800バイトです。実C++エンジン11件とPython制御・資源解放9件が通過しました。C++は模擬時計・LED HAL、Pythonはシリアル・UDP・マイク・モデル未接続です。書込、録音、発音、新たな実機受入試験は行っておらず、過去の聴感・実機記録は本修正版の評価ではありません。

`requirements-control.txt` は制御クライアント用pyserial 3.5のみを固定し、Web・視覚・音声全体を構築するものではありません。全依存は未固定で、外部モデル・元の機器パスの設定が必要です。保守修正は過去記録を保持し、全フレームワーク・モデル・素材の個人独創を意味しません。

```shell
python -m pip install -r pc-agent-vision/requirements-control.txt
```
