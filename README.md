# Fabricated Precision in Emissions Computation — A Pilot Study

**AetherMetrix research.** A small, rigorous, fully replicable study of one failure mode in large language models: when the inputs needed for a definitive calculation are missing, does the model **fabricate a plausible number**, or does it abstain and name what is missing?

The domain is EU CBAM (Carbon Border Adjustment Mechanism) embedded-emissions calculation, where a deterministic reference calculator — included in this repository — produces the correct answer, or a structured refusal listing the missing inputs, for every task. That lets us score a model's behaviour against an unambiguous ground truth.

**Conflict of interest.** The author is the founder of AetherMetrix, which sells CBAM compliance software built on the premise that a regulated figure should be computed by a deterministic engine, not produced by a language model. This pilot tests that premise directly. It is pre-registered, and the full method, data, and scoring code are published so the result can be checked rather than taken on trust — including where the evidence runs against the product's framing (see *Limitations* and the headline findings).

> **Status: RESULTS RELEASE (`results-v2`).** The pre-registration — tasks, reference calculator, rubric, predictions (with judgment criteria), and the grader prompt + schema — was committed and OpenTimestamped **before any model was run**, and is frozen at tag **`prereg-v1`** (unchanged by this release). This release adds the 2,000 runs (`results/`), the scoring and human hand-check adjudication, and the aggregate analysis (`scoring/analysis_report.json`). Headline findings: **zero fabrications observed across 2,000 runs** (reported as a low upper bound, not a proven zero), **100% correct on complete inputs**, and a pre-registered scorecard of **1 confirmed / 4 refuted / 3 untestable** — we predicted far more fabrication than occurred. On contradictory inputs the plurality response was a transparent *computed-it-both-ways* answer (52%). Every deviation and post-hoc decision is disclosed in full in [`POST_PREREG_DISCLOSURE.md`](POST_PREREG_DISCLOSURE.md) — the frozen prompt and schema are byte-unchanged. See **Results** below (all numbers cite `scoring/analysis_report.json`, reproducible to the decimal).

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
- **Scoring:** a deterministic candidate-number extractor, then **two LLM graders** — a Claude flagship and a non‑Claude flagship, **each of which is also one of the four subject models** (graded blind; see *Limitations*) — with inter-grader agreement reported as Cohen's κ; disagreements are oversampled into a **225-output human hand-check** — a stratified sample across models and categories, plus all 87 contested cases and the two fabrication candidates. Confidence intervals are bootstrapped **over tasks, not runs**, with paired comparisons where the same tasks are shared.
- **Blinding:** model identity is withheld from the graders during scoring and **re-attached in the published results** so the comparison can be checked.

## Results

Headline numbers, so a reader does not have to open the JSON. All figures cite `scoring/analysis_report.json` (regenerate with `scripts/analyse.py`; the per-model and boundary figures with `scripts/review_stats.py`). Each rate carries a **task-level bootstrap 95% CI** (resampled over tasks, not runs); the one boundary cell uses an exact interval, noted inline. Scored set **N = 1,971**.

**Category A — complete inputs** (15 tasks, 583 scored runs). Correct figure **100%** [100, 100]; over-refusal — balking at a solvable task — **0%**. Every model, every scored sample.

**Category B — missing inputs** (25 tasks, 988 scored runs). The defensible outcomes are a clean abstention that names the missing input, or a conditional calculation stating the figure contingent on it and flagging the gap:
- clean abstention — **92.1%** [89.5, 94.4]
- conditional, gap named — **7.9%** [5.5, 10.4]
- **fabrication — 0 observed.** An observed zero is reported as an upper bound, not [0, 0]: a 95% upper bound of **≈ 12% at the task level** (25 tasks) and ≈ 0.3% at the run level (988 runs, assuming sample independence). Where models abstained, **100%** named every missing input (910/910).

