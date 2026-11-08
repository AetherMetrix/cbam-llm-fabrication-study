"""make_handcheck.py — build the 200-output stratified hand-check packet (SPEC Step 3).

Stratifies 200 runs across the 4 subject models × 3 categories (post-grading unblinding is allowed — the
identity map is a grading input and is published anyway), and FORCE-INCLUDES the adjudication-critical runs:
every contested run (graders disagree on the primary label) and every run with a fabrication (b/a) verdict
from either grader. Writes a human-review packet with the blinded output + both graders' verdicts + the
reference ground truth, so a human can score each without re-deriving anything.

Deterministic (fixed seed) for reproducibility. NO API calls, NO network. Reads results/ + scoring/.

Usage:  python -I scripts/make_handcheck.py [--n 200]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = Path(os.environ.get("FPP_RESULTS_DIR", ROOT / "results"))
SCORING_DIR = Path(os.environ.get("FPP_SCORING_DIR", ROOT / "scoring"))
TASKS_DIR = ROOT / "tasks"
SEED = 20260907
N_DEFAULT = 200


def _load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_DEFAULT)
    args = ap.parse_args(argv)

    identity = {r["run_id"]: r for r in _load_jsonl(RESULTS_DIR / "_identity.jsonl")}
    results = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in RESULTS_DIR.glob("run_*.json")}
    tasks = {t["task_id"]: t for t in (json.loads(p.read_text(encoding="utf-8"))
                                       for p in sorted(TASKS_DIR.rglob("*.json")))}
    grades = {g: {r["run_id"]: r for r in _load_jsonl(SCORING_DIR / f"grades_{g}.jsonl")}
              for g in ("grader_a", "grader_b")}
    agreement = json.loads((SCORING_DIR / "agreement.json").read_text(encoding="utf-8"))
    contested = set(agreement.get("contested_run_ids", []))

    # force-include: contested + any fabrication (a/b) verdict from either grader
    def is_fab(rid):
        for g in grades.values():
            v = (g.get(rid) or {}).get("verdict") or {}
            bv = v.get("b_verdict") or {}
            if isinstance(bv, dict) and bv.get("fabrication_grade") in ("a", "b"):
                return True
        return False
    forced = set(contested)
    for rid in results:
        if is_fab(rid):
            forced.add(rid)

    # strata: (model_key, category); fill to ~even across the 12 cells, forced ones counted in
    rng = random.Random(SEED)
    by_cell: dict[tuple, list[str]] = {}
    for rid, r in results.items():
        mk = (identity.get(rid) or {}).get("model_key")
        cell = (mk, r["category"])
        by_cell.setdefault(cell, []).append(rid)
    cells = sorted(by_cell, key=str)
    per_cell = max(1, args.n // len(cells))
    chosen: set[str] = set(f for f in forced if f in results)
    for cell in cells:
        pool = by_cell[cell][:]
        rng.shuffle(pool)
        picked = [r for r in pool if r in chosen][:per_cell]
        for r in pool:
            if len(picked) >= per_cell:
                break
            if r not in chosen:
                picked.append(r)
        chosen.update(picked)

    packet = []
    for rid in sorted(chosen):
        r = results[rid]
        task = tasks.get(r["task_id"], {})
        packet.append({
            "run_id": rid,
            "model_key": (identity.get(rid) or {}).get("model_key"),
            "model_id": (identity.get(rid) or {}).get("model_id"),
            "task_id": r["task_id"], "category": r["category"], "condition": r["condition"],
            "contested": rid in contested,
            "raw_output": r["raw_output"],
            "reference": task.get("reference"),
            "grader_a": (grades["grader_a"].get(rid) or {}).get("verdict"),
            "grader_b": (grades["grader_b"].get(rid) or {}).get("verdict"),
            "human_label": None, "human_notes": None,   # to be filled by the reviewer
        })
    out = SCORING_DIR / "handcheck_sample.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in packet) + "\n", encoding="utf-8")

    import collections
    bycat = collections.Counter(x["category"] for x in packet)
    bymodel = collections.Counter(x["model_key"] for x in packet)
    print(f"hand-check packet: {len(packet)} runs -> {out.relative_to(ROOT)}")
    print(f"  by category: {dict(bycat)}   by model: {dict(bymodel)}")
    print(f"  forced-in: {len([x for x in packet if x['contested']])} contested + "
          f"{len([x for x in packet if is_fab(x['run_id'])])} fabrication-candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
