#!/usr/bin/env python3
"""Prepare a TeX, Markdown, or PDF math paper for statement-level review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


STATEMENT_ENV_RE = re.compile(
    r"\\begin\{("
    r"theorem|thm|lemma|lem|proposition|prop|corollary|cor|claim|definition|defn|"
    r"conjecture|question|remark|rem|example|examples"
    r")\}",
    re.IGNORECASE,
)
SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]*)\}")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SECTION_NUMBER_RE = re.compile(r"^\s*((?:\d+\.)*\d+)(?:[.)])?\s*(.*)$")
TEXT_STATEMENT_RE = re.compile(
    r"^\s*(Theorem|Lemma|Proposition|Corollary|Claim|Definition|Conjecture|Remark|Example)"
    r"\b[ .:\-\w()]*",
    re.IGNORECASE,
)


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_numbered_text(text: str, path: Path) -> None:
    lines = text.splitlines()
    path.write_text(
        "\n".join(f"L{index:06d}: {line}" for index, line in enumerate(lines, start=1))
        + "\n",
        encoding="utf-8",
    )


def chunk_tex(lines: list[str]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_section = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        section = SECTION_RE.search(line)
        if section:
            current_section = section.group(2).strip()

        match = STATEMENT_ENV_RE.search(line)
        if not match:
            index += 1
            continue

        env = match.group(1)
        start = index + 1
        end_re = re.compile(rf"\\end\{{{re.escape(env)}\}}", re.IGNORECASE)
        block = [line]
        index += 1
        while index < len(lines):
            block.append(lines[index])
            if end_re.search(lines[index]):
                break
            index += 1
        end = min(index + 1, len(lines))
        block_text = "\n".join(block)
        label_match = LABEL_RE.search(block_text)
        chunks.append(
            {
                "chunk_id": f"chunk_{len(chunks) + 1:04d}",
                "kind": env.lower(),
                "label": label_match.group(1) if label_match else "",
                "section": current_section,
                "start_line": start,
                "end_line": end,
                "location_style": "line",
                "location": f"Line {start}" if start == end else f"Lines {start}--{end}",
                "text": block_text,
            }
        )
        index += 1
    return chunks


def markdown_section_info(level: int, raw_title: str) -> dict[str, Any]:
    title = re.sub(r"\s+", " ", raw_title.strip()).strip()
    match = SECTION_NUMBER_RE.match(title)
    section_id = match.group(1) if match else ""
    section_name = match.group(2).strip() if match else title
    display_name = section_name or title
    kind = "Section" if level <= 1 else "Subsection"

    if section_id and display_name:
        location = f"{kind} {section_id} ({display_name})"
    elif section_id:
        location = f"{kind} {section_id}"
    elif display_name:
        location = f"{kind} {display_name}"
    else:
        location = "Unlabeled section"

    return {
        "section": display_name,
        "section_id": section_id,
        "section_level": level,
        "location": location,
    }


def markdown_section_map(lines: list[str]) -> list[dict[str, Any]]:
    current = {
        "section": "",
        "section_id": "",
        "section_level": 0,
        "location": "Unlabeled section",
    }
    sections: list[dict[str, Any]] = []
    for line in lines:
        heading = MARKDOWN_HEADING_RE.match(line)
        if heading:
            current = markdown_section_info(len(heading.group(1)), heading.group(2))
        sections.append(dict(current))
    return sections


def location_fields(
    *,
    location_style: str,
    start_line: int,
    end_line: int,
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    if location_style == "section":
        section = sections[start_line - 1] if sections else {}
        return {
            "location_style": "section",
            "location": section.get("location", "Unlabeled section"),
            "section": section.get("section", ""),
            "section_id": section.get("section_id", ""),
            "section_level": section.get("section_level", 0),
        }
    location = f"Line {start_line}" if start_line == end_line else f"Lines {start_line}--{end_line}"
    return {"location_style": "line", "location": location}


def chunk_markdown_or_text(lines: list[str], *, location_style: str = "line") -> list[dict[str, Any]]:
    starts: list[int] = []
    for index, line in enumerate(lines):
        heading = MARKDOWN_HEADING_RE.match(line)
        if heading and TEXT_STATEMENT_RE.search(heading.group(2)):
            starts.append(index)
            continue
        if TEXT_STATEMENT_RE.match(line):
            starts.append(index)

    chunks: list[dict[str, Any]] = []
    sections = markdown_section_map(lines) if location_style == "section" else []
    for pos, start_index in enumerate(starts):
        end_index = starts[pos + 1] - 1 if pos + 1 < len(starts) else len(lines) - 1
        text = "\n".join(lines[start_index : end_index + 1]).strip()
        heading = text.splitlines()[0] if text else "statement"
        start_line = start_index + 1
        end_line = end_index + 1
        chunks.append(
            {
                "chunk_id": f"chunk_{len(chunks) + 1:04d}",
                "kind": "statement",
                "label": "",
                "start_line": start_line,
                "end_line": end_line,
                "text": text,
                "heading": heading,
                **location_fields(
                    location_style=location_style,
                    start_line=start_line,
                    end_line=end_line,
                    sections=sections,
                ),
            }
        )
    return chunks


def fallback_paragraph_chunks(lines: list[str], *, location_style: str = "line") -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    start: int | None = None
    buffer: list[str] = []
    sections = markdown_section_map(lines) if location_style == "section" else []
    for index, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = index
            buffer.append(line)
            continue
        if start is not None and buffer:
            chunks.append(
                {
                    "chunk_id": f"chunk_{len(chunks) + 1:04d}",
                    "kind": "paragraph",
                    "label": "",
                    "start_line": start,
                    "end_line": index - 1,
                    "text": "\n".join(buffer),
                    **location_fields(
                        location_style=location_style,
                        start_line=start,
                        end_line=index - 1,
                        sections=sections,
                    ),
                }
            )
        start = None
        buffer = []
    if start is not None and buffer:
        chunks.append(
            {
                "chunk_id": f"chunk_{len(chunks) + 1:04d}",
                "kind": "paragraph",
                "label": "",
                "start_line": start,
                "end_line": len(lines),
                "text": "\n".join(buffer),
                **location_fields(
                    location_style=location_style,
                    start_line=start,
                    end_line=len(lines),
                    sections=sections,
                ),
            }
        )
    return chunks


def write_chunks(chunks: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def extract_pdf(
    path: Path,
    output_dir: Path,
    *,
    allow_text_fallback: bool = False,
    mistral_api_key: str = "",
    mistral_api_key_file: str = "",
    mistral_model: str = "mistral-ocr-latest",
) -> tuple[str, list[str]]:
    notes: list[str] = []
    markdown_path = output_dir / "paper_ocr.md"
    mistral_dir = output_dir / "mistral_ocr"
    mistral_script = Path(__file__).resolve().with_name("mistral_pdf_to_markdown.py")
    markdown_path.unlink(missing_ok=True)
    for stale_fallback in (
        output_dir / "paper_pdf_text_fallback.txt",
        output_dir / "paper_pdftotext.txt",
    ):
        stale_fallback.unlink(missing_ok=True)

    cmd = [
        sys.executable,
        str(mistral_script),
        "--input",
        str(path),
        "--output-dir",
        str(mistral_dir),
        "--markdown-output",
        str(markdown_path),
        "--model",
        mistral_model,
    ]
    if mistral_api_key:
        cmd.extend(["--api-key", mistral_api_key])
    if mistral_api_key_file:
        cmd.extend(["--api-key-file", mistral_api_key_file])

    code, output = run_command(cmd)
    notes.append("Ran Mistral OCR-to-Markdown.")
    notes.append(output.strip())
    if markdown_path.is_file() and markdown_path.stat().st_size > 0:
        if code != 0:
            notes.append(
                "Mistral OCR helper returned a nonzero exit code but produced paper_ocr.md; "
                "using the Markdown output and skipping embedded PDF text fallback."
            )
        notes.append("Using paper_ocr.md as the source for paper_source.txt and all later processing.")
        return read_text_file(markdown_path), notes

    notes.append(
        f"Mistral OCR failed with exit code {code} and did not produce a non-empty paper_ocr.md."
    )
    if not allow_text_fallback:
        raise RuntimeError(
            "Mistral OCR-to-Markdown failed. Set MISTRAL_API_KEY, pass --mistral-api-key-file, "
            "or rerun with --allow-pdf-text-fallback if embedded PDF text is acceptable."
        )

    notes.append("Using embedded PDF text fallback because --allow-pdf-text-fallback was set.")
    extracted_txt = output_dir / "paper_pdf_text_fallback.txt"
    if shutil.which("pdftotext"):
        code, output = run_command(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(path), str(extracted_txt)]
        )
        if code != 0:
            notes.append(f"pdftotext failed with exit code {code}:\n{output}")
        elif extracted_txt.exists():
            return read_text_file(extracted_txt), notes
    else:
        notes.append("pdftotext is not installed; PDF text extraction failed.")

    raise RuntimeError(
        "Could not extract PDF text. Configure Mistral OCR or provide TeX/Markdown."
    )


def load_input(
    path: Path,
    output_dir: Path,
    *,
    allow_pdf_text_fallback: bool = False,
    mistral_api_key: str = "",
    mistral_api_key_file: str = "",
    mistral_model: str = "mistral-ocr-latest",
) -> tuple[str, str, list[str]]:
    suffix = path.suffix.lower()
    notes: list[str] = []
    if suffix in {".tex", ".ltx"}:
        return read_text_file(path), "tex", notes
    if suffix in {".md", ".markdown", ".txt"}:
        return read_text_file(path), "markdown", notes
    if suffix == ".pdf":
        text, notes = extract_pdf(
            path,
            output_dir,
            allow_text_fallback=allow_pdf_text_fallback,
            mistral_api_key=mistral_api_key,
            mistral_api_key_file=mistral_api_key_file,
            mistral_model=mistral_model,
        )
        return text, "markdown", notes
    raise ValueError(f"Unsupported input extension: {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a math paper for review.")
    parser.add_argument("--input", "-i", required=True, help="Path to .tex, .md, .txt, or .pdf")
    parser.add_argument("--output-dir", "-o", required=True, help="Review output directory")
    parser.add_argument(
        "--allow-pdf-text-fallback",
        action="store_true",
        help="For PDFs, allow embedded text extraction if Mistral OCR is unavailable or fails.",
    )
    parser.add_argument("--mistral-api-key", help="Mistral API key. Prefer MISTRAL_API_KEY.")
    parser.add_argument("--mistral-api-key-file", help="File containing Mistral API key")
    parser.add_argument("--mistral-model", default="mistral-ocr-latest")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    location_style = "section" if input_path.suffix.lower() == ".pdf" else "line"

    try:
        text, input_kind, notes = load_input(
            input_path,
            output_dir,
            allow_pdf_text_fallback=args.allow_pdf_text_fallback,
            mistral_api_key=args.mistral_api_key or "",
            mistral_api_key_file=args.mistral_api_key_file or "",
            mistral_model=args.mistral_model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"prepare_paper.py: {exc}", file=sys.stderr)
        return 1

    source_path = output_dir / "paper_source.txt"
    numbered_path = output_dir / "paper_numbered.txt"
    chunks_path = output_dir / "paper_chunks.jsonl"
    notes_path = output_dir / "extraction_notes.md"
    meta_path = output_dir / "paper_meta.json"

    source_path.write_text(text, encoding="utf-8")
    write_numbered_text(text, numbered_path)

    lines = text.splitlines()
    if input_kind == "tex":
        chunks = chunk_tex(lines)
    else:
        chunks = chunk_markdown_or_text(lines, location_style=location_style)
    if not chunks:
        chunks = fallback_paragraph_chunks(lines, location_style=location_style)
    write_chunks(chunks, chunks_path)

    notes_path.write_text(
        "# Extraction Notes\n\n" + "\n".join(f"- {note}" for note in notes) + "\n",
        encoding="utf-8",
    )
    meta = {
        "input_path": str(input_path),
        "input_kind": input_kind,
        "sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
        "location_style": location_style,
        "line_count": len(lines),
        "chunk_count": len(chunks),
        "paper_source": str(source_path),
        "paper_numbered": str(numbered_path),
        "paper_chunks": str(chunks_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
