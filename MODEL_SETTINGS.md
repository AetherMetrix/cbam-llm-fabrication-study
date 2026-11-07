# MODEL_SETTINGS — pinned roster + intended settings (pre-registered)

**Pre-registration artifact.** This file fixes *which* models the pilot evaluates and *which intended
configuration* they are called under, committed **before any evaluation run**. The experimental design is
frozen here; the authoritative server-anchored timestamp is the tagged release + OpenTimestamps `.ots` proof
created at the first public push (`prereg-v1`). Runtime **actuals** (the settings each API actually echoes,
model/API versions, token usage, `stop_reason`) are recorded per run in `results/` and any divergence from the
intended settings below is reported — intended is pinned here, actual is captured at run time.

Blessed by the operator in message 02910 (roster + `max_output_tokens = 4096` + grader overlap disclosed +
filename frozen at `MODEL_SETTINGS.md`).

## Subject roster (the four models under test)

| Slot | Role | Model | API model id | Provider |
|------|------|-------|--------------|----------|
| `m1` | Anthropic flagship | Claude Opus 5.5 | `claude-opus-5-5` | anthropic |
| `m2` | Anthropic smallest | Claude Haiku 5.5 | `claude-haiku-5-5` | anthropic |
| `m3` | OpenAI flagship | GPT‑6 Astra | `gpt-6-astra` | openai |
| `m4` | Google flagship | Gemini 4 Argon | `gemini-4-argon` | google |

Roster keys (`m1`…`m4`) are opaque so downstream code cannot infer a model from the key. The `roles` block
names which key is the Anthropic flagship vs smallest — the capability pair tested by predictions 4 and 7.

**Anthropic flagship = Opus 5.5, not Fable 5.1:** Fable 5.1 is more capable but has non‑default API behaviour
(thinking always‑on) that would break the "each model at its provider default" premise; Opus 5.5 is the clean
flagship for a default‑settings pilot.

## Intended settings (each model at its provider default)

- **temperature:** provider default — the harness does not override it (recorded as `"default"`; the runtime
  actual is captured from each response).
- **reasoning / thinking mode:** provider default.
- **max_output_tokens: 4096**, uniform across all four models. Raised from 2048 deliberately: a truncated
  response on an extended‑reasoning model could be cut off *before its answer*, which would be mis‑scored as
  abstention/incorrect and contaminate the fabrication measurement. Any run that still hits the cap is recorded
  via `stop_reason` in `results/` and reported, never silently scored.

## Graders (dual; pre-registered choice)

- `grader_a = claude-opus-5-5` (Claude flagship) · `grader_b = gpt-6-astra` (non‑Claude flagship).
- `grader_b` coincides with subject `m3`: because both leading non‑Claude flagships are subjects, a non‑Claude
  flagship grader necessarily overlaps one subject. Controls are the designed ones — **blinded** grading, the
  200‑output hand‑check **stratified by subject‑model** to surface self‑preference (symmetric to `grader_a`
  overlapping `m1`), and dual‑grader Cohen's κ. **This overlap is disclosed in the README limitations.**
- The runtime grader configuration lives in `grader/GRADER_SETTINGS.json` (copied from the committed
  `GRADER_SETTINGS.example.json` and keyed at grading time); the block below is the pre‑registered record.

## Exact model IDs — pinned now, validated at Stage 4.1

The competitor IDs (`gpt-6-astra`, `gemini-4-argon`) are pinned here from each provider's current documentation.
They are **not** verified by a live endpoint call before the push — the pre‑registration stays key‑free. The
Stage‑4.1 smoke (the first keyed call, after the push) **fail‑loud‑validates each exact ID** and records the
runtime actuals. Anthropic IDs are per the Claude 5 family.

## Machine-readable block

`providers.load_settings_md` reads the single fenced JSON block below (`run_eval.py` → `model_ids` +
`intended_settings.max_output_tokens`; `analyse.py` → `roles`). This is the one canonical, machine‑parseable
copy — the prose above describes it, this block is authoritative.

```json
{
  "model_ids": {
    "m1": "claude-opus-5-5",
    "m2": "claude-haiku-5-5",
    "m3": "gpt-6-astra",
    "m4": "gemini-4-argon"
  },
  "roles": {
    "anthropic_flagship": "m1",
    "anthropic_smallest": "m2"
  },
  "intended_settings": {
    "temperature": "default",
    "reasoning_mode": "default",
    "max_output_tokens": 4096
  },
  "graders": {
    "grader_a": "claude-opus-5-5",
    "grader_b": "gpt-6-astra"
  },
  "id_validation": "pinned from provider docs; fail-loud-validated at Stage 4.1 (first keyed call, after push)"
}
```
