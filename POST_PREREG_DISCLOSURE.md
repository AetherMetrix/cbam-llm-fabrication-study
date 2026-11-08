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

## 3. Exclusion rule for incomplete grader verdicts
Of the 2,000 runs, **135 were excluded** from the reported rates (scored set **N = 1,865**): Category A 17,
Category B 12, Category C 106. A run was excluded when at least one grader failed to emit a **complete, valid
verdict** — overwhelmingly a missing rationale or a null label — which the validator rejects rather than
guesses at (the parser fails closed; it never coerces an ambiguous output into a label). These exclusions are
**grader-verdict incompleteness, not malformed model outputs**: of the 106 excluded contradictory runs, most
were incomplete on a single grader's verdict rather than on both. The unscoreable share rises with task
difficulty (2.8% / 1.2% / 26.5% for computable / missing-input / contradictory).

## 4. Exact Clopper–Pearson intervals at boundary cells (method addition)
The pre-registered estimation used a task-level bootstrap 95% CI. For the two cells where a count sits at a
boundary — the observed-zero fabrication cell, and the near-zero "contradiction flagged with a figure" cell —
a task-level bootstrap degenerates (it returns a `[0–0]`-type interval that is an artifact of the method on
boundary counts, not a finding). Those two cells are instead reported with an **exact Clopper–Pearson**
interval, flagged where they appear. All other rates keep the pre-registered bootstrap.

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
sides are the zero-fabrication cells** — with no events on either side they cannot be adjudicated, so they are
reported as *untestable* rather than *refuted*. The four refuted predictions each have a definite measured
value that fell outside its range or ran opposite to the predicted direction. This is a reporting refinement
over an earlier "1 confirmed / 7 refuted" framing.

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
