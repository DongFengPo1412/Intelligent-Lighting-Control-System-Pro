> **历史基线 / Historical baseline / 過去の基準**：下文保留本轮扩展前的审计与操作记录。它不描述当前所有功能；当前实现、架构差异与安全的离线运行方式见 [PRO_FEATURES](PRO_FEATURES.ja.md)。Prior audit/setup content is retained below; use the linked current guide for this revision.

# Pro 技術ノート

[简体中文](technical-notes.zh-CN.md) · [English](technical-notes.en.md) · **日本語** · [プロジェクト概要](../README_JA.md)

[ソース](#source-map) · [ドライバ](#driver) · [描画とゲーム](#display) · [音声とエージェント](#voice-agent) · [通信](#transport) · [独立プログラム](#vision-audio) · [状態と根拠](#implementation-status)

基準コミットは`d548868`です。現行ソース、設定、確認できる記録を根拠とし、[18項仕様](HIGH_STAGE_SYSTEM_SPEC_18.md)は過去の要求で、完成証拠とは扱いません。

<a id="source-map"></a>

## モジュールと対応ソース

| 入口・モジュール | ファイル | 実際の役割 |
| :--- | :--- | :--- |
| ファームウェア入口 | [main.cc](../firmware-s3/main/main.cc)、[CMake](../firmware-s3/main/CMakeLists.txt) | 表示、基板LED、I2S、USB、APSTA/UDPを初期化。既定は17で、診断入口は明示選択。 |
| ピクセル出力 | [display_hal.cc](../firmware-s3/main/display/display_hal.cc)、[matrix_layout.h](../firmware-s3/main/display/matrix_layout.h) | 256画素のアプリバッファ1個、蛇行変換、輝度、RMT DMAと転送。 |
| モードと描画 | [display_manager.cc](../firmware-s3/main/display/display_manager.cc)、[effect_engine.cc](../firmware-s3/main/display/effect_engine.cc) | モード初期化、タスク、計時、照明、表情、キャラクター。 |
| ゲームと周波数表示 | [game_engine.cc](../firmware-s3/main/display/game_engine.cc)、[spectrum_engine.cc](../firmware-s3/main/display/spectrum_engine.cc) | 2ゲーム、得点、帯域描画とピーク保持。 |
| 命令とネットワーク | [command_dispatcher.cc](../firmware-s3/main/protocol/command_dispatcher.cc)、[wifi_manager.cc](../firmware-s3/main/protocol/wifi_manager.cc) | USBテキスト／PCM分離、音声リング、命令、UDP応答キャッシュ。 |
| I2S | [audio_hal.cc](../firmware-s3/main/audio/audio_hal.cc) | INMP441入力、MAX98357A出力、PCM変換、再生排他、待機クロック停止。 |
| PCサービス | [web_server.py](../pc-agent-vision/web_server.py)、[light_controller.py](../pc-agent-vision/light_controller.py)、[wifi_gateway.py](../pc-agent-vision/wifi_gateway.py) | HTTP/WS、会話直列化、USB音声、UDP確認。 |
| 音声と計画 | [voice_listener.py](../pc-agent-vision/voice_listener.py)、[wake_detector.py](../pc-agent-vision/wake_detector.py)、[semantic_control.py](../pc-agent-vision/semantic_control.py) | VAD、KWS、Whisper、効果一覧と引数検証。 |
| 対話と合成 | [kurisu_agent.py](../pc-agent-vision/kurisu_agent.py)、[voice_engine.py](../pc-agent-vision/voice_engine.py)、[light_tools.py](../pc-agent-vision/light_tools.py) | 短期会話、ツール、二言語応答、GPT-SoVITSとキャッシュ。 |
| クライアント | [Web JS](../pc-agent-vision/web_app/app.js)、[Android Activity](../android-app/src/org/fglab/kurisu/MainActivity.java) | 操作、独立Canvasアニメーション、WebView。 |

Webは`vision_gesture.py`、`vision_face.py`、`vision_tracker.py`、`audio_visualizer.py`を自動起動しません。`firmware-s3/main/display/fingertip_tracker.*`は正式CMakeに含まれず、26／trackの解析・列挙もありません。[INTEGRATION](../INTEGRATION.md)は統合待ちの提案です。

<a id="driver"></a>

## 1枚パネル・RMT・タスク

正面左上DIN、偶数行は右、奇数行は逆の1枚16×16です。範囲外は-1で、二次元描画は共通変換を使います：

```math
i(x,y)=16y+\begin{cases}x,&y\bmod2=0\\15-x,&y\bmod2=1\end{cases},\qquad 0\le x,y<16
```

GPIO17はWS2812のGRBです。`led_strip_new_rmt_device`は10 MHz、128シンボル、`with_dma=true`で258位置を確保し、256実画素後に黒データ2個を送ります。追加実LEDではなく転送の余裕です。リセット時間はライブラリ次第で、コメントの280 μsは測定根拠ではありません。

描画は優先度5でCore1、USB・音声とUDPはCore0です。通常は更新後33 ms待機、スペクトル20 ms、得点100 msに加え、描画・転送・基板LED・タスクの時間が必要です。DMAはCPUゼロを意味せず、`led_strip_refresh`はアプリのフレーム交換キューではありません。Front/Back交換はなく、安定60 FPSやダブルバッファとは主張しません。

起動輝度20、プロトコルは0–60、各色は概ねRGB×brightness/255です。MidのFastLED 5 V/1200 mA推定器はなく、輝度上限は物理電流制限ではありません。GPIO48は別RMTで`with_dma=false`、接続・聴取・思考・再生を示します。全LEDがDMAとは扱いません。

共通再帰ミューテックスで描画、モード・ゲーム・周波数入力、輝度、計時を直列化し、描画タスクの休止前に解放します。ゲーム終了時の内部モード変更は再入可能です。単一タスクFIFOではなく、ACKはシステム全体の原子的スナップショットでもありません。高度な直接エンジン参照は呼出し側の同期が必要です。

<a id="display"></a>

## 照明・キャラクター・計時・ゲーム

### モード一覧

0–25のうち18を除く25番号です。消灯と得点も含むため、25種類の動的照明ではありません。

| 番号 | 実装 |
| :--- | :--- |
| 0、1/2/3 | 消灯、赤／青／緑。 |
| 4–10 | 斜めHSV虹、空間正弦極光、2流星、14個の星の寿命、全面変色、乱数雨、2重波紋。 |
| 11–14 | 笑・泣・無表情・巡回。瞬きと目の移動は事前アニメーションで、ユーザー視線追跡ではありません。 |
| 15、16/17 | スペクトル、16と17は同じキャラクター描画。 |
| 19/20、21/22 | スネーク／得点、テトリス／得点。 |
| 23/24/25 | 乱数冷却と近傍熱伝搬、列別速度・長さのコード雨、経過時間計時。 |

虹、極光、星、波紋、表情は現在の独立実装で、Midの画素単位複製ではありません。炎はPerlinノイズを使わず、コード雨も読める数字を描きません。実際の熱配列と画素列として説明します。

### キャラクターと配色

待機、閉眼、口2枚の4フレームです。スピーカー有効中に140 msで口を交替し、それ以外はランダム間隔で約160 ms瞬きします。I2Sは待機約800 ms後に止まるため、音声後も口が動き得ます。音素・振幅包絡・時刻同期や、昼夜・あくび・睡眠モデルはありません。

[生成器](../scripts/update_kurisu_sprites.py)は原画RGB、部位、表示上書き、LED目標PWMを分け、[フレーム](../firmware-s3/main/display/kurisu_sprites.h)を出力します。基準輝度B=20の目標qに対して：

```math
c=\left\lceil\frac{255q}{20}\right\rceil,\qquad p=\left\lfloor\frac{cB}{255}\right\rfloor
```

指定輝度の整数出力を守る式で、物理色度・輝度・画面との一致ではありません。現在係数100%、`Show`はsRGBを再復号しません。`srgb_transfer.h`は任意変換として残り、旧Gamma表の存在は正式表示の一律Gamma処理を意味しません。

独立256画素[fixture](../tests/fixtures/kurisu_design_hex.txt)に元データを保存します。肌4画素・消灯2画素・外套と同色のズボンはユーザー要求の表示上書きで、原画そのままとは表現しません。輪郭は濃い茶色に届かずオレンジに見え、4相点滅は不採用です。[調整履歴](KURISU_VISUAL_TUNING.md)に記録しています。

### カウントダウンと世界線演出

1–86400秒を受け、sleep累積ではなく`get_millis()`差分で計算します：

```math
N_{\mathrm{on}}=\left\lfloor256\max\left(0,1-\frac{t-t_0}{T}\right)\right\rfloor
```

境界画素を減光し、進捗を緑・橙・赤で示します。満了後約1500 msの全画面提示で消灯し、誤差実測・砂粒物理・専用終了音はありません。25を選ぶだけでは時刻を初期化せず、`countdown`が必要です。

「世界線」はPCのfire→meteor→matrix→dynamic、待機0.35/0.35/1.2 sです。Webは固定1.048596%を表示し、基板の数字計器、乱数停止、専用放電音はありません。キャラクター台詞を測定とは扱いません。

### ゲームと境界

Snakeは256座標、初期長3、16×16折返し、自身衝突を維持します。空きマスを有限列挙して選び、旧末尾を保持して成長し、満盤で終了します。最新方向を各ステップ1回確定し、直前確定方向への逆転を拒否します。速度下限は80 msで、任意多桁の得点表示は未完成です。

Tetrisは7形状×4向き、16×16配列、x=3..12の10列を維持し、衝突・回転・固定・消行・得点を実装します。初期800 ms、1行30 ms短縮で下限100 msです。dropは1マス下移動で、ハードドロップ、壁蹴り、DDAはありません。

<a id="voice-agent"></a>

## ローカル音声と意味計画

### ウェイクと単発状態機械

I2S_RXは16 kHzモノラル・32ビットスロットで、`ReadMic`が16ビット右シフトしてPCM16をUSB送信します。PCは30 ms／480サンプルで直流成分の除去、WebRTC VAD2、適応的なRMS判定を行います。発話開始には2フレーム、待機時／命令待ち時の終了判定には無音16／36フレームを使い、短い音声にはSileroによる補助確認を行います。コメントの3フレームは旧記述です。

待機中はSherpa ONNX Zipformer KWSの閾値0.50で音響検出し、その後、初期プロンプトなしのWhisperで確認します。設定された呼び名が発話の先頭に必要で、音響的な根拠のない転写だけでは起動しません。WhisperはCUDA float16優先、失敗時はCPU int8を使い、KWSが利用できなければ自動ウェイクを無効にします。操作のない状態が10 s続くと待機へ戻りますが、発話・処理・キュー待ちの途中では打ち切りません。

名前と命令を同時に話せば直接実行、名前だけなら応答後1命令を待ち、不完全な前置句は次の区間へ保持します。処理・読み上げ中はマイク送信を止め、終了後は`is_awake=False`で再開します。連続対話やAEC全二重ではありません。

### 計画検証と対話

`semantic_control.py`は効果名、JSON Schema、完全定型命令、数値句の抽出、検証、最大1回の修正要求です。効果名をコードで番号へ変換し、不正引数、雑談への操作混入、計時開始停止の矛盾を拒否します。競合表示は確認へ回し、操作は最大4件です。

`kurisu_agent.py`は制御計画だけを実行し、人格文の疑似ツールを実行せず、同一ターンの重複操作を抑制します。成功はACKに依存します。会話は約12往復の完全な直近履歴をメモリ保持し、Mem0・永続ベクトル・長期記憶はありません。`Modelfile.kurisu`は`qwen2.5:7b`への人格と生成設定で、LLM学習ではありません。

`light_tools.py`にはMCPという名称と関数スキーマがありますが、実際はローカルPython関数への振り分けで、MCP JSON-RPCのディスカバリやセッション管理を備えたサービスではありません。S3はMidの小智クライアントを継続実行せず、基板の小智MCP双方向統合とは主張しません。

### 合成とPCM再生

`voice_engine.py`は外部GPT-SoVITS v2Pro、BERT/HuBERT、参照音声を読み、独自学習経路はありません。中日を別合成し両方成功時180 ms無音、フィルタ・任意noisereduce・EQ・正規化を経て32 kHz WAVを保存し、`resample_poly`で16 kHzへ変換します。モデル不在でシステムTTSへは移らず、基板USB不在時にWindows再生経路はありますが、全OS対応の保証ではありません。

PCM16を2個の32ビットI2Sスロットへ複製し、音量設定の二乗に比例するデジタルゲインを掛けます。音圧測定ではありません：

```math
g=\left\lfloor65536(V/100)^2\right\rfloor,\qquad s_{32}=\mathrm{clip}_{32}(s_{16}g)
```

PCは累積バイトと単調時計から120 msの先行送信を目安にします：

```math
t_{\mathrm{send}}=t_0+\frac{B_{\mathrm{sent}}}{2\times16000}-0.120
```

32 KiBリングを8192バイトスタックの再生タスクが消費します。前後の`audio_rx/audio_played/audio_dropped/audio_errors`を比較し、同じサンプル増分、破棄・エラーなしを要求します。`audio_played`は完全I2S書込数で聴感ではありません。入力と出力の同時AECや原音の可逆再生ではありません。

<a id="transport"></a>

## USB・Wi-Fi・操作画面

USBマイクは`55 AA len_hi len_lo PCM16LE`、再生は`AA 55 len_hi len_lo PCM16LE`で、長さはビッグエンディアン、PCMはリトルです。再生負荷は最大2048バイト、CRCとフレームタイムアウト復帰はありません。USBもテキスト／JSONを解析しますが、PC通常制御はUDP8888です。

要求形式は`{"request_id":"...","command":"..."}`で、既定の応答待ちは0.6 s、再試行は2回です。S3は送信元IPとIDをキーに最大16件・30 sの結果を保持し、同じIDの異なる命令は競合とします。有限キャッシュであり、無期限のExactly-once配送を保証しません。ACKは命令処理の確認で、光・音の受け入れ確認ではありません。STA+SoftAP、約2 sのビーコン、タイマーによる再接続を使います。

HTTP8080は`/api/chat`、`mode`、`volume`、`cmd`、`game`、`status`、`ceremony`、`/ws`は会話・モードを通知します。Canvasは独立関数と時刻で描き、スペクトル・ゲーム・キャラクターは基板ピクセルの読戻しではありません。世界線もUI演出で、Three.js・WebGL・デジタルツインではありません。

AndroidはJava WebViewでPC URLを優先し、失敗時は内蔵assetsへ移ります。内蔵JSと現行Webは異なり、fileページの相対`/api`は自動でPCへ接続しません。ActivityアドレスとSDKパスは作者環境依存で、APKだけで単独S3操作が完成するわけではありません。HTTP/UDPは利用者認証を実装せず、ローカル実験ネットワークを前提とします。

<a id="vision-audio"></a>

## 独立した視覚・音声入力

| プログラム | 実装 | 制約 |
| :--- | :--- | :--- |
| [vision_gesture.py](../pc-agent-vision/vision_gesture.py) | MediaPipe片手x/y規則、0消灯、1赤、2／ピースでキャラクター、3炎、4コード雨、5虹。 | 結果変化と前回から>0.6 sであり、同姿勢保持0.6 s判定ではありません。USB接続フラグが送信条件、3D把持投擲なし。 |
| [vision_face.py](../pc-agent-vision/vision_face.py) | Haar検出・100×100グレースケールLBPH、S保存／T再学習、ylk赤、zzc青、他は笑顔、挨拶には15 sの間隔。 | ライブネス検出・認証用途の安全性評価なし。同期合成でGUIが止まり得て、オンライン増分学習ではありません。 |
| [vision_tracker.py](../pc-agent-vision/vision_tracker.py) | Face Meshの口幅／高さ>2.8で笑顔、時間で動的表情へ戻り、在席を記録。 | 幾何規則で、感情・頭部姿勢・注視点・疲労分類ではなく、不在節電もありません。 |
| [audio_visualizer.py](../pc-agent-vision/audio_visualizer.py) | PyAudio既定16 kHz、512点Hann/rFFT、16帯域平均、ピーク正規化、対数振幅、低域急増。 | PC入力で、スマートフォン／システム再生の自動取得ではありません。Web自動起動・MIR流体なし。 |

帯域境界はMid由来ですが、レートと定数が異なります。P初値0.05、窓ごと0.96倍、下限0.01。平均a_iから：

```math
P_t=\max(0.96P_{t-1},\max_i a_i,0.01),\qquad
b_i=\left\lfloor15\frac{\ln(1+9a_i/P_t)}{\ln10}\right\rfloor
```

周波数描画は経験的減衰と白いピークを維持し、`last_feed_time_` を500 msの断流判定に使って旧目標を消去します。この閾値は通信全体の遅延評価ではありません。

視覚／周波数スクリプトの`b 150`は0–60外で拒否され、復帰の表示文は成功証拠ではありません。視覚はカメラを取り合い、音声／Webのモードを上書きし得て、統一調停はありません。未接続指先コードで不足を補ったことにはしません。

<a id="implementation-status"></a>

## 検証・未完成部分・今後

公開ネットワーク例を使った隔離ESP-IDF 5.5.4ビルドが成功し、イメージは874800バイトです。実C++エンジン11件とPython制御・資源解放9件が通過しました。C++は模擬時計・LED HAL、Pythonはシリアル・UDP・マイク・モデル未接続です。書込、録音、発音、新たな実機受入試験は行っておらず、過去の聴感・実機記録は本修正版の評価ではありません。

過去の[音声修正](VOICE_CONTROL_RECOVERY.md)は固定30例、確認済み実音声2例、音量ゼロで223360サンプル書込を記録します。異なる範囲を認識率・聴感評価に合算しません。[パネル検証](MATRIX_16X16_VALIDATION.md)は診断図と複数モードのユーザー確認です。73/74件には可変の状態ポーリングを含み、同一固定基準ではありません。

最新配色は873920バイトで、ローカルSHA256が`pants_match_coat_validation`と一致し、ビルド・書込と輝度20／モード17／採音停止ACKを確認できます。過去の根拠であり、今回の新測定ではありません。濃い茶色は目視確認が未完了で、安定した数値出力は色校正ではありません。

| 状態 | 内容 |
| :--- | :--- |
| 追跡できる主実装 | 1台ドライバ、照明／キャラクター／ゲーム／計時、UDP ACK、単発音声、Web操作。 |
| 独立・統合未評価 | 視覚3本、PyAudio周波数、Androidとオフライン画面、指先ソース。 |
| 今後の目標 | 連続会話、MCPサービス、永続記憶、視線／姿勢／疲労、把持投擲、体感ゲーム、DDA、無線音声、MIR、3Dツイン。 |
| 残る制限 | 残る制限はブラウザと実機状態の差、カメラ・モード調停、任意多桁得点、外部モデル・環境、古いAndroid内蔵ページです。新しい排他、断流、入力処理は実機確認が必要です。 |

`requirements-control.txt` は制御クライアント用pyserial 3.5のみを固定し、Web・視覚・音声全体を構築するものではありません。全依存は未固定で、外部モデル・元の機器パスの設定が必要です。保守修正は過去記録を保持し、全フレームワーク・モデル・素材の個人独創を意味しません。

2026-10版では周波数項目・範囲を検査し、拒否を呼出し元へ返します。500 msの断流後は目標をゼロにして減衰し、ゼロ入力で底行・ピークを点灯し続けません。Snakeは食物回避、旧末尾保持、満盤終了、各ステップ1回の方向確定を修正し、80 msを厳密下限としました。Tetrisは100 msを下限とし、描画、モード・ゲーム・周波数入力、輝度、計時を共通の再帰ミューテックスで保護します。

倒計時は1–86400の整数秒を指定する専用命令を使います。直接モードは0–24のうち18を除き、時間なしの25はPC・ツールSchema・ファームウェアで拒否します。独立のジェスチャー・周波数スクリプトはWi-Fi制御状態を確認し、有効な輝度20へ戻します。USB音声接続は制御の前提ではありませんが、カメラ・モードの統一調停は未実装です。
