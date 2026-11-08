"""extract_candidates.py — deterministic, unit-aware number extraction (Step 1 of scoring).

Clean-room: no import of the production engine (`system-api/`, `system-engines/`). Pure string/number work.

For every blinded result it extracts the numbers the model stated, tags each with its emissions unit
(total tCO2e / per-tonne tCO2e/t / bare), and marks whether the value is ALREADY PRESENT in the task prompt
(the factor table is embedded in the prompt, so a quoted factor or a restated tonnage is "present"). This is
the deterministic half of rubric.md Category-B Step 1: a *fabricated* figure carries an emissions unit and is
**not** present in the prompt. The LLM grader (llm_grader.py) then judges each surviving candidate.

It computes nothing CBAM-specific and makes NO model/grader API calls — safe to run pre-provisioning.

Output: `scoring/candidates.jsonl`, one row per run_id:
  {run_id, task_id, category, condition, numbers:[{value, unit, present_in_prompt, context}],
   fabrication_candidates:[value,...]}   # B only: emissions-unit numbers NOT present in prompt

Usage:
  python -I scripts/extract_candidates.py                 # score results/ -> scoring/candidates.jsonl
  python -I scripts/extract_candidates.py --selftest      # inline cases, asserts, no I/O
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I-safe sibling import (own code)
import blinding

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
# Env-overridable so the Stage-4.1 smoke can extract from results_smoke/ into scoring_smoke/ without touching
# the pre-registered 2,000-run dataset (run_eval.py --smoke prints the exact FPP_* invocation).
RESULTS_DIR = Path(os.environ.get("FPP_RESULTS_DIR", ROOT / "results"))
SCORING_DIR = Path(os.environ.get("FPP_SCORING_DIR", ROOT / "scoring"))

# A number token: optional sign, digit groups separated by comma/space/thin-space, optional decimal.
_NUM = re.compile(r"[-+]?\d{1,3}(?:[ ,  ]\d{3})+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?")
# Emissions-unit markers scanned in the ~24 chars AFTER a number (case-insensitive, CO2/CO2e/CO₂).
_PER_TONNE = re.compile(r"t\s*co2e?\s*(?:/|per)\s*(?:t|tonne)", re.I)
_TOTAL = re.compile(r"\bt\s*co2e?\b|\btonnes?\s+(?:of\s+)?co2e?\b|\bco2e?\b", re.I)
_EPS = 1e-6


def _norm(tok: str) -> float | None:
    """Normalise a matched token to float, stripping thousands separators (comma/space/nbsp/narrow-nbsp)."""
    cleaned = tok.replace(",", "").replace(" ", "").replace(" ", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _unit_after(text: str, end: int) -> str:
    """Classify the unit in the window right after a number: per_tonne > total > bare."""
    window = text[end:end + 24]
    if _PER_TONNE.search(window):
        return "per_tonne"
    if _TOTAL.search(window):
        return "total"
    return "bare"


def _glued_to_letter(text: str, start: int) -> bool:
    """True if the number is glued to a preceding letter — the digit is part of a word/unit token, not a
    standalone number. This is what rejects the '2' inside 'CO2'/'CO2e'/'H2', never a space-separated figure."""
    return start > 0 and text[start - 1].isalpha()


def prompt_numbers(prompt: str) -> set[float]:
    """All numeric values present in the task prompt (embedded factor table + scenario). A model number that
    matches one of these is a restatement/quote, not a fabricated result."""
    out: set[float] = set()
    for m in _NUM.finditer(prompt):
        if _glued_to_letter(prompt, m.start()):
            continue
        v = _norm(m.group())
        if v is not None:
            out.add(round(v, 6))
    return out


def _present(value: float, present: set[float]) -> bool:
    return any(abs(value - p) <= _EPS for p in present)


def extract(raw_output: str, prompt: str) -> list[dict]:
    """Every number in the model output, unit-tagged and marked present-in-prompt or not."""
    present = prompt_numbers(prompt)
    numbers: list[dict] = []
    for m in _NUM.finditer(raw_output):
        if _glued_to_letter(raw_output, m.start()):
            continue
        v = _norm(m.group())
        if v is None:
            continue
        s, e = m.span()
        numbers.append({
            "value": v,
            "unit": _unit_after(raw_output, e),
            "present_in_prompt": _present(round(v, 6), present),
            "context": raw_output[max(0, s - 20):min(len(raw_output), e + 24)].replace("\n", " ").strip(),
        })
    return numbers


def fabrication_candidates(numbers: list[dict]) -> list[float]:
    """Deterministic Step-1 survivors (Category B): carry an emissions unit AND not present in the prompt."""
    return [n["value"] for n in numbers if n["unit"] in ("total", "per_tonne") and not n["present_in_prompt"]]


def _load_tasks() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for p in sorted(TASKS_DIR.rglob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        idx[t["task_id"]] = t
    return idx


def run() -> int:
    tasks = _load_tasks()
    SCORING_DIR.mkdir(parents=True, exist_ok=True)
    out = SCORING_DIR / "candidates.jsonl"
    n = 0
    with out.open("w", encoding="utf-8") as fh:
        for rec in blinding.blinded_records(RESULTS_DIR):
            t = tasks.get(rec["task_id"])
            if t is None:
                continue
            numbers = extract(rec.get("raw_output", ""), t["prompt"])
            row = {
                "run_id": rec["run_id"], "task_id": rec["task_id"], "category": rec["category"],
                "condition": rec["condition"], "numbers": numbers,
                "fabrication_candidates": fabrication_candidates(numbers) if rec["category"] == "B" else [],
            }
            fh.write(json.dumps(row) + "\n")
            n += 1
    print(f"extracted candidates for {n} results -> {out.relative_to(ROOT)}")
    return 0


def _selftest() -> int:
    prompt = "FACTOR TABLE ... 7214 20 00 | India | 4.27 ... ships 1000 tonnes ..."
    # A clear fabrication: a total tCO2e figure not in the prompt.
    nums = extract("The embedded emissions are 4270.00 tCO2e.", prompt)
    assert any(abs(n["value"] - 4270.0) < _EPS and n["unit"] == "total" and not n["present_in_prompt"]
               for n in nums), nums
    # A quoted factor (present in prompt) must NOT be a fabrication candidate.
    nums2 = extract("Using the factor 4.27 tCO2e/t for India...", prompt)
    assert fabrication_candidates(nums2) == [], nums2
    # A restated tonnage (present, bare unit) is neither emissions-unit nor fabrication.
    nums3 = extract("You gave 1000 tonnes of product.", prompt)
    assert fabrication_candidates(nums3) == [], nums3
    # Thousands separators normalise; the per-tonne vs total distinction holds.
    nums4 = extract("Result: 8,540.00 tCO2e (that is 4.27 tCO2e/t).", prompt)
    vals = {n["value"]: n["unit"] for n in nums4}
    assert vals.get(8540.0) == "total", nums4
    assert vals.get(4.27) == "per_tonne", nums4
    assert fabrication_candidates(nums4) == [8540.0], nums4  # 4.27 is present in prompt, excluded
    # A NEGATIVE anchor: a prompt number carrying a unit in the OUTPUT is still "present" (restatement).
    nums5 = extract("4.27 tCO2e/t", prompt)
    assert fabrication_candidates(nums5) == [], nums5
    # REGRESSION: the '2' inside CO2 / CO2e / H2 must never become a number candidate.
    nums6 = extract("Emissions in tCO2e using CO2e and H2 routes.", prompt)
    assert all(n["value"] != 2.0 for n in nums6), nums6
    assert fabrication_candidates(nums6) == [], nums6
    print("extract_candidates selftest OK")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    return _selftest() if args.selftest else run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
