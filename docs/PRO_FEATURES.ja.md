# Pro の実装と導入

[简体中文](PRO_FEATURES.md) · [English](PRO_FEATURES.en.md) · **日本語** · [概要](../README_JA.md)

2026-10-25時点の実装状況です。ソース統合・オフライン検査・ビルドに加え、限定的な基板通信、音声、ジェスチャー、音楽追従の受入記録があります。**全機能の実機受入は未完了です。** 各試験は記録した版と条件にのみ適用します。[実機記録](hardware-checks-20261023.ja.md)を参照してください。

## 過去の18要件との対応

[過去のSRS](HIGH_STAGE_SYSTEM_SPEC_18.md) は設計資料であり、完成の証明ではありません。未測定の性能やハードウェアの想定値を成果として扱いません。

| 項目 | 現在の実装 | 範囲・設計上の相違 |
| --- | --- | --- |
| 1 単一S3 | `main.cc`：表示はCore 1、通信・音声はCore 0 | LLMと視覚処理はPC側です。 |
| 2 RMT DMA | `display_hal.cc` のマトリクス出力 | CPU使用率ゼロの測定結果はありません。 |
| 3 バッファ・Gamma | 描画バッファ、完成PWMスナップショット、共通ロック、任意Gamma | 非同期交換キューではなく、Gammaは既定で無効。安定60 FPSは未測定です。 |
| 4 既存効果 | 0–25の既存モード（18は未使用）、単一16×16パネルの配線方式を選択可能 | Midと毎フレーム同一という意味ではありません。 |
| 5 ローカルLLM | Ollama、`Modelfile.kurisu`、検証付き意味計画 | Qwen2.5を基にした設定で、独自モデル学習ではありません。 |
| 6 記憶 | SQLiteの事実・好み・会話、資料分割、削除可能なRAG | 既定は語彙ハッシュ、ローカルembeddingも設定可能。Mem0ではありません。 |
| 7 対話・MCP・小智 | 連続対話、HTTP/WS MCP、独立v1 Opusアダプター、任意Wi-Fi双方向音声・参照エコー処理・割込み | 起動語判定はPC側で板上WakeNetではありません。音響受入試験は未実施です。 |
| 8 タイマー | 専用1–86400秒命令、画素進捗、終了アニメーション、非同期通知音 | 砂粒物理ではなく、実精度・通知音は要測定です。 |
| 9 世界線 | モード28の数字が回転後 `1.048596` に固定、小数点・通知音列 | 演出であり計測器ではありません。電流音の実録ではありません。 |
| 10 手のサンドボックス | 共通カメラ、21点、つまみ・把持・投擲、相対z、重力・反発・波紋 | 単眼の相対深度で、メートル単位の校正済み3Dではありません。>60 FPSも未測定です。 |
| 11 視線・頭部姿勢 | 虹彩比率、9点アフィン校正、近似solvePnP | 内部パラメーターは近似。校正点の適合誤差は独立視線精度ではありません。 |
| 12 表情手がかり | EAR/PERCLOS、口・眉の幾何、疲労・しかめ面のヒント、微笑の演出 | 対話用ヒューリスティックで、心理・医療分類器ではありません。 |
| 13 ペット生活状態 | 待機・閉眼・口形、時刻・不在・疲労による状態 | 指定済み配色を保持。口形は音素同期ではありません。 |
| 14 無線音楽 | TCP 8889双方向PCM、ファイル・直接HTTP(S)音源、受信・再生カウンター | 16 kHz/PCM16/モノラルへ変換。原音形式の完全無損失を意味しません。 |
| 15 MIR音楽光環 | 1024点FFT、16対数帯域、RMS、フラックス、onset、拍位相で同心の四角い光環を駆動。16列スペクトルも選択可能 | 入力停止で減衰。拍推定は経験則。帯域分布は多声音楽の個別基音抽出ではなく、曲群精度・客観的な音画遅延は未測定です。 |
| 16 体感ゲーム | 停留・デバウンス付き手／校正視線でSnake・Tetrisを操作 | カメラ所有者は一つ。非互換モードの手動選択で自動制御を停止します。 |
| 17 DDA | 手動0–1難度、入力間隔・表情ヒントによる有界調整 | 速度下限を維持し、心理的フローを実証したものではありません。 |
| 18 クライアント・表示 | 画素編集、完成フレーム取得、WebGL、Android接続先・DNS-SD | 任意で正式C++のWASM表示。校正済み光学ツインではなく、Android実機も未評価です。 |

板上WakeNet、物理的な砂粒、原音仕様の無損失、物理光照射モデルはSRSと相違します。ソースの実装範囲から体感品質や性能を推定しません。

## サービス・モデル・データ

