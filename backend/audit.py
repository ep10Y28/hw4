"""Append-only audit trail of agent-loop activity (Problem 12).

File: output/audit_trail.json, a JSON array that only ever grows.
  - Each chat turn appends entries, and nothing is edited or removed.
  - Writes are atomic: read the array, append, write to a temp file, then
    os.replace(), so a crash mid-write can't leave a half-written file.
  - If the file is ever unreadable, it is moved aside to
    audit_trail.corrupt-<time>.json (kept, not deleted) and a fresh array starts.

One entry per agent-loop iteration (each model response), plus a
"turn_start" and "turn_end" entry per chat message:

  {
    "time": "2026-10-24T02:51:07Z",       UTC, ISO 8601
    "run_id": "a1b2c3d4",                  ties a turn's entries together
    "event": "model_step",                 turn_start | model_step | turn_end | guardrail
    "user": "user:4" | "guest",            never an email or name
    "step": 1,                             iteration number within the run
    "model": "gpt-5.6-terra",
    "tool_calls": [{"tool": "check_stock", "args": "{\"product_id\": ...}"}],
    "tool_results": [{"tool": "check_stock", "result": "{\"requested_size\": \"M\", ...}"}],
    "stop_reason": "tool_call" | "final_result" | "retry" | "usage_limit" | "error" | "blocked",
                                           (turn_end also has model_requests, tool_call_count, tokens, duration_ms)
    "tokens": {"input": 1234, "output": 56}
  }

Args and results are cut to 300 characters. Shopper messages are logged
after the safety guardrail has redacted them.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
MAX_FIELD = 300

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short(value: Any, limit: int = MAX_FIELD) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    elif isinstance(value, list):
        value = [v.model_dump() if hasattr(v, "model_dump") else v for v in value]
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def append(entries: list[dict], path: Path = AUDIT_PATH) -> None:
    """Append entries to the audit file. Never removes or rewrites old entries."""
    if not entries:
        return
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    raise ValueError("audit file is not a JSON array")
            except (ValueError, json.JSONDecodeError):
                stamp = time.strftime("%Y%m%d-%H%M%S")
                path.replace(path.with_name(f"audit_trail.corrupt-{stamp}.json"))
                existing = []
        existing.extend(entries)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def steps_from_messages(messages: list, run_id: str, user: str, model_name: str) -> list[dict]:
    """One entry per model response in this run, with the tool results that came back for it."""
    entries: list[dict] = []
    step = 0
    for i, msg in enumerate(messages):
        if not isinstance(msg, ModelResponse):
            continue
        step += 1
        calls = [p for p in msg.parts if isinstance(p, ToolCallPart)]
        # Results for these calls arrive in the next request message.
        results: list[dict] = []
        retried = False
        nxt = messages[i + 1] if i + 1 < len(messages) else None
        if isinstance(nxt, ModelRequest):
            for p in nxt.parts:
                if isinstance(p, ToolReturnPart):
                    results.append({"tool": p.tool_name, "result": short(p.content)})
                elif isinstance(p, RetryPromptPart):
                    retried = True
                    results.append({"tool": p.tool_name or "(output)", "result": "RETRY: " + short(p.content, 200)})
        final = any(c.tool_name.startswith("final_result") for c in calls)
        if retried:
            stop = "retry"
        elif nxt is None or final:
            stop = "final_result"
        elif calls:
            stop = "tool_call"
        else:
            stop = getattr(msg, "finish_reason", None) or "text"
        usage = getattr(msg, "usage", None)
        entries.append(
            {
                "time": _now(),
                "run_id": run_id,
                "event": "model_step",
                "user": user,
                "step": step,
                "model": getattr(msg, "model_name", None) or model_name,
                "tool_calls": [{"tool": c.tool_name, "args": short(c.args)} for c in calls],
                "tool_results": results,
                "text": short(" ".join(p.content for p in msg.parts if isinstance(p, TextPart)), 200) or None,
                "stop_reason": stop,
                "tokens": {
                    "input": getattr(usage, "input_tokens", None),
                    "output": getattr(usage, "output_tokens", None),
                },
            }
        )
    return entries


def event(run_id: str, user: str, name: str, **fields: Any) -> dict:
    return {"time": _now(), "run_id": run_id, "event": name, "user": user, **fields}
