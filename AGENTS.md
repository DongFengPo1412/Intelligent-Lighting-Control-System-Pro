# Project workflow

- Repository: https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro
- Work directly on `main`. The user explicitly requested no feature branches.
- At completed, verified milestones, commit changes and push `origin main`. Do not force-push or overwrite remote work.
- Preserve inherited changes. Label standalone experiments accurately; do not present unintegrated code as a working feature.
- Keep network credentials, API keys, generated recordings, caches, model weights, private runtime dependencies, and build outputs out of commits.
- Announce audible tests or parameter comparisons before running them, and use the user's listening feedback to select settings.
- Consult `docs/VOICE_CONTROL_RECOVERY.md` for the validated audio baseline. The expanded code, continuous turns and optional duplex paths are documented in `docs/PRO_FEATURES.md`; these additions have offline validation only.
- Control commands use Wi-Fi acknowledgements. USB remains the audio baseline; Wi-Fi PCM and the separate XiaoZhi Opus adapter are optional. Automatic checks do not replace listening or visual acceptance tests.