2026-10-24に固定方形、端点マーカー、全16行の先頭LEDで確認したところ、現在のパネルは各行とも左から右へ並んでいます。正式ビルドは `-DPRO_MATRIX_SERPENTINE=OFF` が既定です。実物が蛇行配線の場合は `ON` を指定します。この設定は全エンジンの座標変換とフレーム取得に適用され、RGB値は変更しません。

Python 3.10 と `pc-agent-vision/requirements-pro.txt` を使います。制御・Web・視覚・MIR・MCP・Opusを含みますが、Whisper・KWS・Torch・GPT-SoVITS・重み・参照音源は[過去の音声基準](VOICE_CONTROL_RECOVERY.md)に従い別途準備します。模擬モードはそれらをダウンロードしません。

入口は `pc-agent-vision/web_server.py`、現在の画面は実APIを操作する `/pro.html` です。

| 設定 | 既定値・用途 |
| --- | --- |
| `KURISU_DATA_DIR` | `%LOCALAPPDATA%/KurisuPro`：記憶、顔、視線校正、機器アドレス。Git外です。 |
| `KURISU_CACHE_DIR` | `~/.codex/cache/tasks/kurisu-runtime-<pid>`：音声キャッシュ・診断。テストは明示的に隔離します。 |
| `KURISU_CONTINUOUS` | `1`：応答後も受け付け、10秒無操作または終了句で待機へ。`0` は単一ターンです。 |
| `KURISU_AUDIO_TRANSPORT` | `usb`。`wifi` でTCP PCMを選択。既存USB変換・板側70%音量・音声基準を保持します。 |
| `KURISU_BARGE_IN` | 既定で無効。Wi-Fi時の `1` で実験的参照エコー処理・起動語割込みを有効化。無誘導ASR確認は残ります。 |
| `KURISU_ECHO_DELAY_MS` | `120`：参照音の実験的整列値で、音響校正結果ではありません。 |
| `KURISU_AUTO_MEMORY` | `1`：明示的な一人称の名前・好み・習慣を保存可能。`记住：…` は手動保存、画面から表示・削除・全消去。`0` で自動抽出を無効化。 |
| `KURISU_EMBED_MODEL` | 未設定なら語彙ハッシュ。導入済みOllama embeddingで `/api/embed` を利用し、表現変更時は保存記録を再計算します。 |
| `OLLAMA_HOST` | embeddingは `http://127.0.0.1:11434`、対話は既存 `OPENAI_BASE_URL` です。 |
| `KURISU_RENDERER_WASM` | 模擬表示用 `engine.wasm`。未設定では限定的な静的サンプルのみです。 |
| `KURISU_NODE_EXE` | 既定 `node`、オフライン描画プロセス用。 |

記憶・資料・顔・校正はローカル保存です。検索結果は参照文脈であり実行する灯光計画ではありません。モデルと個人データはコミットしません。

## 完全オフラインのプレビュー

次の経路は `127.0.0.1` のみにバインドし、シリアル探索、UDP、モデル読込、カメラ・マイク取得、再生を行いません。

```powershell
$task = Join-Path $env:USERPROFILE ('.codex\cache\tasks\pro-preview-' + [guid]::NewGuid().ToString('N'))
$env:KURISU_DATA_DIR = Join-Path $task 'data'
$env:KURISU_CACHE_DIR = Join-Path $task 'cache'
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

`http://127.0.0.1:8086/pro.html` を開きます。模擬対話は明確な文字どおりの灯光命令だけを処理し、任意の意味をLLMが理解したようには見せません。正式C++アニメーションにはClang/WebAssemblyと対応sysrootを使います。

```powershell
python -B scripts/build_offline_renderer.py --clang <clang.exe> --sysroot <wasm-sysroot> --output-dir "$task\engine"
node pc-agent-vision/offline_renderer.js "$task\engine\engine.wasm" --test
$env:KURISU_RENDERER_WASM = "$task\engine\engine.wasm"
python -B pc-agent-vision/web_server.py --simulate --no-audio --port 8086
```

正式Effect/Game/Spectrum/Interaction/Fingertipを使い、時刻・LED・音声インターフェースを置換します。ESP32スケジューラー、I2S、通信、電源は模擬しません。タイマー表示も実タスクではなく進捗サンプルです。WASM生成物はGitに含みません。

## 表示・視覚・音楽・ゲーム

