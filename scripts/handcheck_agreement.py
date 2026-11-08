"""handcheck_agreement.py — FINAL supplementary numbers for the operator's report (02947/02949):
per-category rate table with task-level bootstrap CIs, and HUMAN-vs-GRADER agreement on the 225-run
hand-check. Reuses analyse.py's assembly + bootstrap; stdlib only; NO API calls; reads committed
scoring/ + results/. Deterministic (analyse.SEED). This validates the pinned graders against the human
adjudication — the hand-check's primary job.

Usage:  python -I scripts/handcheck_agreement.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402  (assembly + bootstrap helpers; no SDK, no API)

SCORING = analyse.SCORING_DIR


def _load_grader(gk):
    d = {}
    for line in (SCORING / f"grades_{gk}.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("valid"):
                d[row["run_id"]] = row["verdict"]
    return d


def main() -> int:
    recs = analyse.assemble()

    print("=" * 78)
    print(f"PER-CATEGORY FINAL RATES ({len(recs)} consensus runs, post-adjudication, task-level 95% CI)")
    print("  [source: analyse.per_category_rates — the SAME function behind analysis_report.json:category_rates]")
    print("=" * 78)
    rates = analyse.per_category_rates(recs)   # canonical single source; no second grouping to drift against
    for cat in ("A", "B", "C"):
        block_c = rates.get(cat)
        if not block_c:
            continue
        print(f"\nCategory {cat}  (n={block_c['n']})")
        for lab, d in sorted(block_c["labels"].items(), key=lambda kv: -kv[1]["count"]):
            ci = f"[{d['lo']:.3f}, {d['hi']:.3f}]" if d["lo"] is not None else "[n/a]"
            print(f"  {lab:<20} count={d['count']:>4}  share={d['share']*100:5.1f}%  "
                  f"task-mean={d['point']*100:5.1f}% CI95 {ci}")
    print("\nFabrication (a+b) by model, Category B:")
    for mk in sorted({r["model_key"] for r in recs}):
        pt = list(analyse.per_task_rates(recs, category="B", condition=None, model_key=mk,
                                         predicate=analyse.FAB).values())
        ci = analyse.bootstrap_mean_ci(pt)
        print(f"  {mk}: {ci['point']*100:.2f}%  CI95 [{ci['lo']*100:.2f}, {ci['hi']*100:.2f}]")

    ga, gb = _load_grader("grader_a"), _load_grader("grader_b")
    sample = {json.loads(l)["run_id"]: json.loads(l)
              for l in (SCORING / "handcheck_sample.jsonl").read_text().splitlines() if l.strip()}
    adj = {json.loads(l)["run_id"]: json.loads(l)["primary_label"]
           for l in (SCORING / "handcheck_adjudicated.jsonl").read_text().splitlines() if l.strip()}
    cat_of = {rid: sample[rid]["category"] for rid in sample}
    contested = set(json.loads((SCORING / "agreement.json").read_text()).get("contested_run_ids", []))

    def block(run_ids, title):
        a = defaultdict(lambda: [0, 0]); b = defaultdict(lambda: [0, 0]); ta = [0, 0]; tb = [0, 0]
        for rid in run_ids:
            cat = cat_of[rid]; h = adj[rid]
            if rid in ga:
                ok = int(analyse._primary(ga[rid], cat) == h); a[cat][0] += ok; a[cat][1] += 1; ta[0] += ok; ta[1] += 1
            if rid in gb:
                ok = int(analyse._primary(gb[rid], cat) == h); b[cat][0] += ok; b[cat][1] += 1; tb[0] += ok; tb[1] += 1
        print(f"\n{title}  (n={len(run_ids)})")
        print(f"  human vs grader_a (Opus): {ta[0]}/{ta[1]} = {100*ta[0]/ta[1]:.1f}%" if ta[1] else "  (no a)")
        print(f"  human vs grader_b (GPT) : {tb[0]}/{tb[1]} = {100*tb[0]/tb[1]:.1f}%" if tb[1] else "  (no b)")
        for cat in ("A", "B", "C"):
            sa = f"{a[cat][0]}/{a[cat][1]}={100*a[cat][0]/a[cat][1]:.0f}%" if a[cat][1] else "-"
            sb = f"{b[cat][0]}/{b[cat][1]}={100*b[cat][0]/b[cat][1]:.0f}%" if b[cat][1] else "-"
            print(f"    {cat}: grader_a {sa:>12}   grader_b {sb:>12}")

    print("\n" + "=" * 78)
    print("HUMAN vs GRADER AGREEMENT (225-run hand-check)")
    print("=" * 78)
    all_ids = list(adj.keys())
    block(all_ids, "ALL 225 (contested-ENRICHED by construction — a lower bound)")
    block([r for r in all_ids if r not in contested], "NON-contested subset (clean validation)")
    block([r for r in all_ids if r in contested], "CONTESTED subset (graders split by construction)")

    nc = [r for r in all_ids if r not in contested]
    ok = tot = 0
    for rid in nc:
        if rid in ga and rid in gb:
            la, lb = analyse._primary(ga[rid], cat_of[rid]), analyse._primary(gb[rid], cat_of[rid])
            if la is not None and la == lb:
                tot += 1; ok += int(la == adj[rid])
    print(f"\nCONSENSUS (both graders agreed) vs human, non-contested: {ok}/{tot} = {100*ok/tot:.1f}%")
    print("\nGrader fabrication flags (a/b) in hand-check vs human ruling:")
    for rid in all_ids:
        for gk, g in (("grader_a", ga), ("grader_b", gb)):
            if rid in g and analyse._primary(g[rid], cat_of[rid]) in ("a", "b"):
                print(f"  {rid[:20]}  cat={cat_of[rid]}  {gk}={analyse._primary(g[rid],cat_of[rid])}  human={adj[rid]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
