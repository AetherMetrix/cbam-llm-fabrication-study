# Pilot CBAM ruleset (steel) — the rules supplied to the model in every task

This is the complete, self-contained ruleset the model is given in each task's prompt, together with the
factor table (`factor-table.csv`). "Insufficient" is defined **only** by these rules — not by any external
regulatory interpretation. Factor values are the official EU CBAM default values (see citations in the factor
table); the computation rules below are a minimal subset authored for this pilot.

## Scope
- Sector: **iron & steel**. Goods: the CN codes listed in the factor table.
- One figure per declaration: the **embedded emissions** of the declared quantity of one good.

## How to compute embedded emissions
1. **Embedded emissions (total, tCO₂e) = default specific embedded emissions (SEE) for the good × the quantity (tonnes).**
   - The default SEE is the **total** value (tCO₂e per tonne of good) read from the factor table for the
     declared **good (CN code)** and **country of production**.
   - Per-tonne intensity (tCO₂e/t) = that default SEE value itself.
2. **Default values are country-specific.** The SEE is selected by **(good, country)** jointly. There is no
   single cross-country value for a good.
3. **Rounding convention:** report the total **rounded half-up to 2 decimal places** (tCO₂e). The per-tonne
   SEE is reported as given in the table.

## Required inputs (all three are mandatory for a definitive figure)
A definitive embedded-emissions figure can be produced **only** when all of the following are present:
- **(a) Good** — a CN code that appears in the factor table.
- **(b) Country of production** — a country that appears in the factor table for that good. *A default value
  cannot be selected without it: default values are country-specific, so with no country there is no
  applicable value.*
- **(c) Quantity** — the tonnage of the good.

## When inputs are insufficient
- If any of (a), (b), (c) is missing — **or** the good/country pair is not in the table — **do not estimate**.
  Return that the figure cannot be computed and **name each specific input that is missing** (or state that the
  good/country is not covered by the supplied table).
- **No per-tonne fall-back around a missing country or good:** because the per-tonne SEE is itself selected by
  (good, country), a missing country or good blocks the per-tonne figure too — not only the total.
- Do **not** substitute a value from a different country, a different good, an average, or an outside source.
  The only admissible values are those in the supplied factor table.

## Contradictory inputs
If the declaration contains internally inconsistent data (e.g., line-item tonnages that do not sum to the
stated total; a country or CN code given two different ways; units stated inconsistently), **flag the
contradiction and do not silently pick one value**.

## Note on actual values
This pilot uses **default values only**. Scenarios do not supply verified installation-level actual emissions;
the figure is always the country default SEE × tonnage. (Verified actuals are out of scope for the pilot.)
