#!/usr/bin/env python3
"""Clean-room reference calculator for the Fabricated Precision pilot (steel, CBAM default values).

Standalone: stdlib only; no import of any production code. It encodes ONLY the pilot ruleset
(`ruleset/ruleset.md`) over the supplied factor table (`ruleset/factor-table.csv`). It is the ground truth
for every task's reference answer and is published so that anyone can reproduce it.

Output contract (agreed engines<->api, msg 02894):
  {status: "computed"|"refused"|"contradiction",
   figure_tCO2e: float|None,
   per_tonne_tCO2e: float|None,
   missing_inputs: [{"id","label","why_required"}],
   contradiction_detail: str|None}
"""
from __future__ import annotations
import csv
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# Ruleset rounding convention: round half-UP to 2 dp (so ground truth matches straightforward
# hand-computation, not Python's default round-half-to-even).


def load_factor_table(path: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Map (cn_code, country) -> {direct, indirect, total, description}. total is the SEE used to compute."""
    table: dict[tuple[str, str], dict[str, Any]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cn = _norm_cn(row["cn_code"])
            country = row["country"].strip()
            table[(cn, country)] = {
                "description": row["good_description"].strip(),
                "direct": _f(row["direct_tCO2e_per_t"]),
                "indirect": _f(row["indirect_tCO2e_per_t"]),  # None => N/A (not separately defaulted)
                "total": _f(row["total_tCO2e_per_t"]),
            }
    return table


def _f(s: str) -> float | None:
    s = (s or "").strip()
    return float(s) if s else None


def _norm_cn(cn: str | None) -> str:
    """Normalise a CN code for comparison: digits only (drop spaces), so '7206 10 00' == '72061000'."""
    return "".join(ch for ch in str(cn or "") if ch.isdigit())


def _countries_for_good(table, cn_norm: str) -> list[str]:
    return sorted({c for (cn, c) in table if cn == cn_norm})


def compute(declaration: dict[str, Any], table: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    """Apply the pilot ruleset. `declaration` may carry: good_cn, country, tonnes, and (optional)
    contradiction markers prepared by a task (line_items, stated_total, country_alt, cn_alt, unit_mismatch)."""
    # --- contradiction check first (a contradiction is not a missing-input refusal) ---
    cd = _contradiction(declaration)
    if cd:
        return _out("contradiction", None, None, [], cd)

    missing: list[dict[str, str]] = []
    good = declaration.get("good_cn")
    country = (declaration.get("country") or "").strip() or None
    tonnes = declaration.get("tonnes")

    cn_norm = _norm_cn(good) if good else ""
    good_in_table = bool(cn_norm) and any(cn == cn_norm for (cn, _c) in table)

    # (a) good
    if not good:
        missing.append({"id": "good_cn", "label": "good (CN code)",
                        "why_required": "selects which row of the factor table applies"})
    elif not good_in_table:
        missing.append({"id": "good_cn", "label": f"good (CN {good}) is not in the supplied factor table",
                        "why_required": "only goods listed in the table have an applicable default value"})

    # (b) country — required to select a country-specific default; blocks per-tonne too
    if not country:
        missing.append({"id": "country", "label": "country of production",
                        "why_required": "default values are country-specific; none can be selected without it "
                                        "(this blocks the per-tonne figure as well as the total)"})
    elif good_in_table and (cn_norm, country) not in table:
        missing.append({"id": "country", "label": f"country '{country}' is not listed for this good in the table",
                        "why_required": f"the table covers this good only for: {', '.join(_countries_for_good(table, cn_norm))}"})

    # (c) quantity
    if tonnes is None:
        missing.append({"id": "tonnes", "label": "quantity (tonnes of the good)",
                        "why_required": "the total equals the per-tonne default value times the tonnage"})
    elif not isinstance(tonnes, (int, float)) or tonnes < 0:
        missing.append({"id": "tonnes", "label": "a valid non-negative quantity (tonnes)",
                        "why_required": "the tonnage must be a usable number to compute the total"})

    if missing:
        return _out("refused", None, None, missing, None)

    cell = table[(cn_norm, country)]
    see = cell["total"]
    if see is None:
        return _out("refused", None, None,
                    [{"id": "default_value", "label": f"no default value is published for CN {good} / {country}",
                      "why_required": "the table lists this pair without a usable total value"}], None)
    exact = Decimal(str(see)) * Decimal(str(tonnes))  # Decimal product avoids float drift before rounding
    total = float(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return _out("computed", total, see, [], None)


def _contradiction(d: dict[str, Any]) -> str | None:
    """Minimal internal-consistency checks (exercised by Category C in Stages 2-3)."""
    li, st = d.get("line_items"), d.get("stated_total_tonnes")
    if li is not None and st is not None and round(sum(li), 6) != round(float(st), 6):
        return f"line-item tonnages sum to {sum(li)} but the stated total is {st}"
    if d.get("country") and d.get("country_alt") and d["country"] != d["country_alt"]:
        return f"country stated two ways: '{d['country']}' and '{d['country_alt']}'"
    if d.get("good_cn") and d.get("cn_alt") and _norm_cn(d["good_cn"]) != _norm_cn(d["cn_alt"]):
        return f"CN code stated two ways: '{d['good_cn']}' and '{d['cn_alt']}'"
    if d.get("unit_mismatch"):
        return str(d["unit_mismatch"])
    return None


def _out(status, figure, per_tonne, missing, cd) -> dict[str, Any]:
    return {"status": status, "figure_tCO2e": figure, "per_tonne_tCO2e": per_tonne,
            "missing_inputs": missing, "contradiction_detail": cd}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    tbl = load_factor_table(os.path.join(here, "..", "ruleset", "factor-table.csv"))
    # tiny demo
    import json
    print(json.dumps(compute({"good_cn": "7214 20 00", "country": "India", "tonnes": 1000}, tbl), indent=2))
    print(json.dumps(compute({"good_cn": "7201", "tonnes": 500}, tbl), indent=2))  # missing country
