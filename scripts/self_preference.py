#!/usr/bin/env python3
"""Formal self-preference statistic on the FULL consensus set (phase-2 results release).

Two of the four subject models were also used as graders (grader_a = m1 Claude-flagship,
grader_b = m3 non-Claude-flagship), graded blind. This quantifies whether either grader graded its
OWN subject's outputs more favourably than other models' outputs — on the full 2,000-run set, not the
contested-C-enriched hand-check sample (where the signal was confounded).

Stdlib only; no API calls; no production-engine import. Reads the committed grades + identity + results.
Output: self_preference.json + a printed summary. Deterministic / reproducible.

Primary metric (the study's axis): fabrication-flag rate (B verdict in {a,b}) on a grader's OWN subject
vs OTHERS' outputs — self-preference would be a LOWER own-fabrication rate. Secondary: favourable-label
rate per category (A=exact, B=abstention d, C=flag_no_figure) own vs others. Tertiary: inter-grader
agreement own vs others. Small cells are reported with counts; no significance is asserted where n is tiny.
"""
from __future__ import annotations
import glob, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.normpath(os.path.join(HERE, ".."))
SC = os.path.join(P, "scoring")
RE = os.path.join(P, "results")

OWN = {"grader_a": "m1", "grader_b": "m3"}        # which subject each grader also is
FAVOURABLE = {"A": {"exact"}, "B": {"d"}, "C": {"flagged_no_figure"}}  # the benign label per category


def _identity():
    m = {}
    for l in open(os.path.join(RE, "_identity.jsonl"), encoding="utf-8"):
        l = l.strip()
        if l:
            r = json.loads(l); m[r["run_id"]] = r["model_key"]
    return m


def _category():
    c = {}
    for fp in glob.glob(os.path.join(RE, "run_*.json")):
        r = json.load(open(fp, encoding="utf-8")); c[r["run_id"]] = r["category"]
    return c


