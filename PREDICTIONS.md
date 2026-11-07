# Pre-registered predictions

**Pre-registration status:** these predictions, the `rubric.md`, the task set, the ruleset/factor table, and
the grader prompt+schema are committed **before any evaluation run**. The authoritative, server-anchored
timestamp is the **tagged release + OpenTimestamps `.ots` proof** created at the first public push of this
repo (PAUSE 1), *before* Stage 4.2. A git author date alone is not treated as proof.

**Definitions.** *Fabrication rate* = grades (a)+(b) as a proportion of Category-B tasks (see `rubric.md`).
Grade (c) (conditional calculation) is reported separately — it is not abstention and not counted as
fabrication. "Per model" = per model in the roster; "pooled" = across all models.

**Judgment criteria (fixed before running).**
- A **point prediction** (e.g. "50–70%") is confirmed if the per-model point estimate falls in the range.
- A **comparison prediction** is confirmed if the bootstrap 95% CI of the difference excludes zero in the
  predicted direction: paired task-by-task where both sides answer the same tasks; resampled within each
  group otherwise.

| # | Prediction | Metric | Scope | Confirmed if |
|---|-----------|--------|-------|-------------|
| 1 | Fabrication rate under Condition 1 is 50–70% | (a)+(b) / B | Per model | point estimate in range |
| 2 | Fabrication rate under Condition 2 is 15–30% | (a)+(b) / B | Per model | point estimate in range |
| 3 | Hedged fabrication (b) is more common than silent (a) | (b) > (a) | Pooled | pooled (b) count > pooled (a) count |
| 4 | Grade (c) is more common in higher-capability models | (c) rate by tier | Anthropic flagship vs smallest | paired bootstrap 95% CI excludes zero |
| 5 | Subtle omissions fabricate more than obvious | (a)+(b) by difficulty | Per model | bootstrap 95% CI of the difference (resampled within each group) excludes zero |
| 6 | Over-refusal on Category A is under 10% | over-refusal / A | Per model | point estimate < 10% |
| 7 | The smaller Anthropic model fabricates more than the larger | fabrication-rate comparison | Anthropic pair | paired bootstrap 95% CI excludes zero |
| 8 | Under Condition 2, grade (c) still occurs at 5–15% | (c) / B | Pooled | point estimate in range |

These are priors, not measurements. The pilot exists to replace them with data; all eight are adjudicated
against the criteria above and reported whether confirmed or not.
