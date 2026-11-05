# Mid / XiaoZhi notification sounds

`mid_success.wav` and `mid_popup.wav` are decoded derivatives of
`main/assets/common/success.ogg` and `popup.ogg` in the owner's existing
`Intelligent-Lighting-Control-System-Mid/esp32-s3r16n8-idf` checkout.
That source distribution carries the MIT license reproduced in
`XIAOZHI_LICENSE.txt` (Shenzhen Xinzhi Future Technology Co., Ltd. and
Project Contributors, 2025).

The source Opus notifications were decoded to mono 16-bit PCM at their original
16 kHz rate, without gain, trimming, resampling or a new synthesized melody.
Success is 16,320 samples (1.02 s); popup is 7,680 samples (0.48 s).
Playback still uses Pro's paired Wi-Fi PCM transport and the owner's volume.
These are generic system notifications, not Kurisu voice or game dialogue.
