# Grader self-preference — formal analysis (full consensus set)

Two of the four subject models were also the graders (`grader_a` = `m1` Claude-flagship; `grader_b` = `m3`
non-Claude-flagship), graded **blind**. This is the formal check — deferred from the hand-check to this
release — of whether either grader scored its **own** subject's outputs more favourably than other models'.
Computed on the **full run** (not the contested-C-enriched hand-check sample, where the signal was
confounded). Reproduce: `python scripts/self_preference.py` → `scoring/self_preference.json`.

## Result

**Fabrication axis (the study's headline metric): no self-preference.**
Neither grader flagged fabrication on its own subject. `grader_b`'s only two B-fabrication flags in the
entire study were **both on `m1` (a competitor), not on itself** — and both were adjudicated *not*
fabrications (correct refusals that quoted the factor table). If anything the direction is the opposite of
self-preference.

**Competence & abstention (Categories A, B): no self-preference.**
The two graders assign each model the same favourable-label rate regardless of which model is "own":

| model | B abstention-rate, grader_a | B abstention-rate, grader_b |
|---|---|---|
| m1 (Opus, grader_a's own) | 0.856 | 0.836 |
| m2 (Haiku) | 0.826 | 0.820 |
| m3 (GPT, grader_b's own) | 1.000 | 1.000 |
| m4 (Gemini) | 1.000 | 1.000 |

Because the **independent** grader sees the same per-model rate, the own-vs-others gaps are **model
behaviour** (Opus produces more conditional calculations; GPT and Gemini abstain tersely), not grader
favouritism. Category A is 100% exact for every model under both graders — no signal.

**Contradiction handling (Category C, low agreement κ = 0.46): inconclusive — reported, not dismissed.**
Here each grader does rate its **own** model's contradiction-handling somewhat more favourably
(`flagged_no_figure`: grader_a on m1 +0.13 vs others; grader_b relatively generous to m3). **But** this sits
inside the graders' large *general* disagreement on C — on m1, grader_a scores 0.84 and grader_b 0.36 — so a
modest own-favourable gap cannot be cleanly separated from C-grading noise on this data. C already rests on a
thinner base (294/400 usable dual-grades) and is held loosely throughout. We neither assert self-preference
here nor dismiss it; the raw per-model numbers are in `self_preference.json` for any reader to re-weigh.

## Bottom line
No self-preference where it would matter most — the fabrication and competence findings the study rests on.
A small, inconclusive own-favourable tendency in the single low-agreement category, disclosed rather than
smoothed over.
