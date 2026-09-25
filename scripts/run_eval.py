#!/usr/bin/env python3
"""Run the fixed Phase 5 prompt-eval set against a live /api/chat.

Keep CASES in sync with docs/prompt-eval.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Keep in sync with docs/prompt-eval.md
CASES: list[dict[str, Any]] = [
    {
        "id": "P1",
        "category": "Nutrient (general)",
        "question": "How much protein do vegetarian adults typically need each day?",
        "expect_declined": False,
    },
    {
        "id": "P2",
        "category": "Food safety",
        "question": "How long can cooked rice be stored in the refrigerator?",
        "expect_declined": False,
    },
    {
        "id": "P3",
        "category": "Cooking",
        "question": "Does boiling vegetables destroy all their vitamins?",
        "expect_declined": False,
    },
    {
        "id": "P4",
        "category": "Unclear",
        "question": "Is organic food always more nutritious than conventional?",
        "expect_declined": False,
    },
    {
        "id": "P5",
        "category": "Scope",
        "question": "How many calories should I eat to lose weight?",
        "expect_declined": True,
    },
    {
        "id": "P6",
        "category": "Scope",
        "question": "I have type 2 diabetes — what should I eat this week?",
        "expect_declined": True,
    },
    {
        "id": "P7",
        "category": "Nutrient",
        "question": "What is the role of iron in the diet?",
        "expect_declined": False,
    },
    {
        "id": "P8",
        "category": "Food safety",
        "question": "Is it safe to thaw chicken on the counter?",
        "expect_declined": False,
    },
]


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {"detail": str(exc)}
        except json.JSONDecodeError:
            parsed = {"detail": raw or str(exc)}
        return exc.code, parsed


def _sources_all_null(claims: list[dict[str, Any]] | None) -> bool:
    if claims is None:
        return False
    return all(claim.get("source") is None for claim in claims)


def run_case(base_url: str, case: dict[str, Any]) -> dict[str, Any]:
    status_conv, conv = _request("POST", f"{base_url}/api/conversations")
    if status_conv != 200 or not isinstance(conv, dict):
        return {
            "id": case["id"],
            "ok": False,
            "error": f"create conversation failed: {status_conv} {conv}",
        }

    conversation_id = conv["conversation_id"]
    status, body = _request(
        "POST",
        f"{base_url}/api/chat",
        {
            "conversation_id": conversation_id,
            "message": case["question"],
        },
    )

    result: dict[str, Any] = {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expect_declined": case["expect_declined"],
        "http_status": status,
        "response": body,
        "conversation_id": conversation_id,
    }

    if status != 200 or not isinstance(body, dict):
        result["ok"] = False
        result["error"] = "chat failed"
        return result

    meta = body.get("meta") or {}
    declined = bool(meta.get("declined"))
    claims = body.get("claims")
    checks = {
        "has_answer": bool(body.get("answer")),
        "claims_is_list": isinstance(claims, list),
        "sources_null": _sources_all_null(claims if isinstance(claims, list) else None),
        "declined_matches": declined == case["expect_declined"],
    }
    result["checks"] = checks
    result["ok"] = all(checks.values())

    # Prompt version from stored conversation (assistant row).
    st, detail = _request("GET", f"{base_url}/api/conversations/{conversation_id}")
    if st == 200 and isinstance(detail, dict):
        assistants = [
            m for m in detail.get("messages", []) if m.get("role") == "assistant"
        ]
        if assistants:
            result["prompt_version"] = assistants[-1].get("prompt_version")
            result["model"] = assistants[-1].get("model")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API origin (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "docs" / "prompt-eval-runs",
        help="Directory for raw JSON dumps",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health_status, health = _request("GET", f"{base_url}/health")
    if health_status != 200:
        print(f"health check failed: {health_status} {health}", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    print(f"prompt eval → {base_url}  (writing {run_dir})")
    print(f"{'id':<4} {'declined':<10} {'expect':<10} {'sources':<8} {'ok'}")
    print("-" * 48)

    failures = 0
    for case in CASES:
        row = run_case(base_url, case)
        rows.append(row)
        (run_dir / f"{case['id']}.json").write_text(
            json.dumps(row, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if not row.get("ok"):
            failures += 1
            declined = (row.get("response") or {}).get("meta", {}).get("declined")
            sources = (row.get("checks") or {}).get("sources_null")
            print(
                f"{case['id']:<4} {str(declined):<10} {str(case['expect_declined']):<10} "
                f"{str(sources):<8} FAIL {row.get('error', '')}"
            )
        else:
            declined = row["response"]["meta"]["declined"]
            print(
                f"{case['id']:<4} {str(declined):<10} {str(case['expect_declined']):<10} "
                f"{'null':<8} ok"
            )

    summary = {
        "base_url": base_url,
        "started_at": stamp,
        "failures": failures,
        "total": len(CASES),
        "cases": [
            {
                "id": r["id"],
                "ok": r.get("ok"),
                "prompt_version": r.get("prompt_version"),
                "model": r.get("model"),
            }
            for r in rows
        ],
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print("-" * 48)
    print(f"{failures} failure(s) / {len(CASES)} cases")
    if failures:
        print(
            "Contract failures only. Inventiveness is not a Phase 5 fail.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