**Category C — contradictory inputs** (10 tasks, 400 runs — full coverage after the human hand-score). The one family where behaviour is model-dependent:
- compute both values and present both, transparently — **52.0%** [48.0, 55.5] *(the plurality)*
- flag the contradiction, no figure — **43.8%** [38.0, 49.2]
- flag it, yet still attach one figure — **4.2%** (exact Clopper–Pearson 95% [2.5, 6.7]); all 17 of these come from one model (GPT-6 Astra)
- silent resolution / refusal without spotting — **0 / 0**

Per model (n = 100 each): Claude Opus 5.5 — 65% both-ways / 35% flag · Claude Haiku 5.5 — 70% / 30% · GPT-6 Astra — 57% flag / 26% both / 17% flag-with-figure · Gemini 4 Argon — 53% flag / 47% both.

**Grader agreement (Cohen's κ, by family).** Computable **1.00**, missing-input **0.99**, contradictory **0.46**. The low contradictory κ sits entirely at the `both_values_used` rubric boundary — the pre-registration defines "both values used" as *inconsistent* use, and a transparent "computed both ways" answer has no clean label — so read it as LLM-as-judge / rubric-specification reliability, not model capability. (Details in *Limitations* and [`POST_PREREG_DISCLOSURE.md`](POST_PREREG_DISCLOSURE.md).)

**Pre-registered predictions — 1 confirmed / 4 refuted / 3 untestable** (full criteria in [`PREDICTIONS.md`](PREDICTIONS.md); *untestable* marks a comparison whose two fabrication rates were both zero, leaving no events to compare):

| # | Pre-registered prediction | Outcome |
|---|---------------------------|---------|
| 1 | Fabrication rate (grades a+b / B) is 50–70% under the neutral prompt | **Refuted** — 0 observed |
| 2 | Fabrication rate is 15–30% under the abstention-permitting prompt | **Refuted** — 0 observed |
| 3 | Hedged fabrication (b) is more common than silent fabrication (a) | **Untestable** — both 0 |
| 4 | Conditional answers (grade c) are more common in the higher-capability Anthropic model | **Refuted** — ran opposite (the smaller model gave more) |
| 5 | Subtle omissions fabricate more than obvious ones | **Untestable** — fabrication 0 in both |
| 6 | Over-refusal on complete-input tasks is under 10% per model | **Confirmed** — 0% |
| 7 | The smaller Anthropic model fabricates more than the larger | **Untestable** — fabrication 0 in both |
| 8 | Conditional answers (grade c) still occur at 5–15% under the abstention-permitting prompt | **Refuted** — 2.6%, below the range |

**The excluded runs did not hide fabrication.** The two LLM graders left 26.5% of contradictory runs unscoreable — grader-verdict incompleteness (86 of the 106 had a missing grader rationale), not failed model outputs — so a human scored all 106 directly from the raw outputs. Re-including them introduces **no fabrication and no silent resolution (0 of 106)**; because the excluded set was overwhelmingly transparent dual-computations, the earlier 294-run framing under-counted "both values used" by ~15 points (37.4% → 52.0%). The zero-fabrication finding is unchanged.

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
- **The two graders are themselves two of the four subject models** — the Claude flagship grader overlaps subject `m1`, and the non‑Claude flagship grader overlaps subject `m3`. This is unavoidable (both leading non‑Claude flagships are subjects) and is a deliberate, disclosed choice rather than an independent panel. The controls are **blind** grading, a hand‑check **stratified by subject model** to surface any grader favouring its own outputs, and dual‑grader Cohen's κ. The formal self‑preference statistic (`scoring/self_preference.json`) is reported per axis rather than as a flat null: **no self‑preference on competence** (the computable and abstention rates); on **fabrication it is underpowered** — the whole study produced only two fabrication flags, both on a *competitor's* output, which cannot establish a preference either way; and on the low‑agreement **contradictory category it is inconclusive** (the modest own‑model effect there cannot be separated from the graders' large general disagreement). Blinding is label‑blinding, not style‑blinding, so self‑preference is *bounded* by this statistic, not eliminated. Read the grader agreement as the tested models grading, not as an outside judge.

## Licence

Code is MIT; data, tasks, and results are CC-BY-4.0. See [`LICENSE`](LICENSE). Emissions factor values reproduced from EU regulatory tables are the regulation, cited to source.
