"""Provider adapters for the Fabricated-Precision pilot eval harness.

Clean-room: fresh code, NO import of the production engine (`system-api/`, `system-engines/`). Standard
official-SDK usage only. Each adapter lazily imports its SDK so a missing provider never breaks the others.

Isolation: keys are read from RESEARCH-scoped env vars (`RESEARCH_<PROVIDER>_API_KEY`), deliberately distinct
from the product's `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, so this harness can never silently spend on
product credentials. No key present → `available()` is False and `generate()` raises; nothing runs until the
operator provisions research keys at PAUSE 2.

Each provider is called at the provider's DEFAULT settings (SPEC §Models). `describe()` returns exactly what
goes into MODEL_SETTINGS.md; `generate()` returns the actual settings used, captured from the live response
where the API exposes them — recorded, never assumed.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


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
    raw_meta: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    name: str
    model_id: str
    def available(self) -> bool: ...
    def describe(self) -> dict[str, Any]: ...            # -> MODEL_SETTINGS.md row
    def generate(self, system: str, user: str, *, max_tokens: int) -> GenResult: ...


class _Base:
    """Shared env-key plumbing. Subclasses set `name`, `env_key`, `model_id` and implement `_call`."""
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

    def generate(self, system: str, user: str, *, max_tokens: int) -> GenResult:
        if not self.available():
            raise RuntimeError(
                f"{self.name}: no research key in ${self.env_key} — provisioned at PAUSE 2, not before.")
        t0 = time.monotonic()
        res = self._call(system, user, max_tokens)
        res.latency_s = round(time.monotonic() - t0, 4)
        return res

    def _call(self, system: str, user: str, max_tokens: int) -> GenResult:  # pragma: no cover
        raise NotImplementedError


class AnthropicProvider(_Base):
    name = "anthropic"
    env_key = "RESEARCH_ANTHROPIC_API_KEY"

    def _call(self, system: str, user: str, max_tokens: int) -> GenResult:
        import anthropic  # lazy
        client = anthropic.Anthropic(api_key=self._key())
        r = client.messages.create(
            model=self.model_id, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in r.content if getattr(b, "type", None) == "text")
        u = getattr(r, "usage", None)
        return GenResult(
            text=text, model_id=getattr(r, "model", self.model_id),
            api_version=None, temperature="default", reasoning_mode=self.reasoning_mode,
            max_output_tokens=max_tokens,
            input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None),
            latency_s=0.0, raw_meta={"stop_reason": getattr(r, "stop_reason", None)})


class OpenAIProvider(_Base):
    name = "openai"
    env_key = "RESEARCH_OPENAI_API_KEY"

    def _call(self, system: str, user: str, max_tokens: int) -> GenResult:
        from openai import OpenAI  # lazy
        client = OpenAI(api_key=self._key())
        # Responses API; some models fix temperature/ignore it — recorded as supplied, not assumed.
        r = client.responses.create(
            model=self.model_id, max_output_tokens=max_tokens,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        text = getattr(r, "output_text", "") or ""
        u = getattr(r, "usage", None)
        return GenResult(
            text=text, model_id=getattr(r, "model", self.model_id),
            api_version=None, temperature="default", reasoning_mode=self.reasoning_mode,
            max_output_tokens=max_tokens,
            input_tokens=getattr(u, "input_tokens", None), output_tokens=getattr(u, "output_tokens", None),
            latency_s=0.0, raw_meta={})


class GoogleProvider(_Base):
    name = "google"
    env_key = "RESEARCH_GOOGLE_API_KEY"   # net-new per 02888/02894; no product equivalent exists

    def _call(self, system: str, user: str, max_tokens: int) -> GenResult:
        from google import genai  # lazy; `google-genai` SDK (net-new dependency)
        from google.genai import types
        client = genai.Client(api_key=self._key())
        r = client.models.generate_content(
            model=self.model_id, contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=max_tokens))
        text = getattr(r, "text", "") or ""
        um = getattr(r, "usage_metadata", None)
        return GenResult(
            text=text, model_id=self.model_id, api_version=None,
            temperature="default", reasoning_mode=self.reasoning_mode, max_output_tokens=max_tokens,
            input_tokens=getattr(um, "prompt_token_count", None),
            output_tokens=getattr(um, "candidates_token_count", None),
            latency_s=0.0, raw_meta={})


# Roster: opaque keys (m1…m4) → provider. Real model ids are pinned at runtime into MODEL_SETTINGS.md
# BEFORE the full run (SPEC §Models: "confirmed at runtime"); the placeholders below are intentionally
# unset so nothing runs against an unpinned/guessed id.
def build_roster(model_ids: dict[str, str]) -> dict[str, Provider]:
    """`model_ids` maps roster key -> exact pinned model id, e.g.
    {"m1": "<anthropic-flagship>", "m2": "<anthropic-smallest>", "m3": "<openai-flagship>", "m4": "<google-flagship>"}
    sourced from MODEL_SETTINGS.md. Keys are opaque so downstream code can't infer the model from the key."""
    ctor = {"m1": AnthropicProvider, "m2": AnthropicProvider, "m3": OpenAIProvider, "m4": GoogleProvider}
    return {k: ctor[k](model_ids[k]) for k in ctor if model_ids.get(k)}
