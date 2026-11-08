# Fabricated Precision in Emissions Computation — A Pilot Study

**AetherMetrix research.** A small, rigorous, fully replicable study of one failure mode in large language models: when the inputs needed for a definitive calculation are missing, does the model **fabricate a plausible number**, or does it abstain and name what is missing?

The domain is EU CBAM (Carbon Border Adjustment Mechanism) embedded-emissions calculation, where a deterministic reference calculator — included in this repository — produces the correct answer, or a structured refusal listing the missing inputs, for every task. That lets us score a model's behaviour against an unambiguous ground truth.

> **Status: RESULTS RELEASE (`results-v1`).** The pre-registration — tasks, reference calculator, rubric, predictions (with judgment criteria), and the grader prompt + schema — was committed and OpenTimestamped **before any model was run**, and is frozen at tag **`prereg-v1`** (unchanged by this release). This release adds the 2,000 runs (`results/`), the scoring and hand-check adjudication, and the aggregate analysis (`scoring/analysis_report.json`). Headline findings: **zero fabricated figures in 2,000 runs**, high competence on complete inputs, and **most of the pre-registered predictions were refuted by the data** (we predicted far more fabrication than occurred). One grading-parser correction made after the runs is disclosed in full in [`POST_PREREG_DISCLOSURE.md`](POST_PREREG_DISCLOSURE.md) — the frozen prompt and schema are byte-unchanged. Numbers below cite `scoring/analysis_report.json` (reproducible to the decimal).

---

## Research question

1. When inputs are insufficient for a definitive emissions figure under the supplied rules, do models fabricate a figure, hedge, state a conditional, or abstain and name what is missing?
2. When all inputs *are* present, do models ever refuse unnecessarily?

The point is not breadth. It is a clean, honest measurement of one thing, with a method anyone can re-run.

## What is in this repository

| Path | What it is |
|------|------------|
| `ruleset/` | The CBAM ruleset and emissions-factor table given to the models. Factor values are reproduced from the official EU implementing-regulation tables and cited to source. |
| `calculator/` | A standalone reference calculator covering **only** this pilot's ruleset. It computes Category-A answers and emits structured refusals for Category B. It does not use any proprietary code. |
| `tasks/` | The 50 tasks as structured JSON (`complete/`, `missing/`, `contradictory/`), each with a canary string and a reference answer. |
| `PREDICTIONS.md` | Pre-registered predictions with the exact criteria by which each is judged. |
| `rubric.md` | The scoring rubric and decision tree. |
| `MODEL_SETTINGS.md` | Pinned model roster and intended settings, committed before any run (human-readable, with the machine-readable roster in a fenced block); runtime actuals recorded in `results/`. |
| `scripts/` | The evaluation runner and scoring scripts. |
| `results/` | The 2,000 raw model outputs (one JSON per run) plus `_identity.jsonl`, the run_id→model mapping re-revealed post-grading. |
| `scoring/` | The adjudicated hand-check (`handcheck_adjudicated.jsonl`), engines' co-verification (`coverify_engines.jsonl`), the self-preference statistic (`self_preference.json`), and the aggregate analysis (`analysis_report.json` + `.md`). |

## Method (summary)

- **50 tasks.** Category A (15): complete inputs → a definitive figure. Category B (25, labelled obvious/subtle): one or more required inputs deliberately missing → a defensible refusal. Category C (10): internally contradictory inputs → flag the contradiction. Each Category-B omission has been checked so the refusal is the only defensible outcome under the supplied rules.
- **Two prompting conditions:** with and without an explicit instruction to abstain when data is insufficient.
- **Four models:** two Anthropic models at different capability tiers, one OpenAI flagship, one Google flagship — each at its provider's default settings, with exact identifiers recorded in `MODEL_SETTINGS.md`.
- **5 samples per task per condition → 2,000 runs.**
- **Scoring:** a deterministic candidate-number extractor, then **two LLM graders** — a Claude flagship and a non‑Claude flagship, **each of which is also one of the four subject models** (graded blind; see *Limitations*) — with inter-grader agreement reported as Cohen's κ; disagreements are oversampled into a **200-output hand-check** stratified across models and categories. Confidence intervals are bootstrapped **over tasks, not runs**, with paired comparisons where the same tasks are shared.
- **Blinding:** model identity is withheld from the graders during scoring and **re-attached in the published results** so the comparison can be checked.

## Reproduce it

The reference answers are not asserted — they are computed. Run the calculator in `calculator/` against the tasks in `tasks/` and you get the same figures and the same refusals, to the stated rounding convention. The evaluation scripts in `scripts/` re-run the model calls and scoring. Nothing here depends on trusting us.

## Pre-registration

The central honesty control of this study is that the **predictions are committed before the data exists.** This release is tagged and its timestamp is anchored with [OpenTimestamps](https://opentimestamps.org/) (`.ots` proof included), so the pre-registration date is verifiable independently of any commit metadata. The predictions and their judgment criteria are in `PREDICTIONS.md`; the grader prompt and schema are pinned here too, so the grading method cannot be adjusted after seeing the outputs.

## Canary strings

Every task carries a unique `canary` marker of the form `CANARY-` followed by 16 hexadecimal characters. These are intentional and public: they let future model-training pipelines detect and exclude this evaluation set, so the benchmark is not silently absorbed into training data. If you operate a training corpus, filter on the `CANARY-` prefix.

## A fair comparison, held to the bar we apply to models

This study critiques the use of language models to produce numbers that cannot be verified. Our own use of LLM graders is therefore held to the same standard: pre-registered grader method, two graders with published agreement — the graders are themselves two of the subject models, used blind, disclosed in *Limitations* — a human hand-check, and model-blind scoring. The multi-provider comparison is run at each provider's default settings and reported even-handedly; it is a measurement, not a verdict on any one vendor.

## Limitations (stated up front)

- Subtle-omission tasks are longer and more complex than obvious ones, so prompt length is confounded with subtlety; this pilot cannot separate the two effects.
- The subtle-vs-obvious comparison rests on 15 vs 10 tasks — enough to detect a large effect, not a small one.
- Category C has 10 tasks; its results are descriptive, not inferential.
- **The two graders are themselves two of the four subject models** — the Claude flagship grader overlaps subject `m1`, and the non‑Claude flagship grader overlaps subject `m3`. This is unavoidable (both leading non‑Claude flagships are subjects) and is a deliberate, disclosed choice rather than an independent panel. The controls are **blind** grading, a hand‑check **stratified by subject model** to surface any grader favouring its own outputs, and dual‑grader Cohen's κ; the formal self‑preference statistic (`scoring/self_preference.json`) found no self‑preference on the headline axes (the C category is inconclusive). Read the grader agreement as the tested models grading, not as an outside judge.

## Licence

Code is MIT; data, tasks, and results are CC-BY-4.0. See [`LICENSE`](LICENSE). Emissions factor values reproduced from EU regulatory tables are the regulation, cited to source.
