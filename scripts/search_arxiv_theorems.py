#!/usr/bin/env python3
"""Query the arXiv theorem-search API hosted at leansearch.net."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


THEOREM_SEARCH_URL = "https://leansearch.net/thm/search"
THEOREM_SEARCH_TASK = (
    "Given a math statement, retrieve useful references, such as theorems, "
    "lemmas, and definitions, that are useful for solving the given problem."
)


def search_arxiv_theorems(
    query: str,
    num_results: int = 10,
    endpoint: str = THEOREM_SEARCH_URL,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("query must be non-empty")
    if num_results <= 0:
        raise ValueError("num_results must be > 0")

    payload = {
        "query": query,
        "task": THEOREM_SEARCH_TASK,
        "num_results": num_results,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8")

    data = json.loads(response_body)
    if not isinstance(data, list):
        raise ValueError("The theorem endpoint must return a JSON list")

    normalized: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "")),
                "theorem": str(item.get("theorem", "")),
                "arxiv_id": str(item.get("arxiv_id", "")),
                "theorem_id": str(item.get("theorem_id", "")),
            }
        )

    return {
        "query": query,
        "count": len(normalized),
        "results": normalized,
        "endpoint": endpoint,
    }


def read_query(args: argparse.Namespace) -> str:
    if args.query:
        return args.query
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    raise ValueError("provide --query or pipe query text on stdin")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search arXiv theorem references from the leansearch.net endpoint.",
    )
    parser.add_argument("--query", "-q", help="Mathematical statement or search query")
    parser.add_argument("--num-results", "-n", type=int, default=10)
    parser.add_argument("--endpoint", default=THEOREM_SEARCH_URL)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args()

    try:
        result = search_arxiv_theorems(
            query=read_query(args),
            num_results=args.num_results,
            endpoint=args.endpoint,
            timeout_seconds=args.timeout_seconds,
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.compact:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
