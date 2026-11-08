"""make_excluded_contradictory.py — build the hand-score packet for the ~106 UNSCOREABLE Category-C runs
(round-2 review WS1.1). These are EXISTING outputs the two LLM graders left unscoreable (at least one
grader's verdict failed validation), so no re-run and no model spend. A human scores them from the raw
output + reference; the result folds into a C-rate recompute + sensitivity analysis.

A Category-C run is "excluded" iff it is NOT in the dual-valid consensus set — i.e. at least one grader's
verdict is invalid, so the two graders could not be compared. (Contested-but-dual-valid C runs are already
adjudicated in the 225 hand-check and are NOT here.)

Each row: {run_id, model_key, model_id, task_id, condition, raw_output, reference,
           grader_a:{valid, verdict, errors}, grader_b:{valid, verdict, errors}, reason_unscoreable,
           human_label:null, human_notes:null}.  Deterministic, stdlib, NO API, NO network.

Usage:  python -I scripts/make_excluded_contradictory.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402  (ROOT + task/identity loaders; no SDK, no API)

ROOT = analyse.ROOT
RESULTS = analyse.RESULTS_DIR
SCORING = analyse.SCORING_DIR
TASKS_DIR = ROOT / "tasks"


def _load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def main() -> int:
    identity = {r["run_id"]: r for r in _load_jsonl(RESULTS / "_identity.jsonl")}
    tasks = {t["task_id"]: t for t in (json.loads(p.read_text(encoding="utf-8"))
                                       for p in sorted(TASKS_DIR.rglob("*.json")))}
    results = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in RESULTS.glob("run_*.json")}
    # ALL grader rows (valid AND invalid), keyed by run_id
    grows = {g: {r["run_id"]: r for r in _load_jsonl(SCORING / f"grades_{g}.jsonl")}
             for g in ("grader_a", "grader_b")}

    packet = []
    for rid, r in results.items():
        if r.get("category") != "C":
            continue
        ga = grows["grader_a"].get(rid)
        gb = grows["grader_b"].get(rid)
        a_valid = bool(ga and ga.get("valid"))
        b_valid = bool(gb and gb.get("valid"))
        if a_valid and b_valid:
            continue  # dual-valid → scoreable (in consensus / 225 hand-check), not an exclusion
        # reason
        bits = []
        if not a_valid:
            bits.append("grader_a invalid: " + ("; ".join(map(str, (ga or {}).get("errors") or [])) or
                        ("no verdict row" if ga is None else "unspecified")))
        if not b_valid:
            bits.append("grader_b invalid: " + ("; ".join(map(str, (gb or {}).get("errors") or [])) or
                        ("no verdict row" if gb is None else "unspecified")))
        idn = identity.get(rid, {})
        task = tasks.get(r.get("task_id"), {})
        packet.append({
            "run_id": rid,
            "model_key": idn.get("model_key"),
            "model_id": idn.get("model_id"),
            "task_id": r.get("task_id"),
            "condition": r.get("condition"),
            "raw_output": r.get("raw_output"),
            "reference": task.get("reference"),
            "grader_a": {"valid": a_valid, "verdict": (ga or {}).get("verdict"), "errors": (ga or {}).get("errors")},
            "grader_b": {"valid": b_valid, "verdict": (gb or {}).get("verdict"), "errors": (gb or {}).get("errors")},
            "reason_unscoreable": " | ".join(bits),
            "human_label": None,
            "human_notes": None,
        })

    packet.sort(key=lambda x: x["run_id"])
    out = SCORING / "excluded_contradictory.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in packet) + "\n", encoding="utf-8")

    import collections
    by_model = collections.Counter(x["model_key"] for x in packet)
    by_reason = collections.Counter(
        ("both invalid" if (not x["grader_a"]["valid"] and not x["grader_b"]["valid"])
         else "grader_a only" if not x["grader_a"]["valid"] else "grader_b only") for x in packet)
    # total C runs for the denominator check
    total_c = sum(1 for r in results.values() if r.get("category") == "C")
    print(f"excluded contradictory runs: {len(packet)} of {total_c} C runs "
          f"({100*len(packet)/total_c:.1f}%) -> {out.relative_to(ROOT)}")
    print(f"  by model: {dict(by_model)}")
    print(f"  by which grader failed: {dict(by_reason)}")
    print(f"  all rows carry raw_output+reference+both-grader-attempts+reason; human_label empty for scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
