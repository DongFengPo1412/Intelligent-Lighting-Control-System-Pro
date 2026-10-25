# Local music library

Chinese homophones are matched against the catalog. Larger pronunciation differences require a strong, clearly separated artist/title match; otherwise the user chooses a candidate. Frequent artists provide spelling hints only after waking. This does not establish unrestricted accent/foreign-title recognition. Music alone defaults to linear gain `0.25` (about −12 dB), selected through the user's listening comparison; MIR analysis and speech gain retain their original signals. Override with `KURISU_MUSIC_GAIN` in `(0,1]` and restart.

[简体中文](LOCAL_MUSIC.md) · [日本語](LOCAL_MUSIC.ja.md) · [Pro guide](PRO_FEATURES.en.md)

The PC reads the original files, decodes the selected song to 16 kHz mono PCM, and sends it to the board speaker over the existing Wi-Fi PCM or USB path. FFT bands, RMS and onsets from the same PCM drive the halo or 16-column spectrum. No SD-card hardware is required; keep the PC running and connected to the board's network.

Open `/pro.html#musicLibrary`, enter an absolute folder path and save/scan. Search titles and artists, then play a result. The current search result defines the queue; clear the search to use the full catalog. Previous/next, stop, sequential/shuffle and off/list/single repeat are available. The progress indicator is read-only; seeking and resume-from-position are not implemented.

Embedded title/artist tags take priority over filenames. Source files are not moved or batch-converted. Only the selected song is decoded. Local playback bypasses the 20 MiB upload limit but retains a 30-minute duration limit and 16 kHz mono output. SoundFile handles available formats; existing PyAV supplies a fallback, whose codec support depends on the installed environment. Not every file/codec has been individually validated.

With the complete voice service, wake first and request a song in Chinese, for example `播放周杰伦的七里香`, an artist collection with `播放艾伦沃克的歌`, or `下一首`, `上一首`, `停止音乐`, `随机播放`, `顺序播放`, `单曲循环`, `列表循环`, `取消循环`. Ambiguous matches require clarification or a numbered selection such as `播放第2首`. This uses bounded request patterns and catalog matching, not unrestricted language understanding. Pause requests currently stop playback; a later request starts from the beginning. Text chat uses the same router. Playback itself confirms a song request, avoiding overlapping TTS.

During Wi-Fi music, the complete voice service can monitor the wake word. Acoustic KWS and unprompted ASR must both confirm it before cancelling the song and accepting the next command. Lyrics do not directly enter normal command transcription. Reference-audio processing is not a claim of mature acoustic AEC; false/missed wakes still require listening tests across songs, distances and levels. Disable with `KURISU_MUSIC_WAKE=0`; USB playback does not enable this monitor. `--no-audio` disables automatic voice/TTS but retains web music playback.

`KURISU_MUSIC_DIR` optionally overrides the saved folder. The saved folder is in `KURISU_DATA_DIR/music-library.json`; tag cache is in `KURISU_CACHE_DIR/music-library-tags.json`, checked against size and modification time. Personal music paths, songs, generated audio and runtime files do not belong in Git.

API:

- `GET /api/pro/library?q=...&offset=0&limit=30`: paginated catalog, maximum 100 entries per page.
- `POST /api/pro/library`: `{"action":"configure","root":"absolute path"}` or `{"action":"scan"}`.
- `POST /api/pro/music`: `{"track_id":"catalog ID","visual":"fluid","scope":"query"}`; optional `single:true`. A `query` field instead resolves a song request and explains ambiguity.
- Music actions: `next`, `previous`, `stop`, or `options` with `order:sequential|shuffle` and `repeat:off|one|all`. Existing upload/direct-URL paths remain; selecting them detaches the library queue.
- `GET /api/pro/status`: current track, queue position, duration/progress, errors, library status, dispatch statistics and `voice_wake`.

Only catalog IDs resolve to local files, with a containment check on playback. Missing files, failed decoding and unacknowledged commands are not reported as successful playback. Stop/switch invalidates the prior automatic queue continuation.

Offline tests: `tests/test_music_library.py`, `tests/test_music_follow.py`, `scripts/test_interaction_regressions.py`. Use a task cache for fixtures/logs. Physical acceptance is separate; see [board records](hardware-checks-20261023.en.md).
