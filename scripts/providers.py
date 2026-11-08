"""Provider adapters for the Fabricated-Precision pilot eval harness.

Clean-room: fresh code, NO import of the production engine (`system-api/`, `system-engines/`). Standard
official-SDK usage only. Each adapter lazily imports its SDK so a missing provider never breaks the others.

Isolation: keys are read from RESEARCH-scoped env vars (`RESEARCH_<PROVIDER>_API_KEY`), deliberately distinct
from the product's `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, so this harness can never silently spend on
product credentials. No key present → `available()` is False and `generate()` raises; nothing runs until the
operator provisions research keys at PAUSE 2. Keys arrive only via `os.environ` (the operator places them in
the api host env right before the 4.1 smoke) — there is deliberately NO in-code dotenv load.

Each provider is called at the provider's DEFAULT settings (SPEC §Models). `describe()` returns exactly what
goes into MODEL_SETTINGS.md; `generate()` returns the actual settings used, captured from the live response
where the API exposes them — recorded, never assumed.

ONE-TIME-run hardening (operator 02928):
  * `generate()` wraps the provider call in `with_retry` — exponential backoff + full jitter on transient
    errors (429 / 5xx / timeouts / connection drops / Anthropic 529), fail-loud-immediate on fatal errors
    (401 auth, 400 bad-request, 404 model-not-found). A transient blip never loses a data point.
  * every `GenResult` carries `stop_reason` + a normalised `truncated` flag (the response hit
    `max_output_tokens`), so a truncated answer is flagged and reported, never silently scored.
  * `generate(..., cache=True)` marks the (static) system prompt cacheable — a billing-only optimisation for
    the grader's repeated rubric. It changes NO content the model sees (Anthropic: a `cache_control` marker;
    OpenAI caches automatically; Google left to implicit caching).
"""
from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

# --- transient-error retry -----------------------------------------------------------------------
# Retryable HTTP statuses: request-timeout, conflict, too-early, rate-limit, 5xx, Anthropic 529 overloaded.
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
# Exception class-name fragments treated as retryable when the SDK exposes no numeric status.
_RETRYABLE_NAMES = ("ratelimit", "timeout", "apiconnection", "connectionerror", "connectionreset",
                    "internalserver", "serviceunavailable", "overloaded", "apitimeout")
MAX_ATTEMPTS = 6
BASE_BACKOFF = 1.5          # seconds; exponential, capped, with full jitter
BACKOFF_CAP = 60.0


def _status_of(e: BaseException) -> int | None:
    for attr in ("status_code", "status", "http_status", "code"):
        v = getattr(e, attr, None)
        if isinstance(v, int):
            return v
    resp = getattr(e, "response", None)
    if resp is not None and isinstance(getattr(resp, "status_code", None), int):
        return resp.status_code
    return None


def is_retryable(e: BaseException) -> bool:
    """True for transient failures worth a backoff-retry; False for fatal (auth/bad-request/not-found)."""
    st = _status_of(e)
    if st is not None:
        return st in RETRYABLE_STATUS
    name = type(e).__name__.lower()
    return any(frag in name for frag in _RETRYABLE_NAMES)


