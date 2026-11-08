"""review_stats.py — the review-round supplementary statistics (the scientific review's asks), all on the
frozen graded data: NO API, NO re-run. Reuses analyse.py. Reproducible, stdlib-only.

Produces, for the article + an auditor:
  - exact Clopper-Pearson / rule-of-three bounds for the zero-fabrication and the C flag-with-figure cells
    (bootstrap degenerates at those counts; every OTHER category rate stays task-level bootstrap);
  - raw per-family grader agreement (observed P_o) alongside Cohen's κ;
  - per-model Category-C label distribution;
  - Category-B abstention/conditional rates by prompt condition, task-level bootstrap CIs;
  - parser-validity breakdown (valid vs incomplete; no unparsed serialization formats remain);
  - per-family unscoreable rates.

Usage:  python -I scripts/review_stats.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse  # noqa: E402

ROOT = analyse.ROOT
SCORING = analyse.SCORING_DIR
RESULTS = analyse.RESULTS_DIR


def cp_upper_zero(n, alpha=0.05):
    """One-sided (upper) and two-sided-upper 95% bound for 0 successes in n (exact Clopper-Pearson)."""
    return 1 - alpha ** (1.0 / n), 1 - (alpha / 2) ** (1.0 / n)


def wilson(k, n, z=1.95996398454):
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / d, (centre + half) / d


def _binom_cdf(k, n, p):
    """P(X <= k), X ~ Binomial(n, p); summed in log-space for stability."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    s = 0.0
    for i in range(0, k + 1):
        lt = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
              + i * math.log(p) + (n - i) * math.log(1 - p))
        s += math.exp(lt)
    return s


def clopper_pearson(k, n, alpha=0.05):
    """Exact two-sided Clopper-Pearson 95% interval for k/n, by bisection on the binomial CDF
    (reliable, stdlib only — this is the method §setup pre-specifies for the boundary cells)."""
    def _bisect(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            m = (lo + hi) / 2
            if f(m) > target:   # P(X<=·) is decreasing in p
                lo = m
            else:
                hi = m
        return (lo + hi) / 2
    upper = _bisect(lambda p: _binom_cdf(k, n, p), alpha / 2)
    lower = 0.0 if k == 0 else _bisect(lambda p: _binom_cdf(k - 1, n, p), 1 - alpha / 2)
    return lower, upper


def _load_grader(gk):
    d, rows = {}, []
    for line in (SCORING / f"grades_{gk}.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows.append(r)
            if r.get("valid"):
                d[r["run_id"]] = r["verdict"]
    return d, rows


def main() -> int:
    recs = analyse.assemble()
    by_cat = defaultdict(list)
    for r in recs:
        by_cat[r["category"]].append(r)
    results = {p.stem: json.loads(p.read_text()) for p in RESULTS.glob("run_*.json")}
    ga, ga_rows = _load_grader("grader_a")
    gb, gb_rows = _load_grader("grader_b")

    print("== exact bounds for the two boundary cells (Clopper-Pearson; rest stay task-level bootstrap) ==")
    for label, n in (("fabrication 0/988 (run-level)", 988), ("fabrication 0/25 (task-level)", 25),
                     ("fabrication 0/50 (pooled)", 50)):
        one, two = cp_upper_zero(n)
        print(f"  {label}: 95% one-sided upper {one*100:.2f}% | two-sided upper {two*100:.2f}%")
    # full-family flag-with-figure count/n straight from the data (after the 106 fold-in)
    fwf = sum(1 for r in by_cat["C"] if r["label"] == "flagged_with_figure")
    nc = len(by_cat["C"])
    cp_lo, cp_hi = clopper_pearson(fwf, nc)
    w_lo, w_hi = wilson(fwf, nc)
    print(f"  C flag-with-figure {fwf}/{nc} = {100*fwf/nc:.2f}%  "
          f"exact Clopper-Pearson 95% [{cp_lo*100:.1f}%, {cp_hi*100:.1f}%]  (Wilson [{w_lo*100:.1f}%, {w_hi*100:.1f}%])")

    print("\n== raw per-family agreement (observed P_o, both graders valid) vs kappa ==")
    kappa = json.loads((SCORING / "agreement.json").read_text()).get("kappa_by_category", {})
    for cat in ("A", "B", "C"):
        both = [rid for rid in (ga.keys() & gb.keys()) if results.get(rid, {}).get("category") == cat]
        agree = sum(1 for rid in both
                    if analyse._primary(ga[rid], cat) is not None
                    and analyse._primary(ga[rid], cat) == analyse._primary(gb[rid], cat))
        po = agree / len(both) if both else float("nan")
        print(f"  {cat}: raw agreement {agree}/{len(both)} = {po*100:.1f}%   (kappa = {kappa.get(cat):.3f})")

    print("\n== per-model Category-C label distribution (consensus) ==")
    for mk in sorted({r["model_key"] for r in recs}):
        cnt = Counter(r["label"] for r in by_cat["C"] if r["model_key"] == mk)
        n = sum(cnt.values())
        print(f"  {mk} (n={n}): " + "  ".join(f"{k} {v} ({100*v/n:.0f}%)"
              for k, v in sorted(cnt.items(), key=lambda x: -x[1])))

    print("\n== Category-B by prompt condition (task-level bootstrap CI) ==")
    for cond in (1, 2):
        for lab, name in (("d", "abstention"), ("c", "conditional")):
            pt = list(analyse.per_task_rates(recs, category="B", condition=cond, model_key=None,
                                             predicate=lambda l, lab=lab: l == lab).values())
            ci = analyse.bootstrap_mean_ci(pt)
            print(f"  cond {cond} {name:11s}: {ci['point']*100:5.1f}% [{ci['lo']*100:.1f}, {ci['hi']*100:.1f}]")

    print("\n== parser validity (no unparsed serialization formats remain) ==")
    for gk, rows in (("grader_a", ga_rows), ("grader_b", gb_rows)):
        valid = sum(1 for r in rows if r.get("valid"))
        inv = [r for r in rows if not r.get("valid")]
        reasons = Counter()
        for r in inv:
            e = " | ".join(map(str, r.get("errors") or [])) or "empty"
            reasons["missing rationale" if "rationale" in e else
                    "null/invalid outcome" if "invalid" in e or "None" in e else
                    "empty" if e == "empty" else "other"] += 1
        print(f"  {gk}: {valid}/{len(rows)} valid; {len(inv)} incomplete -> {dict(reasons)}")

    print("\n== unscoreable rates (1 - scored/total) ==")
    tot = {"A": 600, "B": 1000, "C": 400}
    for cat in ("A", "B", "C"):
        s = len(by_cat[cat])
        print(f"  {cat}: {tot[cat]-s}/{tot[cat]} = {100*(tot[cat]-s)/tot[cat]:.1f}% unscoreable (scored {s})")
    print(f"\n  total scored N = {len(recs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