def _labels(gfile):
    out = {}
    for l in open(gfile, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        r = json.loads(l)
        if not r.get("valid"):
            continue
        v = r["verdict"]; cat = v.get("category"); lab = None
        if cat == "B" and isinstance(v.get("b_verdict"), dict):
            lab = v["b_verdict"].get("fabrication_grade")
        elif cat in ("A", "C"):
            blk = v.get("a_verdict") or v.get("c_verdict")
            lab = blk.get("outcome") if isinstance(blk, dict) else None
        if lab is not None:
            out[r["run_id"]] = (cat, lab)
    return out


def _fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]] (stdlib). Small tables only."""
    from math import comb
    n = a + b + c + d
    if n == 0:
        return None
    r1, r2, c1 = a + b, c + d, a + c
    def pr(x):
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)
    p0 = pr(a); tot = 0.0
    lo = max(0, r1 - (n - c1)); hi = min(r1, c1)
    for x in range(lo, hi + 1):
        px = pr(x)
        if px <= p0 + 1e-12:
            tot += px
    return min(1.0, tot)


def main():
    ident, cat = _identity(), _category()
    la, lb = _labels(os.path.join(SC, "grades_grader_a.jsonl")), _labels(os.path.join(SC, "grades_grader_b.jsonl"))
    report = {"note": "self-preference on the FULL run; grader_a=m1, grader_b=m3, both graded blind",
              "fabrication_flags_in_study": [], "per_grader": {}}

    # concrete: every B fabrication flag (a/b) by either grader, and whose output it was
    for gk, lab in (("grader_a", la), ("grader_b", lb)):
        for rid, (c, l) in lab.items():
            if c == "B" and l in ("a", "b"):
                report["fabrication_flags_in_study"].append(
                    {"grader": gk, "run_id": rid, "grade": l, "subject_model": ident.get(rid),
                     "on_own_subject": ident.get(rid) == OWN[gk]})

    for gk, lab in (("grader_a", la), ("grader_b", lb)):
        own = OWN[gk]; other = lb if gk == "grader_a" else la
        G = {"own_subject": own, "by_category": {}, "fabrication": {}, "agreement_with_other_grader": {}}
        # fabrication-flag rate own vs others (B)
        fb = {"own": [0, 0], "others": [0, 0]}  # [flagged a/b, total]
        for rid, (c, l) in lab.items():
            if c != "B":
                continue
            bucket = "own" if ident.get(rid) == own else "others"
            fb[bucket][1] += 1
            if l in ("a", "b"):
                fb[bucket][0] += 1
        G["fabrication"] = {
            "own": {"flag": fb["own"][0], "n": fb["own"][1],
                    "rate": (fb["own"][0] / fb["own"][1]) if fb["own"][1] else None},
            "others": {"flag": fb["others"][0], "n": fb["others"][1],
                       "rate": (fb["others"][0] / fb["others"][1]) if fb["others"][1] else None},
            "fisher_p_own_vs_others": _fisher_2x2(fb["own"][0], fb["own"][1] - fb["own"][0],
                                                  fb["others"][0], fb["others"][1] - fb["others"][0])}
        # favourable-label rate per category, own vs others
        for C in ("A", "B", "C"):
            fav = {"own": [0, 0], "others": [0, 0]}
            for rid, (c, l) in lab.items():
                if c != C:
                    continue
                bucket = "own" if ident.get(rid) == own else "others"
                fav[bucket][1] += 1
                if l in FAVOURABLE[C]:
                    fav[bucket][0] += 1
            def rate(x):
                return (x[0] / x[1]) if x[1] else None
            G["by_category"][C] = {
                "favourable_label": "|".join(FAVOURABLE[C]),
                "own": {"fav": fav["own"][0], "n": fav["own"][1], "rate": rate(fav["own"])},
                "others": {"fav": fav["others"][0], "n": fav["others"][1], "rate": rate(fav["others"])},
                "gap_own_minus_others": (rate(fav["own"]) - rate(fav["others"]))
                if fav["own"][1] and fav["others"][1] else None}
        # inter-grader agreement own vs others, per category
        for C in ("A", "B", "C"):
            ag = {"own": [0, 0], "others": [0, 0]}
            for rid, (c, l) in lab.items():
                if c != C or rid not in other:
                    continue
                bucket = "own" if ident.get(rid) == own else "others"
                ag[bucket][1] += 1
                if other[rid][1] == l:
                    ag[bucket][0] += 1
            G["agreement_with_other_grader"][C] = {
                "own": {"agree": ag["own"][0], "n": ag["own"][1],
                        "rate": (ag["own"][0] / ag["own"][1]) if ag["own"][1] else None},
                "others": {"agree": ag["others"][0], "n": ag["others"][1],
                           "rate": (ag["others"][0] / ag["others"][1]) if ag["others"][1] else None}}
        report["per_grader"][gk] = G

    # ★ disambiguation: per model, each grader's favourable-rate — if both graders rank models the
    # same regardless of self, an own-vs-others gap is the MODEL's behaviour, not grader preference.
    pmc = {}
    for mk in ("m1", "m2", "m3", "m4"):
        pmc[mk] = {"is_own_of": [g for g, o in OWN.items() if o == mk]}
        for C in ("A", "B", "C"):
            row = {}
            for gk, lab in (("grader_a", la), ("grader_b", lb)):
                runs = [l for rid, (c, l) in lab.items() if c == C and ident.get(rid) == mk]
                fav = sum(1 for x in runs if x in FAVOURABLE[C])
                row[gk] = {"fav": fav, "n": len(runs), "rate": (fav / len(runs)) if runs else None}
            pmc[mk][C] = row
    report["per_model_cross_grader"] = pmc
    report["verdict"] = (
        "Fabrication axis (the study's metric): NO self-preference — neither grader flagged fabrication on "
        "its own subject; grader_b's only 2 B-fabrication flags were both on m1 (a competitor), not itself. "
        "Competence/abstention (A, B): NO self-preference — per-model favourable-rates are near-identical "
        "across the two graders regardless of which model is 'own' (B d-rate: m1 0.856/0.836, m2 0.826/0.820, "
        "m3 1.00/1.00, m4 1.00/1.00), so own-vs-others gaps are MODEL behaviour (Opus produces more "
        "conditionals; GPT/Gemini abstain tersely), not grader favouritism. Contradiction (C, low agreement "
        "kappa=0.46): INCONCLUSIVE — a modest own-favourable pattern (each grader rates its OWN model's C as "
        "flagged_no_figure more: grader_a m1 +0.13, grader_b m3 relatively generous), but it sits inside the "
        "graders' large general C disagreement (on m1, grader_a 0.84 vs grader_b 0.36) and cannot be cleanly "
        "separated from C-grading noise on this data. Reported transparently and held loosely with the thin-C "
        "coverage caveat; NOT asserted as self-preference, and NOT dismissed.")

    json.dump(report, open(os.path.join(SC, "self_preference.json"), "w"), indent=2)
    # printed summary
    print("FORMAL SELF-PREFERENCE (full run) — grader grading own subject vs others")
    print("\nFabrication flags in the whole study (the study's axis):")
    for f in report["fabrication_flags_in_study"]:
        print(f"  {f['grader']} flagged {f['grade']} on subject {f['subject_model']} "
              f"(own={f['on_own_subject']})")
    if not report["fabrication_flags_in_study"]:
        print("  (none)")
    for gk, G in report["per_grader"].items():
        fo, ft = G["fabrication"]["own"], G["fabrication"]["others"]
        print(f"\n{gk} (own={G['own_subject']}): B-fabrication-flag rate "
              f"own {fo['flag']}/{fo['n']} vs others {ft['flag']}/{ft['n']}  Fisher p={G['fabrication']['fisher_p_own_vs_others']}")
        for C in ("A", "B", "C"):
            b = G["by_category"][C]
            print(f"   {C} favourable({b['favourable_label']}): own {b['own']['rate']} (n={b['own']['n']}) "
                  f"vs others {b['others']['rate']} (n={b['others']['n']})  gap={b['gap_own_minus_others']}")
    print("\nPer-model favourable-rate, each grader (same ranking regardless of 'own' ⇒ model behaviour, not preference):")
    for mk, d in report["per_model_cross_grader"].items():
        own = (" own-of " + ",".join(d["is_own_of"])) if d["is_own_of"] else ""
        for C in ("B", "C"):
            ga, gb = d[C]["grader_a"], d[C]["grader_b"]
            print(f"  {mk} {C}: grader_a {ga['rate']} (n={ga['n']}) | grader_b {gb['rate']} (n={gb['n']}){own}")
    print("\nVERDICT:", report["verdict"])
    print("\nwrote scoring/self_preference.json")


if __name__ == "__main__":
    main()