def with_retry(fn: Callable[[], "GenResult"], *, max_attempts: int = MAX_ATTEMPTS,
               base: float = BASE_BACKOFF, sleep: Callable[[float], Any] = time.sleep,
               rng: Callable[[], float] = random.random) -> "GenResult":
    """Run fn(); on a retryable error back off (exponential + full jitter) and retry up to max_attempts.
    A non-retryable error is raised at once — fail loud, never silently swallow or loop forever."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:   # noqa: BLE001 — re-raised unless transient
            attempt += 1
            if attempt >= max_attempts or not is_retryable(e):
                raise
            cap = min(BACKOFF_CAP, base * (2 ** (attempt - 1)))
            sleep(cap * rng())


def load_settings_md(path: Path) -> dict:
    """Read the pre-registered MODEL_SETTINGS.md and return its single fenced ```json block as a dict.

    One canonical artifact (operator 02906): a human-readable pre-registration doc whose machine-readable
    roster/roles/intended-settings live in ONE fenced json block, so there is no MODEL_SETTINGS.md-vs-.json
    drift. Absent file or absent block -> {} (callers then stay fail-closed / unpinned). Uses only stdlib."""
    if not path.exists():
        return {}
    m = re.search(r"```json\s*(\{.*?\})\s*```", path.read_text(encoding="utf-8"), re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


@dataclass
class GenResult:
    text: str
    model_id: str
    api_version: str | None
    temperature: float | str | None      # value, or "default"/"fixed"/"n/a" when the API ignores it
    reasoning_mode: str | None            # "on"/"off"/"default"/"n/a"
    max_output_tokens: int | None
    input_tokens: int | None
    output_tokens: int | None
    latency_s: float
    stop_reason: str | None = None        # provider's finish/stop reason, verbatim where exposed
    truncated: bool = False               # response hit max_output_tokens — flag, never silently score
    raw_meta: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    name: str
    model_id: str
    def available(self) -> bool: ...
    def describe(self) -> dict[str, Any]: ...            # -> MODEL_SETTINGS.md row
    def generate(self, system: str, user: str, *, max_tokens: int, cache: bool = False) -> GenResult: ...


class _Base:
    """Shared env-key plumbing + retry. Subclasses set `name`, `env_key`, `model_id`, implement `_call`."""
    name = "base"
    env_key = ""
    model_id = ""
    reasoning_mode = "default"

    def __init__(self, model_id: str | None = None):
        if model_id:
            self.model_id = model_id

    def _key(self) -> str:
        return os.environ.get(self.env_key, "").strip()

    def available(self) -> bool:
        return bool(self._key())

    def describe(self) -> dict[str, Any]:
        return {"provider": self.name, "model_id": self.model_id, "env_key": self.env_key,
                "reasoning_mode": self.reasoning_mode, "key_present": self.available()}

    def generate(self, system: str, user: str, *, max_tokens: int, cache: bool = False) -> GenResult:
        if not self.available():
            raise RuntimeError(
                f"{self.name}: no research key in ${self.env_key} — provisioned at PAUSE 2, not before.")
        t0 = time.monotonic()
        res = with_retry(lambda: self._call(system, user, max_tokens, cache))
        res.latency_s = round(time.monotonic() - t0, 4)
        return res

    def _call(self, system: str, user: str, max_tokens: int, cache: bool) -> GenResult:  # pragma: no cover
        raise NotImplementedError


class AnthropicProvider(_Base):
    name = "anthropic"
    env_key = "RESEARCH_ANTHROPIC_API_KEY"

    def _call(self, system: str, user: str, max_tokens: int, cache: bool) -> GenResult:
        import anthropic  # lazy
        client = anthropic.Anthropic(api_key=self._key())
        # cache=True marks the static system prompt cacheable (billing-only; identical text to the model).
        system_arg: Any = ([{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                           if cache else system)
        r = client.messages.create(
            model=self.model_id, max_tokens=max_tokens, system=system_arg,
            messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text")
        u = getattr(r, "usage", None)
        stop = getattr(r, "stop_reason", None)
        return GenResult(
            text=text, model_id=getattr(r, "model", self.model_id),
            api_version=None, temperature="default", reasoning_mode=self.reasoning_mode,
            max_output_tokens=max_tokens,
            input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None),
            latency_s=0.0, stop_reason=stop, truncated=(stop == "max_tokens"),
            raw_meta={"stop_reason": stop,
                      "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None),
                      "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", None)})


class OpenAIProvider(_Base):
    name = "openai"
    env_key = "RESEARCH_OPENAI_API_KEY"

    def _call(self, system: str, user: str, max_tokens: int, cache: bool) -> GenResult:
        from openai import OpenAI  # lazy
        client = OpenAI(api_key=self._key())
        # Responses API; OpenAI caches long prompts automatically (no flag needed) — `cache` is a no-op here.
        r = client.responses.create(
            model=self.model_id, max_output_tokens=max_tokens,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        text = getattr(r, "output_text", "") or ""
        u = getattr(r, "usage", None)
        status = getattr(r, "status", None)
        inc = getattr(r, "incomplete_details", None)
        reason = getattr(inc, "reason", None) if inc is not None else None
        cached = None
        itd = getattr(u, "input_tokens_details", None)
        if itd is not None:
            cached = getattr(itd, "cached_tokens", None)
        return GenResult(
            text=text, model_id=getattr(r, "model", self.model_id),
            api_version=None, temperature="default", reasoning_mode=self.reasoning_mode,
            max_output_tokens=max_tokens,
            input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None),
            latency_s=0.0, stop_reason=(reason or status),
            truncated=(status == "incomplete" and reason == "max_output_tokens"),
            raw_meta={"status": status, "incomplete_reason": reason, "cached_tokens": cached})


class GoogleProvider(_Base):
    name = "google"
    env_key = "RESEARCH_GOOGLE_API_KEY"   # net-new per 02888/02894; no product equivalent exists

    def _call(self, system: str, user: str, max_tokens: int, cache: bool) -> GenResult:
        from google import genai  # lazy; `google-genai` SDK (net-new dependency)
        from google.genai import types
        client = genai.Client(api_key=self._key())
        r = client.models.generate_content(
            model=self.model_id, contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens))
        text = getattr(r, "text", "") or ""
        um = getattr(r, "usage_metadata", None)
        fr = None
        cands = getattr(r, "candidates", None)
        if cands:
            raw_fr = getattr(cands[0], "finish_reason", None)
            fr = getattr(raw_fr, "name", None) or (str(raw_fr) if raw_fr is not None else None)
        return GenResult(
            text=text, model_id=self.model_id, api_version=None,
            temperature="default", reasoning_mode=self.reasoning_mode, max_output_tokens=max_tokens,
            input_tokens=getattr(um, "prompt_token_count", None),
            output_tokens=getattr(um, "candidates_token_count", None),
            latency_s=0.0, stop_reason=fr, truncated=(fr == "MAX_TOKENS"),
            raw_meta={"finish_reason": fr,
                      "cached_content_token_count": getattr(um, "cached_content_token_count", None)})


# Roster: opaque keys (m1…m4) → provider. Real model ids are pinned at runtime into MODEL_SETTINGS.md
# BEFORE the full run (SPEC §Models: "confirmed at runtime"); the placeholders below are intentionally
# unset so nothing runs against an unpinned/guessed id.
def build_roster(model_ids: dict[str, str]) -> dict[str, Provider]:
    """`model_ids` maps roster key -> exact pinned model id, e.g.
    {"m1": "<anthropic-flagship>", "m2": "<anthropic-smallest>", "m3": "<openai-flagship>", "m4": "<google-flagship>"}
    sourced from MODEL_SETTINGS.md. Keys are opaque so downstream code can't infer the model from the key."""
    ctor = {"m1": AnthropicProvider, "m2": AnthropicProvider, "m3": OpenAIProvider, "m4": GoogleProvider}
    return {k: ctor[k](model_ids[k]) for k in ctor if model_ids.get(k)}


# --- offline selftest (no SDKs, no network) ------------------------------------------------------
def _selftest() -> int:
    import sys

    class _Err(Exception):
        def __init__(self, status=None):
            super().__init__(f"status={status}")
            if status is not None:
                self.status_code = status

    # retry classification: statuses + class-name fallback.
    assert is_retryable(_Err(429)) and is_retryable(_Err(503)) and is_retryable(_Err(529))
    assert not is_retryable(_Err(401)) and not is_retryable(_Err(400)) and not is_retryable(_Err(404))

    class RateLimitError(Exception):
        pass

    class AuthenticationError(Exception):
        pass
    assert is_retryable(RateLimitError()), "name-based retryable"
    assert not is_retryable(AuthenticationError()), "auth is fatal"

    # with_retry: succeeds after transient failures, never sleeps for real (stubbed), honours fatal + cap.
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Err(429)
        return GenResult("ok", "m", None, "default", None, 10, 1, 1, 0.0)
    got = with_retry(flaky, sleep=lambda s: None, rng=lambda: 0.5)
    assert got.text == "ok" and calls["n"] == 3, calls

    def fatal():
        raise _Err(401)
    try:
        with_retry(fatal, sleep=lambda s: None)
        raise AssertionError("fatal error must not be retried")
    except _Err:
        pass

    def always():
        raise _Err(500)
    slept: list[float] = []
    try:
        with_retry(always, sleep=slept.append, rng=lambda: 1.0, max_attempts=4)
        raise AssertionError("exhausted retries must re-raise")
    except _Err:
        pass
    assert len(slept) == 3 and max(slept) <= BACKOFF_CAP, slept   # 4 attempts => 3 backoffs, capped

    # generate() accepts the cache kwarg and fails CLOSED (RuntimeError, not TypeError) with no key.
    p = AnthropicProvider("x")
    assert not p.available()
    try:
        p.generate("sys", "usr", max_tokens=16, cache=True)
        raise AssertionError("must refuse without a key")
    except RuntimeError as e:
        assert "research key" in str(e)

    # truncation flag lives on GenResult and defaults false.
    assert GenResult("t", "m", None, "default", None, 10, 1, 1, 0.0).truncated is False
    print("providers selftest OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_selftest() if "--selftest" in sys.argv[1:] else 0)