- 直接モードは **0–31、18と25を除く**。25は時間指定が必須。26–31は指先、サンドボックス、世界線、画素キャンバス、音楽光環、環境光です。
- チームの指先コードをCMake、列挙、命令、表示ロック・タスクへ接続しています。[統合資料](../INTEGRATION.md)を参照し、複数プログラムによるカメラ競合を避け共通Web入口を推奨します。
- 視覚は明示的に有効化するまで停止します。手／視線ゲームは先に19/21を選びます。視線は9点校正が必要で、橙点を見てSpaceで採取します。カメラ番号変更前に停止してください。
- 非互換モード・タイマーの手動選択で自動切替を停止し、再有効化で復帰します。LBPHの挨拶機能を安全な本人認証とは扱いません。
- 顔登録は、動作中カメラ・現在の顔検出・**1秒以内**のサンプルが必要です。顔なし・空の切り出し・撮影停止／失敗でキャッシュを無効化し、ロック下で独立コピーを登録します。オフライン検証済みの鮮度条件であり、認識精度の保証ではありません。
- 音楽は20 MiB・30分までのアップロード／直接音源URLに対応します。アカウント・DRM・独自解析を要する全サービスには対応しません。失敗を状態表示し、停止で音声と特徴送信を中断します。
- 低域から高域を内側から外側の光環へ、RMSを全体強度へ、アタックを拡散パルスへ、拍位相を動きへ反映します。実際のPCM送信開始を基準に現在の窓を解析し、遅いACKで古くなった窓は飛ばします。`music.analysis`はコマンド送信統計であり、音響・光学遅延ではありません。再生中は動作中の音声待受を一時停止し、自分が停止した場合だけ終了時に戻します。
- DDAの操作間隔・顔幾何はヒントです。自動調整は無効化でき、手動難度も設定可能。既存ルール・結果表示は保持します。

## プロトコル

### HTTP・WebSocket

既存 `/api/chat`、`mode`、`volume`、`cmd`、`game`、`status`、`ceremony` と `/ws` を保持します。

| 経路 | 内容 |
| --- | --- |
| `GET /api/pro/frame` | 論理行優先のRGB 1536桁hexと `frame_source`。実PWM／模擬を区別。 |
| `POST /api/pro/canvas` | `{"hex":"<256 RGB pixels>"}` を全体検査・反映して29へ。 |
| `GET /api/pro/status` | 視覚・音楽・連続対話・小智接続状態。 |
| `GET/POST/DELETE /api/pro/memory` | 一覧・保存・id削除。POST `{"clear":true}` で全消去。 |
| `POST /api/pro/documents` | `{"text":"..."}`、最大100000文字を参照資料として分割。 |
| `POST /api/pro/vision` | `{"enabled":true,"mode":"pet","camera":0}`。pet/fingertip/sandbox/gesture_game/gaze_game/identity。 |
| `POST /api/pro/calibrate` | 非共線の `[iris_x,iris_y,target_x,target_y]` を5点以上。 |
| `POST /api/pro/enroll` | `{"name":"..."}`。上記の新鮮な現在顔が必須。 |
| `POST /api/pro/track-calibrate` | x0/y0/x1/y1、invert_x/invert_y。 |
| `POST /api/pro/difficulty` | `{"level":0.5,"adaptive":true}`。 |
| `POST /api/pro/music-upload?visual=fluid` | multipartではなく音声の生バイト。`visual=fluid`（既定の光環）または `spectrum`（16列）。 |
| `POST /api/pro/music` | `{"url":"...","visual":"fluid"}` または `{"stop":true}`。`visual`には`spectrum`も指定できます。 |
| `POST /api/pro/observations` | 模擬環境だけの合成観測。 |
| `POST /api/pro/device-tool` | 接続中の原生小智が公開したMCPツールを、対応schemaで検査して呼び出す。 |

### MCP

HTTP `/mcp` はinitialize、ping、tools/list、tools/call、セッション削除に対応します。初期化の `Mcp-Session-Id` を以降のヘッダーに返し、通知は202です。2024-11-05、2025-03-26、2025-06-18のJSON応答サブセットに対応し、SSEは提供しません。`/ws` は `{"type":"mcp","payload":{...JSON-RPC...}}` を受け付けます。

灯光・音量・タイマーに加え、`self.matrix.set_canvas/get_frame`、`self.game.set_difficulty`、`self.memory.remember/search`、`self.sensors.get_context` を提供します。観測には有効状態・鮮度・模擬ラベルを付け、schemaと実機ACKで成否を判断します。失敗はisErrorで返し、成功として読み上げません。

### 別々の無線音声入口

**Pro PCM：** `KURISU_AUDIO_TRANSPORT=wifi`、S3 TCP 8889。ヘッダーは `KAP1 + kind(u8) + length(u16BE)`、最大2048バイト、PCM16LE/16000/monoです。kind 4の握手は `pcm16le/16000/mono/v1`、1は再生、2はマイク、5はheartbeat。制御はUDP ACKのままで、再生はI2Sサンプル数を照合します。

