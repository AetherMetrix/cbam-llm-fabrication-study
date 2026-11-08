# Publish manifest + push procedure (frontend-owned)

This file is the auditable record of **what goes into the public repo** and **how the first push is made**. It ships in the repo (like `leak-scan.sh`) to show the publishing process; `publish/` is excluded from the belt's own scan (it holds detection patterns + procedure, no secrets). The published set MUST equal the belt's scanned set + the pinned `MODEL_SETTINGS` (below).

Target repo: **`AetherMetrix/cbam-llm-fabrication-study`** (public). First push = the server-timestamped **pre-registration release**.

## Public set (the frozen pre-registration bundle)
- `README.md` — pre-registration README (company-research framing, application framing stripped)
- `LICENSE` — MIT (code) / CC-BY-4.0 (data, tasks, results)
- `PREDICTIONS.md` · `rubric.md` — pre-registered predictions + scoring rubric
- `MODEL_SETTINGS.md` — pinned roster + intended settings + `roles` block; human-readable pre-registration doc with the machine-readable roster in a fenced block (parsed by `providers.load_settings_md`, wired into `run_eval.py`/`analyse.py`) *(**pending**)*
- `HARNESS_IO.md` — the harness input/output contract (runner ↔ calculator/grader)
- `ruleset/` — ruleset + OJ-cited factor table
- `calculator/` — clean-room reference calculator
- `tasks/complete|missing|contradictory/` — the 50 tasks (canaries intended-public)
- `scripts/*.py` — eval runner + scoring (`run_eval`, `providers`, `blinding`, `extract_candidates`, `llm_grader`, `analyse`)
- `grader/` — dual-grader prompt + schema + settings **template**
- `publish/` — this file + `leak-scan.sh`
- *(added post-grading, phase 2: `results/`, `hand_check/`, `analysis/` — model identities re-revealed for replicability)*

## Internal — NEVER published
- `SPEC.md` — carries personal-application framing (boundary #4); **stays internal**. Pre-registration design is fully captured publicly by PREDICTIONS + rubric + ruleset + tasks + README, so the raw spec is not needed in the repo.
- `BUILD-STATUS.md`, `authoring/` — internal build log + task generators
- **`*.private.sh` (e.g. `publish/leak-scan.private.sh`) — the org-specific detection lists for the leak-scan belt (real collaborator names, internal topology specifics, proprietary symbols, internal process tokens). NEVER published** — gitignored, excluded from the staging allowlist, and excluded from the belt's own scan (`! -name '*.private.sh'`). The public `leak-scan.sh` sources it only on internal runs; a replicator runs the generic belts without it.
- **`writeup/` (whole folder — drafts, REVIEW-COPY.*, reviews/) — the article's work-in-progress draft + external reviews.** The article's canonical home is aethermetrix.com/articles; the repo links out. Created post-prereg and briefly swept into `results-v1` before it was excluded; removed from `main`, and the belt now excludes `writeup/` and flags internal process references so it cannot recur.
- `__pycache__/`, `*.pyc` — compiled artifacts
- **`.env*` (e.g. `.env.research`) — live API keys; NEVER published** (the belt excludes `.env*` and fail-closed-caught `.env.research` carrying a real `RESEARCH_ANTHROPIC_API_KEY` at the results-phase push).
- **populated `GRADER_SETTINGS.json` / `MODEL_SETTINGS.json`, `*.key`, `*.pem`** — only the `*.example.json` template is public; keys are read from `RESEARCH_<PROVIDER>_API_KEY` env vars and never committed. The belt excludes these by name.

## Push procedure — runs ONLY on the operator's explicit go
1. **Re-run the belt on the final assembled bundle** (`bash publish/leak-scan.sh`) — must be 0 findings. Gate 2 is "belt green on the *assembled* bundle," so this is the last scan, after `MODEL_SETTINGS` lands.
2. Stage the **public set** above into the repo working tree (internal files excluded exactly as the belt excludes them).
3. `git init` (or add remote) → `git remote add origin git@github.com:AetherMetrix/cbam-llm-fabrication-study.git` (operator's credential owns the org).
4. One clean commit = the pre-registration baseline. **Tag** it (`prereg-v1`).
5. **OpenTimestamps** the tagged commit (`ots stamp`), commit the `.ots` proof, so the pre-registration date is server-anchored independent of commit metadata.
6. `git push origin main --tags`. Verify the release + `.ots` are live.
- **No runs, no API keys** are involved in this push (that's PAUSE 2, later). This push publishes the design only.

## Resolved
- **`MODEL_SETTINGS` canonical = `MODEL_SETTINGS.md`** — a human-readable pre-registration doc carrying the roster/roles/intended-settings in a fenced json block, parsed by `providers.load_settings_md` and wired into `run_eval.py`/`analyse.py`. README + manifest references aligned. (A brief `.json` variant considered earlier was superseded.)
