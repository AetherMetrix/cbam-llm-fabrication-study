# Post-pre-registration disclosure

This document lists **every deviation and post-hoc decision** made after the pre-registration was frozen, so a
reader can see exactly where the executed study departed from, or went beyond, the committed plan.

The pre-registration — `PREDICTIONS.md`, `rubric.md`, the task set, the ruleset / factor table, and the grader
prompt + schema — was committed and server-timestamped (OpenTimestamps) as the `prereg-v1` tag **before any
evaluation run**. That snapshot is immutable. The items below are changes or additions relative to it; the
updated results are published under a separate `results-v2` tag, and `prereg-v1` / `results-v1` are left
byte-identical.

## 1. The two graders are also subjects (disclosed design choice)
Grading used two LLM judges — `grader_a` (Claude Opus 5.5) and `grader_b` (GPT-6 Astra) — which are **two of the
four models under test**, not an independent panel. This overlap was a deliberate, disclosed choice. We treated
self-preference as something to measure, not assume away: blind grading (model identity stripped before
grading), a hand-check stratified by subject model, and a formal self-preference statistic. Result: on the
competence and abstention axes neither grader favoured its own outputs; on fabrication the event count (two
flags in the whole study) is too low to assess self-preference either way; on the low-agreement contradictory
category the result is inconclusive. Blinding is identity-label blinding, not style blinding — a model may still
recognise its own prose — so self-preference is *bounded* by the measured statistic, not eliminated.

## 2. Hand-check oversampled disagreements (deviation from pure stratified sampling)
The pre-registration described a 200-output hand-check stratified by subject model and category. The executed
hand-check was **225 outputs**: the stratified sample **plus all 87 contested runs** (every run where the two
graders disagreed) **plus the 2 fabrication candidates**, force-included. Oversampling the disagreements is a
deviation from pure stratified sampling; it was done to put human attention exactly where the graders were least
reliable. All rates are reported on the agreed-plus-adjudicated set.

All human scoring — this 225-run hand-check and the 106 excluded-run adjudication (§8) — was done by a **single
rater (the author), blind to model identity**: the scoring tool withheld which model produced each output.
Single-rater scoring (no second independent human) is a limitation, noted alongside the conflict-of-interest
disclosed in the repository README.

## 3. Exclusion rule for incomplete grader verdicts
Of the 2,000 runs, **135 were excluded** from the reported rates (scored set **N = 1,865**): Category A 17,
Category B 12, Category C 106. A run was excluded when at least one grader failed to emit a **complete, valid
verdict** — overwhelmingly a missing rationale or a null label — which the validator rejects rather than
guesses at (the parser fails closed; it never coerces an ambiguous output into a label). These exclusions are
**grader-verdict incompleteness, not malformed model outputs**: of the 106 excluded contradictory runs, most
were incomplete on a single grader's verdict rather than on both. The unscoreable share rises with task
difficulty (2.8% / 1.2% / 26.5% for computable / missing-input / contradictory).

This N is **superseded by §8 for Category C**: after the 106 excluded contradictory runs were human-scored and
folded back in, the final scored set is **N = 1,971**. The 17 Category A and 12 Category B exclusions remain
excluded (those families were scored on 97%+ of their runs and were not re-adjudicated).

## 4. Per-cell interval methods at boundary cells (method addition)
The pre-registered estimation used a task-level bootstrap 95% CI, which degenerates on cells whose count sits at
a boundary (it returns a `[0–0]`-type interval that is an artifact of the method, not a finding). Two kinds of
boundary cell are handled by an exact method instead, and — this is the per-cell settlement — they are handled
**differently**, so the method is stated per cell rather than lumped together:

- **Observed-zero cells** — the zero-fabrication cell, and the two Category-C outcomes that never occurred
  (silent resolution, refusal without spotting) — are **not** given a two-sided interval, because a two-sided
  interval on a zero count is degenerate. The fabrication cell is reported with an explicit **one-sided 95%
  upper bound** (rule-of-three; equivalently the Clopper–Pearson one-sided upper limit): **≈12% at the task
  level** (25 missing-input tasks) and **≈0.3% at the run level** (988 runs); it assumes independence across
  samples. The two zero Category-C outcomes are reported as simply not observed (0/400); the same one-sided
  bound would apply if one were quoted.
- **The one near-zero, non-zero cell** — "contradiction flagged with a figure," 17/400 = 4.2% — uses a
  **two-sided exact Clopper–Pearson** 95% interval, **[2.5, 6.7]**. Like the run-level fabrication bound, this
  assumes independence **across samples — and here across models, since all 17 came from a single model**, so
  the true uncertainty is wider than the nominal interval.

So exactly **one** reported cell uses a two-sided exact Clopper–Pearson interval; the observed-zero cells use
one-sided upper bounds. All other rates keep the pre-registered task-level bootstrap. (The article's §setup line
and the README state the same per-cell split.)