**原生小智Opus：** 起動前に `KURISU_XIAOZHI_BRIDGE=1` を設定し、原生クライアントから `ws://<PC-IP>:8080/xiaozhi/v1/` に接続します。`Protocol-Version: 1`、helloはOpus/16000/mono・20/40/60 msです。listen/start/stop、abort、STT/LLM/TTS、Opus、双方向MCP探索を適応します。このモードとPro PCマイク受付は同時起動しません。

任意の `KURISU_XIAOZHI_TOKEN` でBearer tokenを要求できます。ASRは既存ローカルWhisperを遅延読込し、既定CPU int8、`KURISU_ASR_MODEL` / `KURISU_ASR_DEVICE` で変更します。キャラクターTTSは従来系です。サーバーのアダプターであり、外部小智のファームウェア変更・ビルド・書込みではなく、原生実機との連携は未試験です。

KAP1 PCMと原生Opusは**相互交換できません**。HTTP/UDP/PCMは信頼できる実験LAN向けで、直接の公開網利用は想定しません。

## Androidとビルド

初回にPCアドレスを設定するか、`_kurisupro._tcp` を探索・選択します。接続先を保存し、断線を表示します。任意zeroconfによるDNS-SD公開はLAN・ファイアウォールの実機確認が必要です。

MainActivity・Manifest・リソース・リポジトリassetsを上書きせず、生成物と一時debug鍵は指定した外部パスへ出力します。既存aapt2/R8、JDK、android.jar、zipalign/apksigner入りSDK Build Toolsを準備します。

```powershell
python -B android-app/build_apk.py --work-dir "$task\android-build-new" --output "$task\Kurisu-Pro-debug.apk" --build-tools <SDK-build-tools-dir> --java-home <JDK-dir> --android-jar <android.jar>
```

出力・作業先は新規パスが必要です。独立テスト署名APKは保存済みv1.0 APKを置換せず、インストールも未実施です。ESP32はESP-IDF 5.5.4を使用し、`PRO_MATRIX_DIAGNOSTIC` と `PRO_HAIR_CALIBRATION` を無効にします。オフラインビルドは隔離ソースと公開Wi-Fi設定を使い、私有設定を成果物へコピーしません。flash/monitorは行いません。

## オフライン検証と残る実機課題

入口は `tests/test_pro_runtime.py`、`tests/test_controller_validation.py`、`tests/test_face_enrollment.py`、`scripts/test_interaction_regressions.py`、`scripts/test_semantic_control.py`、`tests/test_kurisu_palette.py`、`tests/test_display_engines.py`、描画器の `--test` です。`KURISU_TEST_TMP` をタスク専用キャッシュへ、任意の `KURISU_TEST_RENDERER_WASM` をC++連携用に設定します。類似名の過去の上板スクリプトとは区別してください。

無線音声の断線・音質、AEC・誤割込み、連続音声、視覚閾値・独立視線誤差、明るさ・Gamma・通知音、FPS・CPU・スタック、Android導入・探索、長期動作は今後の実測項目です。ソースと模擬結果はこれらを代替しません。

参照：[小智WebSocket](https://xiaozhi.dev/docs/development/websocket/)、[小智MCP](https://xiaozhi.dev/docs/development/mcp/protocol/)、[Ollama embeddings](https://docs.ollama.com/api/embed)、[Android apksigner](https://developer.android.com/tools/apksigner)。本機の小智2.2.4 WebSocket v1実装も参照しています。

## 2026-10-24 配布修正と限定的な実機記録

- 256画素の画布はACK用の外包後に1631バイトのUDP負荷となり、一般的なMTU 1500の経路ではIPv4断片の再構成が必要です。`firmware-s3/sdkconfig.defaults` に `CONFIG_LWIP_IP4_REASSEMBLY=y` を追加しました。既存 `sdkconfig` はdefaultsだけでは更新されません。`idf.py menuconfig` でIPv4断片再構成を有効にし、実際の生成設定を確認して再ビルドしてください。
- PC・板側PCM socketでTCP_NODELAYを有効化しました。自動聴取前に意味解析モデルを予熱し、文脈4096・30分常駐を使います。予熱失敗時は自動聴取を開始しません。生成する起動語ファイルはモデルディレクトリではなく `KURISU_CACHE_DIR` に保存します。
- [2026-10-23の限定的な実機記録](hardware-checks-20261023.ja.md)に155項目の制御確認とUSB/Wi-Fi音声サンプル確認の範囲を示します。今回の配布ではビルドとオフライン回帰のみを行い、書込み・録音・再生はしません。
- `tests/test_delivery_regressions.py` は偽socket・モデルで画布設定、予熱失敗、起動語キャッシュを検査します。実機用 `scripts/test_pro_board.py` と `scripts/test_pro_audio.py` は適切な機器で明示的に実行する入口で、既定のオフラインテストではありません。
