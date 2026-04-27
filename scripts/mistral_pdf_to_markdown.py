#!/usr/bin/env python3
"""Convert a PDF to Markdown through Mistral OCR."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def require_mistral():
    try:
        from mistralai import Mistral  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The Mistral OCR helper requires mistralai. Install it with: pip install mistralai"
        ) from exc
    return Mistral


def api_key_from_args(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key.strip()
    if args.api_key_file:
        return Path(args.api_key_file).read_text(encoding="utf-8").strip()
    key = os.environ.get(args.api_key_env, "").strip()
    if key:
        return key
    raise RuntimeError(
        f"Mistral API key not found. Set {args.api_key_env}, pass --api-key-file, or pass --api-key."
    )


def page_markdown(page: Any) -> str:
    markdown = getattr(page, "markdown", None)
    if markdown is None and isinstance(page, dict):
        markdown = page.get("markdown")
    return str(markdown or "")


def file_id(uploaded: Any) -> str:
    value = getattr(uploaded, "id", None)
    if value is None and isinstance(uploaded, dict):
        value = uploaded.get("id")
    if not value:
        raise RuntimeError("Mistral file upload did not return a file id")
    return str(value)


def response_pages(response: Any) -> list[Any]:
    pages = getattr(response, "pages", None)
    if pages is None and isinstance(response, dict):
        pages = response.get("pages")
    if pages is None:
        raise RuntimeError("Mistral OCR response did not include pages")
    return list(pages)


def convert_pdf_to_markdown(args: argparse.Namespace) -> dict[str, Any]:
    pdf_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    markdown_output = (
        Path(args.markdown_output).resolve() if args.markdown_output else output_dir / "full.md"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    Mistral = require_mistral()
    client = Mistral(api_key=api_key_from_args(args))

    with pdf_path.open("rb") as handle:
        uploaded = client.files.upload(
            file={"file_name": pdf_path.name, "content": handle},
            purpose="ocr",
        )

    uploaded_id = file_id(uploaded)
    response = client.ocr.process(
        model=args.model,
        document={"file_id": uploaded_id},
    )
    pages = response_pages(response)

    chunks: list[str] = []
    for index, page in enumerate(pages, start=1):
        markdown = page_markdown(page)
        if args.page_headings:
            chunks.append(f"### Page {index}\n{markdown}".rstrip())
        else:
            chunks.append(markdown.rstrip())

    markdown_text = "\n\n".join(chunk for chunk in chunks if chunk).rstrip() + "\n"
    markdown_output.write_text(markdown_text, encoding="utf-8")

    result = {
        "uploaded_file_id": uploaded_id,
        "model": args.model,
        "page_count": len(pages),
        "markdown_output": str(markdown_output),
    }
    (output_dir / "mistral_ocr_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR a PDF to Markdown with Mistral OCR.")
    parser.add_argument("--input", "-i", required=True, help="Input PDF path")
    parser.add_argument("--output-dir", "-o", required=True, help="Directory for Mistral OCR metadata")
    parser.add_argument("--markdown-output", help="Final markdown path to write")
    parser.add_argument("--api-key", help="Mistral API key. Prefer MISTRAL_API_KEY or --api-key-file.")
    parser.add_argument("--api-key-file", help="File containing the Mistral API key")
    parser.add_argument("--api-key-env", default="MISTRAL_API_KEY")
    parser.add_argument("--model", default="mistral-ocr-latest")
    parser.add_argument("--no-page-headings", dest="page_headings", action="store_false")
    parser.set_defaults(page_headings=True)
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