## 5. Parser normalization fix (disclosed in the write-up)
An early scoring pass under-counted fabrication because the graders returned verdicts in three serializations
the parser did not fully anticipate, and one caused valid verdicts to be dropped silently. The fix changed
**only the parser** — the code that *reads* verdicts. The pre-registered grader prompt and schema are
**byte-for-byte unchanged**, and because the fix re-reads verdicts already on disk, **no model was called
again** (zero additional spend). Two fabrication verdicts that had been dropped were recovered, then adjudicated
— by an independent extraction check and a human reviewer — to be **not fabrications** (they were correct
refusals that quoted the factor table). We hand-checked the parser's coverage: 3,858 of 4,000 grader outputs
parsed to a valid verdict; the remaining 142 are incomplete verdicts, not unparsed formats (see §3).

## 6. Post-hoc, exploratory grader-reliability analysis (not pre-registered)
The analysis of inter-grader agreement by category — including the κ = 0.46 on the contradictory family — was
**not a pre-registered prediction**. It emerged post-hoc and is reported as **exploratory**. It is a finding
about **LLM-as-judge / model-graded-evaluation reliability**, not about scalable oversight in the sense of
overseeing models whose capability exceeds the overseers'. The κ = 0.46 disagreement is **concentrated entirely
at a single rubric label**: every one of the 86 contradictory-family disagreements is a split between
`both_values_used` and a `flagged` label, where a transparently-conditional answer fits neither pre-registered
definition cleanly. This is **consistent with rubric-boundary ambiguity and with grader miscalibration**, and
this pilot cannot fully separate the two — though the 100%-at-one-boundary pattern points to rubric
specification as the primary driver. It rests on 10 contradictory tasks.

## 7. Prediction scorecard: "untestable" distinguished from "refuted"
The scorecard is reported as **1 confirmed / 4 refuted / 3 untestable**. Three predictions (hedged vs. silent
fabrication; subtle vs. obvious fabrication; smaller vs. larger model fabrication) are **comparisons whose both
sides are the zero-fabrication cells** — with no events on either side they cannot be adjudicated, so each is
reported as **"not confirmed (untestable: zero fabrication events in both arms of the comparison)"** rather than
*refuted*. This is an application of the pre-registered binary rule — a comparison prediction is confirmed only
if its CI excludes zero in the predicted direction — not a softer third category invented after the fact. The
four refuted predictions each have a definite measured value that fell outside its range or ran opposite to the
predicted direction. This is a reporting refinement over an earlier "1 confirmed / 7 refuted" framing.

## 8. Re-inclusion of the 106 excluded contradictory runs (done)
The 106 excluded contradictory runs (§3) were human-scored against the five Category-C outcomes and folded back
in, giving **full coverage of all 400 contradictory runs**. The 106 resolved to **98 "both values used" and 8
"contradiction flagged, no figure" — and zero of any single-figure outcome** (no silent resolution, no
flag-with-a-figure). So the exclusion was **not masking a fabrication or a silently-resolved figure**; every
excluded run was a transparent conditional answer or a clean flag.

Folding them in shifts the Category-C picture because the excluded set was heavily "both values used": on the
full 400, **"both values used" is 52.0% (208/400)** and **"contradiction flagged, no figure" is 43.8%
(175/400)** — a reversal of their order on the scored subset (37.4% vs 56.8% on n = 294), while
"flagged with a figure" is 4.2% (17/400) and the two single-figure outcomes remain 0%. The honest direction of
the earlier exclusion was therefore that it **under-counted the transparent both-ways response** and
over-counted clean flagging — it did not flatter the models on anything safety-relevant. The zero-fabrication
result and the 1 confirmed / 4 refuted / 3 untestable scorecard are unchanged by the re-inclusion.

## 9. Post-hoc relabel of `both_values_used` (the one to look at hardest)
This is the single place a reader checking the pre-registration should scrutinise most, because it is the one
place the labelling of an outcome changed after the data came in. The results report the `both_values_used`
label as **transparent dual computation** — the model works the figure under each reading of the contradiction
and presents both — and it is the Category-C plurality, **52.0% (208/400)**. That reading **departs from the
label's pre-registered definition**, which was *inconsistent* use: one value used in one place and the other
elsewhere — a failure mode. Under the **strict pre-registered reading**, those 208 runs would be scored as a
failure outcome rather than as a transparent, deliberate response, and the Category-C picture would read very
differently.

We judge the transparent-dual-computation reading the **more accurate description of what the models actually
did** — the single human rater confirmed it on the hand-check, and the responses explicitly present both
computations rather than silently mixing them — but we flag the relabel plainly, rather than quietly adopting
it, so a reader sees **both readings** and can apply either. The article marks this at the first mention of the
52% with a parenthetical to the same effect. This relabel is also the most likely driver of the κ = 0.46
grader disagreement (§6): the pre-registered label scheme had no clean category for a transparent dual
computation, so two careful graders split on exactly these runs.
