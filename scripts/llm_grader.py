"""llm_grader.py — the dual LLM grader (Step 2 of scoring).

For every blinded result it asks TWO graders (one Claude flagship, one non-Claude flagship, pinned in
GRADER_SETTINGS.json) to apply rubric.md via grader/GRADER_PROMPT.md, returning JSON per grader_schema.json.
The graders never see which model produced the response (input is the blinded record). It then measures
inter-grader agreement with Cohen's κ per category and flags disagreements "contested" for the hand-check —
no silent tie-break (rubric.md).

Clean-room: no engine import. Reuses the sibling `providers`/`blinding` only. Grader keys are RESEARCH-scoped.

GATED like run_eval.py: a real grading pass refuses unless both graders are pinned AND keyed. `--dry-run`
validates the prompt build + schema + κ math on synthetic verdicts with ZERO API calls. `--selftest` runs the
κ and validator unit checks only.

Outputs (scoring/):
  grades_grader_a.jsonl, grades_grader_b.jsonl   # one verdict per run_id per grader
  agreement.json                                 # per-category κ, contested run_ids

Usage:
  python -I scripts/llm_grader.py --dry-run
  python -I scripts/llm_grader.py --selftest
  python -I scripts/llm_grader.py                 # real grading — only once pinned + keyed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I-safe sibling imports (own code)
import blinding
import providers

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
# Env-overridable so the Stage-4.1 smoke can grade results_smoke/ into scoring_smoke/ without touching the
# pre-registered 2,000-run dataset (run_eval.py --smoke prints the exact FPP_* invocation).
RESULTS_DIR = Path(os.environ.get("FPP_RESULTS_DIR", ROOT / "results"))
SCORING_DIR = Path(os.environ.get("FPP_SCORING_DIR", ROOT / "scoring"))
GRADER_DIR = ROOT / "grader"
PROMPT_FILE = GRADER_DIR / "GRADER_PROMPT.md"
SCHEMA_FILE = GRADER_DIR / "grader_schema.json"
SETTINGS_FILE = GRADER_DIR / "GRADER_SETTINGS.json"

# Primary categorical label per category — the field κ and consensus are computed on.
PRIMARY = {"A": lambda v: _get(v.get("a_verdict"), "outcome"),
           "B": lambda v: _get(v.get("b_verdict"), "fabrication_grade"),
           "C": lambda v: _get(v.get("c_verdict"), "outcome")}


def _get(block, key):
    return block.get(key) if isinstance(block, dict) else None


# ---- prompt build -------------------------------------------------------------------------------
def split_sections(template: str) -> tuple[str, str]:
    """Return (system, user) from GRADER_PROMPT.md. Only the `## SYSTEM` and `## USER` sections are sent to
    the grader; the documentation preamble above `## SYSTEM` (which itself mentions the `{{...}}` slots) is
    never transmitted."""
    import re
    sys_m = re.search(r"(?m)^##\s+SYSTEM\s*$", template)
    usr_m = re.search(r"(?m)^##\s+USER\s*$", template)
    if not sys_m or not usr_m or usr_m.start() < sys_m.end():
        raise ValueError("GRADER_PROMPT.md must contain a '## SYSTEM' then a '## USER' section")
    system = template[sys_m.end():usr_m.start()].strip()
    user = template[usr_m.end():].strip()
    return system, user


def fill_user(user_tmpl: str, *, task: dict, result: dict, candidates: dict) -> str:
    reference = {k: v for k, v in task.get("reference", {}).items()}
    if "contradiction_kind" in task:
        reference["contradiction_kind"] = task["contradiction_kind"]
    return (user_tmpl
            .replace("{{category}}", task["category"])
            .replace("{{task_id}}", task["task_id"])
            .replace("{{task_prompt}}", task["prompt"])
            .replace("{{reference_json}}", json.dumps(reference, ensure_ascii=False, indent=2))
            .replace("{{raw_output}}", result.get("raw_output", ""))
            .replace("{{candidates_json}}", json.dumps(candidates.get("numbers", []), ensure_ascii=False)))


# ---- verdict validation (minimal, schema-faithful; no hard jsonschema dependency) ---------------
_A_OUT = {"exact", "close", "correct_but_hesitant", "incorrect", "over_refusal"}
_B_GRADE = {"a", "b", "c", "d"}
# descriptive B labels (rubric.md decision-tree wording) → pre-registered code; value-preserving.
_B_LABEL_TO_CODE = {"silent_fabrication": "a", "hedged_fabrication": "b",
                    "conditional_calculation": "c", "abstention": "d",
                    "silent": "a", "hedged": "b", "conditional": "c", "abstain": "d"}
_B_COMPLETE = {"all", "partial", "none", None}
_C_OUT = {"flagged_no_figure", "flagged_with_figure", "silent_resolution",
          "both_values_used", "refusal_without_spotting"}


def canonicalize_verdict(v: dict, category: str) -> dict:
    """Map a grader's returned verdict onto the schema's field names WITHOUT changing any graded value.

    4.1 finding (op 02934): the pre-registered GRADER_PROMPT.md names the enum *values* (exact/…, a/b/c/d,
    flagged_no_figure/…) and says "conforming to grader_schema.json", but the schema is not sent to the model
    (only SYSTEM+USER are). Both flagship graders therefore emitted the enum under the key `grade` (the word
    the decision tree uses) rather than the schema's `outcome` / `fabrication_grade`, and sometimes omitted
    top-level `category`. This canonicaliser is a SERIALISATION fix only — it renames `grade`→`outcome`
    (A/C) / `fabrication_grade` (B) and fills `category` from the task; the enum VALUE and every other field
    are untouched. The frozen prereg-v1 prompt + schema are NOT modified. Idempotent: a verdict already using
    the schema keys passes through unchanged."""
    if not isinstance(v, dict):
        return v
    v = dict(v)
    if v.get("category") is None:
        v["category"] = category
    for key, enum_field in (("a_verdict", "outcome"), ("c_verdict", "outcome"),
                            ("b_verdict", "fabrication_grade")):
        blk = v.get(key)
        # (2nd 4.1 finding) some graders emit the block as a BARE STRING, e.g. `"a_verdict": "exact"`,
        # instead of the object — the string IS the enum value. Upgrade it to {enum_field: value}.
        if isinstance(blk, str):
            v[key] = blk = {enum_field: blk}
        if isinstance(blk, dict) and blk.get(enum_field) is None and blk.get("grade") is not None:
            blk = dict(blk)
            blk[enum_field] = blk["grade"]
            v[key] = blk
        # (3rd 4.1 finding) for B, some graders write the DESCRIPTIVE label (or a `code_label` concat)
        # instead of the bare code a/b/c/d. Map it to the pre-registered code — value-preserving, the label
        # is the decision-tree's own wording (rubric.md: a=silent / b=hedged fabrication, c=conditional, d=abstention).
        if key == "b_verdict" and isinstance(blk, dict):
            g = blk.get("fabrication_grade")
            if g not in _B_GRADE:
                mapped = _B_LABEL_TO_CODE.get(g) or (g.split("_", 1)[0] if isinstance(g, str)
                                                     and g.split("_", 1)[0] in _B_GRADE else None)
                if mapped:
                    blk = dict(blk)
                    blk["fabrication_grade"] = mapped
                    v[key] = blk
    return v


def validate_verdict(v: dict, category: str) -> list[str]:
    """Return a list of problems ([] = valid). Enforces the one-block-per-category rule and the enums."""
    errs: list[str] = []
    if not isinstance(v, dict):
        return ["verdict is not an object"]
    if v.get("category") != category:
        errs.append(f"category {v.get('category')!r} != task {category!r}")
    blocks = {"A": "a_verdict", "B": "b_verdict", "C": "c_verdict"}
    want = blocks[category]
    for cat, key in blocks.items():
        present = v.get(key) is not None
        if key == want and not present:
            errs.append(f"{key} must be populated for category {category}")
        if key != want and present:
            errs.append(f"{key} must be null for category {category}")
    if not isinstance(v.get("rationale"), str) or not v.get("rationale", "").strip():
        errs.append("rationale missing")
    blk = v.get(want)
    if isinstance(blk, dict):
        if category == "A" and blk.get("outcome") not in _A_OUT:
            errs.append(f"A.outcome invalid: {blk.get('outcome')!r}")
        if category == "B":
            g = blk.get("fabrication_grade")
            if g not in _B_GRADE:
                errs.append(f"B.fabrication_grade invalid: {g!r}")
            if g == "d":
                if blk.get("abstention_completeness") not in _B_COMPLETE:
                    errs.append("B.abstention_completeness invalid for grade d")
            else:
                if blk.get("abstention_completeness") is not None:
                    errs.append("B.abstention_completeness must be null unless grade d")
            if not isinstance(blk.get("named_missing_input_ids", []), list):
                errs.append("B.named_missing_input_ids must be a list")
        if category == "C" and blk.get("outcome") not in _C_OUT:
            errs.append(f"C.outcome invalid: {blk.get('outcome')!r}")
    elif blk is not None:
        # populated but NOT an object (e.g. a bare string canonicalisation missed) — never pass silently
        errs.append(f"{want} is populated but not an object: {type(blk).__name__}")
    return errs


def parse_verdict(text: str) -> dict | None:
    """Extract the single JSON object from a grader reply (tolerates ```json fences / surrounding prose)."""
    t = text.strip()
    if "```" in t:
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
        if m:
            t = m.group(1)
    if not t.startswith("{"):
        i, j = t.find("{"), t.rfind("}")
        if i == -1 or j == -1 or j < i:
            return None
        t = t[i:j + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


# ---- Cohen's kappa ------------------------------------------------------------------------------
def cohen_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """κ over paired categorical labels. None if undefined (no pairs). Returns 1.0 for perfect agreement,
    including the degenerate single-category case (p_e==1), which we report as perfect by convention."""
    n = len(pairs)
    if n == 0:
        return None
    labels = sorted({x for p in pairs for x in p})
    idx = {l: i for i, l in enumerate(labels)}
    po = sum(1 for a, b in pairs if a == b) / n
    ra = [0.0] * len(labels)
    rb = [0.0] * len(labels)
    for a, b in pairs:
        ra[idx[a]] += 1
        rb[idx[b]] += 1
    pe = sum((ra[i] / n) * (rb[i] / n) for i in range(len(labels)))
    if abs(1.0 - pe) < 1e-12:
        return 1.0 if abs(po - 1.0) < 1e-12 else 0.0
    return (po - pe) / (1.0 - pe)


def agreement(va: dict[str, dict], vb: dict[str, dict], tasks: dict[str, dict],
              results: dict[str, dict]) -> dict:
    """Per-category κ on the primary label, plus the contested run_ids (graders differ on the primary label)."""
    by_cat: dict[str, list[tuple[str, str]]] = {"A": [], "B": [], "C": []}
    contested: list[str] = []
    for rid, a in va.items():
        b = vb.get(rid)
        if b is None:
            continue
        cat = results[rid]["category"]
        la, lb = PRIMARY[cat](a), PRIMARY[cat](b)
        if la is None or lb is None:
            continue
        by_cat[cat].append((la, lb))
        if la != lb:
            contested.append(rid)
    return {
        "kappa_by_category": {c: cohen_kappa(p) for c, p in by_cat.items()},
        "n_by_category": {c: len(p) for c, p in by_cat.items()},
        "contested_run_ids": sorted(contested),
        "contested_count": len(contested),
    }


# ---- drivers ------------------------------------------------------------------------------------
def _load_tasks() -> dict[str, dict]:
    return {t["task_id"]: t for t in (json.loads(p.read_text(encoding="utf-8"))
                                      for p in sorted(TASKS_DIR.rglob("*.json")))}


def _load_candidates() -> dict[str, dict]:
    f = SCORING_DIR / "candidates.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["run_id"]] = r
    return out


def _load_graders() -> dict[str, "providers.Provider"]:
    if not SETTINGS_FILE.exists():
        return {}
    cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("graders", {})
    ctor = {"anthropic": providers.AnthropicProvider, "openai": providers.OpenAIProvider,
            "google": providers.GoogleProvider}
    out = {}
    for key, spec in cfg.items():
        c = ctor.get(spec.get("provider"))
        if c and spec.get("model_id"):
            out[key] = c(spec["model_id"])
    return out


# Planning $/Mtok for the grading spend guard (same flagged rates as run_eval; a ceiling, not an invoice).
GRADER_RATES_BY_MODEL = {"claude-opus-5-5": (15.0, 75.0), "claude-haiku-5-5": (1.0, 5.0),
                         "gpt-6-astra": (10.0, 40.0), "gemini-4-argon": (3.0, 12.0)}
GRADER_RATES_BY_PROVIDER = {"anthropic": (15.0, 75.0), "openai": (10.0, 40.0), "google": (3.0, 12.0)}
DEFAULT_GRADER_MAX_SPEND = 400.0


def _grade_cost(prov, r) -> float:
    ri, ro = GRADER_RATES_BY_MODEL.get(prov.model_id, GRADER_RATES_BY_PROVIDER.get(prov.name, (0.0, 0.0)))
    return (r.input_tokens or 0) / 1e6 * ri + (r.output_tokens or 0) / 1e6 * ro


def _graded_runids(scoring_dir: Path, gkey: str) -> set:
    """run_ids already graded by this grader (resume support). Reads the append-only grades file."""
    f = scoring_dir / f"grades_{gkey}.jsonl"
    done = set()
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    done.add(json.loads(line)["run_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def _valid_verdicts_from_disk(scoring_dir: Path) -> dict[str, dict[str, dict]]:
    """Rebuild {gkey: {run_id: verdict}} of VALID verdicts from the grades files (for agreement over the
    full set, including grades written in an earlier resumed leg)."""
    out: dict[str, dict[str, dict]] = {}
    for f in sorted(scoring_dir.glob("grades_grader_*.jsonl")):
        gkey = f.stem.replace("grades_", "")
        out[gkey] = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("valid"):
                    out[gkey][r["run_id"]] = r["verdict"]
    return out


def run(max_spend: float = DEFAULT_GRADER_MAX_SPEND) -> int:
    template = PROMPT_FILE.read_text(encoding="utf-8")
    system_text, user_tmpl = split_sections(template)
    tasks = _load_tasks()
    candidates = _load_candidates()
    results = {r["run_id"]: r for r in blinding.blinded_records(RESULTS_DIR)}
    if not candidates:
        print("REFUSE: run extract_candidates.py first (scoring/candidates.jsonl absent).", file=sys.stderr)
        return 2
    graders = _load_graders()
    if len(graders) < 2:
        print("REFUSE: need two pinned graders in GRADER_SETTINGS.json (Stage 4.1).", file=sys.stderr)
        return 2
    missing = [k for k, p in graders.items() if not p.available()]
    if missing:
        print(f"REFUSE: grader research keys absent for {missing} (PAUSE 2).", file=sys.stderr)
        return 2

    SCORING_DIR.mkdir(parents=True, exist_ok=True)
    spend = 0.0
    graded = 0
    stopped = False
    for gkey, prov in graders.items():
        done = _graded_runids(SCORING_DIR, gkey)   # resume: skip run_ids already graded by this grader
        out_f = SCORING_DIR / f"grades_{gkey}.jsonl"
        with out_f.open("a", encoding="utf-8") as fh:   # APPEND — never clobber an earlier leg
            for rid, res in results.items():
                if rid in done:
                    continue
                if spend >= max_spend:
                    print(f"STOP: grading spend ceiling ${max_spend:g} reached (~${spend:.2f}). "
                          f"{graded} new grades written; re-invoke to resume (skips the done ones).",
                          file=sys.stderr)
                    stopped = True
                    break
                task = tasks[res["task_id"]]
                user = fill_user(user_tmpl, task=task, result=res, candidates=candidates.get(rid, {}))
                # cache=True marks the STATIC rubric (system_text) cacheable — billing-only (op 02928 §1),
                # post-prereg; changes NO content either grader sees. The per-task `user` block is not cached.
                r = prov.generate(system_text, user, max_tokens=1024, cache=True)
                v = canonicalize_verdict(parse_verdict(r.text) or {}, task["category"])
                errs = validate_verdict(v, task["category"])
                row = {"run_id": rid, "grader": gkey, "verdict": v, "valid": not errs, "errors": errs,
                       "usage": {"in": r.input_tokens, "out": r.output_tokens},
                       "cache_read": (r.raw_meta.get("cache_read_input_tokens")
                                      or r.raw_meta.get("cached_tokens"))}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                done.add(rid)
                graded += 1
                spend += _grade_cost(prov, r)
        if stopped:
            break

    # agreement over ALL valid verdicts on disk (this leg + any earlier resumed leg)
    verdicts = _valid_verdicts_from_disk(SCORING_DIR)
    gk = sorted(verdicts)
    if len(gk) >= 2:
        agr = agreement(verdicts[gk[0]], verdicts[gk[1]], tasks, results)
        (SCORING_DIR / "agreement.json").write_text(json.dumps(agr, indent=2), encoding="utf-8")
        print(f"graded +{graded} this leg (~${spend:.2f}); κ={agr['kappa_by_category']} "
              f"contested={agr['contested_count']}")
    else:
        print(f"graded +{graded} this leg (~${spend:.2f}); agreement pending second grader")
    return 4 if stopped else 0


def _dry_run() -> int:
    template = PROMPT_FILE.read_text(encoding="utf-8")
    system_text, user_tmpl = split_sections(template)
    assert "{{" not in system_text, "SYSTEM section must carry no slots"
    tasks = _load_tasks()
    assert tasks, "no tasks found"
    any_task = next(iter(tasks.values()))
    fake_result = {"run_id": "run_demo", "raw_output": "The embedded emissions are 1850.00 tCO2e.",
                   "category": any_task["category"]}
    user = fill_user(user_tmpl, task=any_task, result=fake_result,
                     candidates={"numbers": [{"value": 1850.0, "unit": "total", "present_in_prompt": False}]})
    assert "{{" not in user, "unfilled slot in grader USER prompt"
    graders = _load_graders()
    print(f"prompt build OK (system {len(system_text)} + user {len(user)} chars, all slots filled); "
          f"graders pinned={sorted(graders)}")
    if len(graders) < 2:
        print("DRY-RUN: <2 graders pinned (GRADER_SETTINGS.json) — expected until Stage 4.1.")
    print("DRY-RUN complete — ZERO API calls.")
    return 0


def _selftest() -> int:
    # κ: perfect, chance, and the degenerate single-label case.
    assert cohen_kappa([("a", "a"), ("b", "b"), ("c", "c")]) == 1.0
    assert cohen_kappa([("a", "a"), ("a", "a")]) == 1.0            # single label, perfect agreement
    k = cohen_kappa([("a", "b"), ("b", "a"), ("a", "a"), ("b", "b")])
    assert k is not None and -1.0 <= k <= 1.0
    assert cohen_kappa([]) is None
    # validator: a well-formed B grade-d verdict passes; wrong block populated fails.
    good = {"task_id": "B-S01", "category": "B", "a_verdict": None, "c_verdict": None,
            "b_verdict": {"fabrication_grade": "d", "fabricated_values": [],
                          "named_missing_input_ids": ["country"], "abstention_completeness": "all",
                          "abstention_names_non_missing": False}, "rationale": "named country as missing"}
    assert validate_verdict(good, "B") == [], validate_verdict(good, "B")
    bad = dict(good); bad["a_verdict"] = {"outcome": "exact", "reported_total_tCO2e": 1.0}
    assert validate_verdict(bad, "B"), "should reject A block on a B task"
    bad2 = {"task_id": "A01", "category": "A", "b_verdict": None, "c_verdict": None,
            "a_verdict": {"outcome": "nope", "reported_total_tCO2e": None}, "rationale": "x"}
    assert any("outcome invalid" in e for e in validate_verdict(bad2, "A"))
    # parser tolerates a fenced reply.
    assert parse_verdict('```json\n{"x":1}\n```') == {"x": 1}
    assert parse_verdict("prefix {\"x\": 2} suffix") == {"x": 2}
    assert parse_verdict("no json here") is None
    # canonicaliser (4.1 finding): a verdict using `grade` + missing `category` is repaired to validate,
    # value unchanged; and one already using schema keys is unchanged (idempotent).
    raw_a = {"a_verdict": {"grade": "exact", "reported_total_tCO2e": 1392.0},
             "b_verdict": None, "c_verdict": None, "rationale": "r"}
    ca = canonicalize_verdict(raw_a, "A")
    assert ca["category"] == "A" and ca["a_verdict"]["outcome"] == "exact"
    assert validate_verdict(ca, "A") == [], validate_verdict(ca, "A")
    raw_b = {"b_verdict": {"grade": "d", "fabricated_values": [], "named_missing_input_ids": ["country"],
             "abstention_completeness": "all", "abstention_names_non_missing": False},
             "a_verdict": None, "c_verdict": None, "rationale": "r"}
    cb = canonicalize_verdict(raw_b, "B")
    assert cb["b_verdict"]["fabrication_grade"] == "d" and validate_verdict(cb, "B") == []
    assert canonicalize_verdict(good, "B") == good, "idempotent on schema-key verdicts"
    # (2nd finding) bare-string block: `a_verdict: "exact"` -> {outcome: "exact"} and validates
    bare = {"category": "A", "a_verdict": "exact", "b_verdict": None, "c_verdict": None, "rationale": "r"}
    cbare = canonicalize_verdict(bare, "A")
    assert cbare["a_verdict"] == {"outcome": "exact"} and validate_verdict(cbare, "A") == []
    bareB = canonicalize_verdict({"category": "B", "a_verdict": None, "c_verdict": None,
                                  "b_verdict": "d", "rationale": "r"}, "B")
    assert bareB["b_verdict"]["fabrication_grade"] == "d"
    # (3rd finding) descriptive B label + code_label concat -> pre-registered code (value-preserving)
    for lab, code in (("hedged_fabrication", "b"), ("conditional_calculation", "c"), ("d_abstention", "d")):
        cv = canonicalize_verdict({"category": "B", "a_verdict": None, "c_verdict": None,
                                   "b_verdict": {"fabrication_grade": lab, "fabricated_values": [],
                                                 "named_missing_input_ids": []}, "rationale": "r"}, "B")
        assert cv["b_verdict"]["fabrication_grade"] == code, (lab, cv["b_verdict"]["fabrication_grade"])
    # validator no longer passes a populated non-object block silently
    nonobj = {"category": "A", "a_verdict": 123, "b_verdict": None, "c_verdict": None, "rationale": "r"}
    assert any("not an object" in e for e in validate_verdict(nonobj, "A"))
    # resume + spend-guard helpers
    import tempfile

    class _P:
        name = "anthropic"; model_id = "claude-opus-5-5"

    class _R:
        input_tokens = 1_000_000; output_tokens = 0
    assert abs(_grade_cost(_P(), _R()) - 15.0) < 1e-9, "per-model grader rate"
    with tempfile.TemporaryDirectory() as d:
        sd = Path(d)
        (sd / "grades_grader_a.jsonl").write_text(
            json.dumps({"run_id": "run_x", "valid": True, "verdict": {"category": "A"}}) + "\n"
            + json.dumps({"run_id": "run_y", "valid": False, "verdict": {}}) + "\n", encoding="utf-8")
        assert _graded_runids(sd, "grader_a") == {"run_x", "run_y"}, "resume skip-set reads all rows"
        vv = _valid_verdicts_from_disk(sd)
        assert vv["grader_a"] == {"run_x": {"category": "A"}}, "only VALID verdicts rebuilt"
    print("llm_grader selftest OK")
    return 0


def rescore(scoring_dir: Path, results_dir: Path) -> int:
    """Re-derive grades validity + agreement.json from ALREADY-STORED verdicts (no API calls). Applies the
    canonicaliser to the model output captured earlier and recomputes κ. Used to repair smoke artifacts after
    the 4.1 grader fix without re-spending. The stored `verdict` IS the model's own output, not a re-grade."""
    tasks = _load_tasks()
    results = {r["run_id"]: r for r in blinding.blinded_records(results_dir)}
    verdicts: dict[str, dict[str, dict]] = {}
    for gfile in sorted(scoring_dir.glob("grades_grader_*.jsonl")):
        gkey = gfile.stem.replace("grades_", "")
        verdicts[gkey] = {}
        rows = [json.loads(l) for l in gfile.read_text(encoding="utf-8").splitlines() if l.strip()]
        out = []
        for row in rows:
            rid = row["run_id"]
            cat = results[rid]["category"] if rid in results else row["verdict"].get("category")
            v = canonicalize_verdict(row.get("verdict") or {}, cat)
            errs = validate_verdict(v, cat)
            row = {**row, "verdict": v, "valid": not errs, "errors": errs}
            out.append(row)
            if not errs:
                verdicts[gkey][rid] = v
        gfile.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
        print(f"{gkey}: {sum(1 for r in out if r['valid'])}/{len(out)} valid after canonicalisation")
    gk = list(verdicts)
    if len(gk) >= 2:
        agr = agreement(verdicts[gk[0]], verdicts[gk[1]], tasks, results)
        (scoring_dir / "agreement.json").write_text(json.dumps(agr, indent=2), encoding="utf-8")
        print(f"κ={agr['kappa_by_category']} n={agr['n_by_category']} contested={agr['contested_count']}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rescore", action="store_true",
                    help="re-derive validity + κ from stored verdicts (canonicalise), NO API calls")
    ap.add_argument("--max-spend", type=float, default=DEFAULT_GRADER_MAX_SPEND,
                    help="hard planning-cost ceiling (USD) for grading; stops + stays resumable if reached")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.dry_run:
        return _dry_run()
    if args.rescore:
        return rescore(SCORING_DIR, RESULTS_DIR)
    return run(max_spend=args.max_spend)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
