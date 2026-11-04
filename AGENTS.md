# Project workflow

- Repository: https://github.com/DongFengPo1412/Intelligent-Lighting-Control-System-Pro
- Continue on `arcade-100-audit-and-elevation` for the current arcade repair work (owner instruction, 2026-11-04). Inspect and preserve the current branch and inherited changes before editing. Do not switch to, overwrite, or merge into `main`.
- At completed, verified milestones, commit changes on the development branch. Push only that branch after checking the remote; never force-push or overwrite remote work.
- Preserve inherited changes. Label standalone experiments accurately; do not present unintegrated code as a working feature.
- Keep network credentials, API keys, generated recordings, caches, model weights, private runtime dependencies, and build outputs out of commits.
- Announce audible tests or parameter comparisons before running them, and use the user's listening feedback to select settings.
- Consult `docs/VOICE_CONTROL_RECOVERY.md` for the validated audio baseline. The expanded code, continuous turns and optional duplex paths are documented in `docs/PRO_FEATURES.md`; these additions have offline validation and limited board transport/audio-sample records in `docs/hardware-checks-20261023.en.md`, not full-system acceptance.
- Control commands use Wi-Fi acknowledgements. USB remains the audio baseline; Wi-Fi PCM and the separate XiaoZhi Opus adapter are optional. Automatic checks do not replace listening or visual acceptance tests.
