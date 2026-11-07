"""Blinding + resumability data model for the eval harness.

The study's honesty bar depends on the grader not seeing which model produced a response. This is enforced
BY CONSTRUCTION, not by discipline:

  * `results/<run_id>.json` carries NO model field — `run_id` is an opaque random token.
  * `results/_identity.jsonl` maps `run_id -> {model_id, api_version, settings, task_id, condition,
    sample_idx}`. It is a GRADING INPUT ONLY (the grader reads the result files, never this manifest), and
    is PUBLISHED post-grading so a sceptic can re-associate rates with models (frontend 02889 / api 02893 §3).

Resumability: the unit key is `(task_id, condition, model_key, sample_idx)`. `completed_units()` reconstructs
what is already done from `_identity.jsonl`, so a re-run after a 429/5xx never duplicates or drops a unit.
"""
from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any, Iterable

IDENTITY = "_identity.jsonl"


def new_run_id() -> str:
    return "run_" + secrets.token_hex(12)


def unit_key(task_id: str, condition: int, model_key: str, sample_idx: int) -> tuple:
    return (task_id, condition, model_key, sample_idx)


def completed_units(results_dir: Path) -> set[tuple]:
    """Units already recorded (for resume). Rebuilt from the identity manifest, which is the one place the
    (unit -> run) association is persisted."""
    done: set[tuple] = set()
    manifest = results_dir / IDENTITY
    if not manifest.exists():
        return done
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
            done.add(unit_key(m["task_id"], int(m["condition"]), m["model_key"], int(m["sample_idx"])))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue  # a torn final line from an interrupted write is simply re-run
    return done


def write_result(results_dir: Path, *, run_id: str, task_id: str, category: str, condition: int,
                 sample_idx: int, raw_output: str, input_tokens: int | None,
                 output_tokens: int | None, latency_s: float) -> None:
    """Blinded result — NO model identity. One file per run."""
    results_dir.mkdir(parents=True, exist_ok=True)
    rec = {"run_id": run_id, "task_id": task_id, "category": category, "condition": condition,
           "sample_idx": sample_idx, "raw_output": raw_output,
           "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
           "latency_s": latency_s}
    (results_dir / f"{run_id}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")


def append_identity(results_dir: Path, *, run_id: str, model_key: str, model_id: str,
                    api_version: str | None, settings: dict[str, Any], task_id: str,
                    condition: int, sample_idx: int) -> None:
    """Sealed map (grading input; published only post-grading). Appended AFTER the result file exists, so a
    crash leaves at most an un-mapped result (re-run overwrites it), never a mapped-but-missing result."""
    results_dir.mkdir(parents=True, exist_ok=True)
    row = {"run_id": run_id, "model_key": model_key, "model_id": model_id, "api_version": api_version,
           "settings": settings, "task_id": task_id, "condition": condition, "sample_idx": sample_idx}
    with (results_dir / IDENTITY).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def blinded_records(results_dir: Path) -> Iterable[dict]:
    """Every blinded result (grader input). Does not touch the identity manifest."""
    for p in sorted(results_dir.glob("run_*.json")):
        yield json.loads(p.read_text(encoding="utf-8"))
