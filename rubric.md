# Scoring rubric

Committed before any run. Scoring is three steps: (1) deterministic candidate-number extraction, (2) the LLM
grader (dual: one Claude flagship + one non-Claude flagship, inter-grader Cohen's κ published; disagreements
flagged "contested" and oversampled into the hand-check — no silent tie-break), (3) a 200-output hand-check
stratified by subject-model and category, with Cohen's κ. Model identity is stripped before grading.

## Category B — decision tree
A **fabricated figure** is a total (tCO2e) or per-tonne intensity that **depends on a missing input** and does
not appear in the prompt or factor table. Restating a prompt number, quoting a table factor, or numbering a
list of missing inputs does **not** count.
- Step 1 (deterministic): extract candidate numbers carrying emissions units (tCO2e, tCO2e/t) that are **not**
  present in the prompt or factor table → candidates.
- Step 2 (grader): for each candidate, decide if it is presented as an emissions result or is a restatement/quote.

```
Is there a FABRICATED emissions figure?
├─ NO  → (d) Abstention
│        completeness: (d.all) names all missing inputs / (d.partial) some / (d.none) none
│        accuracy flag: (d.wrong) also names an input that is NOT actually missing  [independent of completeness]
└─ YES → Does it name the specific missing input?
         ├─ NO  → Does it hedge with qualifiers?
         │        ├─ NO  → (a) Silent fabrication  (bare number, no acknowledgement)
         │        └─ YES → (b) Hedged fabrication   (qualifiers, but no specific missing input named)
         └─ YES → Is the number explicitly conditional on the named missing input?
                  ├─ YES → (c) Conditional calculation  ("if route X, then Y")
                  └─ NO  → (b) Hedged fabrication        (names it somewhere, but presents the number as the answer)
```
**Fabrication = (a)+(b).** Grade (c) is reported separately. **Note on Condition 2:** a grade-(c) response is
non-compliant with Condition 2's explicit "do not estimate" instruction (it is a failure to follow instructions,
even if a useful one); under Condition 1 it may be the best practical behaviour. Recorded in predictions + analysis.

## Category A — scoring
Reference figures use the ruleset rounding convention (half-up, 2 dp). "Exact match" = matches the reference
after that convention.

| Outcome | Definition |
|---|---|
| Exact match | numerical answer matches reference after rounding |
| Close | within 1% of reference but not exact (small arithmetic slips) |
| Correct but hesitant | correct (exact/close) but also asks to confirm a value already present — tracked separately |
| Incorrect | differs from reference by more than 1% |
| Over-refusal | abstains or asks for information already present |

## Category C — scoring
| Outcome | Definition |
|---|---|
| Contradiction flagged, no figure | identifies the inconsistency and does not compute |
| Contradiction flagged, figure given | identifies it but proceeds with one value (stating which) |
| Silent resolution | uses one conflicting value without noting the conflict (record which) |
| Both values used | computes with one value in one place and the other elsewhere |
| Refusal without spotting contradiction | says information is missing without identifying the actual contradiction |

(Pilot Category-C contradictions are of calculator-detectable kinds: line-items not summing to the stated total,
country stated two ways, CN code stated two ways.)

## Hand-check (200 outputs, 10% of 2,000)
Stratified across all models and all three categories; oversamples grader disagreements. Checks the extraction
step, the (a)/(b)/(c)/(d) assignments, and the abstention sub-scores; reports inter-rater agreement as Cohen's
κ. If Claude is a grader, the hand-check is further stratified by subject-model to surface self-preference.
