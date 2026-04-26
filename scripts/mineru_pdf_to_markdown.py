#!/usr/bin/env python3
"""Convert a PDF to Markdown through the MinerU OCR API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any


API_BASE = "https://mineru.net/api/v4"


def require_requests():
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("The MinerU OCR helper requires requests. Install it with: pip install requests") from exc
    return requests


def sanitize_data_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "paper"


def token_from_args(args: argparse.Namespace) -> str:
    if args.token:
        return args.token.strip()
    if args.token_file:
        return Path(args.token_file).read_text(encoding="utf-8").strip()
    token = os.environ.get(args.token_env, "").strip()
    if token:
        return token
    raise RuntimeError(
        f"MinerU API token not found. Set {args.token_env}, pass --token-file, or pass --token."
    )


def check_json_response(resp: Any, name: str) -> dict[str, Any]:
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"{name} failed: {result}")
    return result


def apply_upload_url(
    *,
    token: str,
    pdf_path: Path,
    data_id: str,
    model_version: str,
    enable_formula: bool,
    enable_table: bool,
    request_timeout: int,
) -> tuple[str, str]:
    requests = require_requests()
    url = f"{API_BASE}/file-urls/batch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "files": [
            {
                "name": pdf_path.name,
                "data_id": data_id,
                "is_ocr": True,
            }
        ],
        "model_version": model_version,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
    }
    result = check_json_response(
        requests.post(url, headers=headers, json=payload, timeout=request_timeout),
        "apply_upload_url",
    )
    return result["data"]["batch_id"], result["data"]["file_urls"][0]


def upload_file(upload_url: str, pdf_path: Path, request_timeout: int) -> None:
    requests = require_requests()
    with pdf_path.open("rb") as handle:
        resp = requests.put(upload_url, data=handle, timeout=request_timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Upload failed: {resp.status_code}, {resp.text[:500]}")


def wait_batch_result(
    *,
    token: str,
    batch_id: str,
    poll_interval: int,
    timeout_seconds: int,
    request_timeout: int,
) -> str:
    requests = require_requests()
    url = f"{API_BASE}/extract-results/batch/{batch_id}"
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + timeout_seconds

    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(f"MinerU batch timed out after {timeout_seconds} seconds")

        result = check_json_response(
            requests.get(url, headers=headers, timeout=request_timeout),
            "query_result",
        )
        items = result["data"]["extract_result"]
        if not items:
            raise RuntimeError("MinerU returned no extract_result items")
        item = items[0]
        state = item["state"]

        if state == "done":
            return item["full_zip_url"]
        if state == "failed":
            raise RuntimeError(f"MinerU parse failed: {item.get('err_msg')}")

        time.sleep(poll_interval)


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    base = extract_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if base not in target.parents and target != base:
                raise RuntimeError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(extract_dir)


def download_and_extract(
    zip_url: str,
    output_dir: Path,
    data_id: str,
    request_timeout: int,
) -> tuple[Path, Path]:
    requests = require_requests()
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{data_id}_mineru.zip"
    extract_dir = output_dir / data_id

    resp = requests.get(zip_url, timeout=request_timeout)
    resp.raise_for_status()
    zip_path.write_bytes(resp.content)
    safe_extract_zip(zip_path, extract_dir)
    return zip_path, extract_dir


def find_full_markdown(extract_dir: Path) -> Path:
    candidates = sorted(extract_dir.rglob("full.md"))
    if not candidates:
        raise RuntimeError(f"MinerU output did not contain full.md under {extract_dir}")
    return candidates[0]


def convert_pdf_to_markdown(args: argparse.Namespace) -> dict[str, Any]:
    pdf_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    markdown_output = Path(args.markdown_output).resolve() if args.markdown_output else output_dir / "full.md"
    digest = hashlib.sha256(str(pdf_path).encode("utf-8")).hexdigest()[:8]
    data_id = sanitize_data_id(args.data_id or f"{pdf_path.stem}_{digest}")
    token = token_from_args(args)

    batch_id, upload_url = apply_upload_url(
        token=token,
        pdf_path=pdf_path,
        data_id=data_id,
        model_version=args.model_version,
        enable_formula=not args.disable_formula,
        enable_table=not args.disable_table,
        request_timeout=args.request_timeout,
    )
    upload_file(upload_url, pdf_path, args.request_timeout)
    zip_url = wait_batch_result(
        token=token,
        batch_id=batch_id,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout_seconds,
        request_timeout=args.request_timeout,
    )
    zip_path, extract_dir = download_and_extract(zip_url, output_dir, data_id, args.request_timeout)
    full_md = find_full_markdown(extract_dir)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_md, markdown_output)

    result = {
        "batch_id": batch_id,
        "data_id": data_id,
        "zip_path": str(zip_path),
        "extract_dir": str(extract_dir),
        "mineru_full_md": str(full_md),
        "markdown_output": str(markdown_output),
    }
    (output_dir / "mineru_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR a PDF to Markdown with MinerU.")
    parser.add_argument("--input", "-i", required=True, help="Input PDF path")
    parser.add_argument("--output-dir", "-o", required=True, help="Directory for MinerU zip/output")
    parser.add_argument("--markdown-output", help="Final markdown path to write")
    parser.add_argument("--token", help="MinerU API token. Prefer MINERU_API_TOKEN or --token-file.")
    parser.add_argument("--token-file", help="File containing MinerU API token")
    parser.add_argument("--token-env", default="MINERU_API_TOKEN")
    parser.add_argument("--data-id", help="Optional MinerU data_id")
    parser.add_argument("--model-version", default="vlm")
    parser.add_argument("--disable-formula", action="store_true")
    parser.add_argument("--disable-table", action="store_true")
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--request-timeout", type=int, default=1200)
    args = parser.parse_args()

    try:
        result = convert_pdf_to_markdown(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), flush=True)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
