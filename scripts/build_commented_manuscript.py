#!/usr/bin/env python3
"""Build a manuscript-with-comments TeX/PDF from source and review comments."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


COMMENT_MACRO = r"""
% Review comment boxes inserted by paper-reviewing-skills.
\newcounter{prskillcomment}
\newcommand{\prskillcomment}[1]{%
  \refstepcounter{prskillcomment}%
  \par\smallskip
  \noindent\fbox{\begin{minipage}{0.94\linewidth}\textbf{Reviewer comment \theprskillcomment.} #1\end{minipage}}%
  \par\smallskip
}
"""

MATH_RE = re.compile(r"(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^```")
SECTION_NUMBER_RE = re.compile(r"^\s*((?:\d+\.)*\d+)(?:[.)])?\s*(.*)$")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    if not path.exists():
        return comments
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if isinstance(item, dict):
                comments.append(item)
    return comments


def int_field(item: dict[str, Any], *names: str) -> int | None:
    for name in names:
        value = item.get(name)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def latex_escape_preserving_math(text: str) -> str:
    parts = MATH_RE.split(text)
    escaped: list[str] = []
    for part in parts:
        if not part:
            continue
        if MATH_RE.fullmatch(part):
            escaped.append(part)
        else:
            escaped.append(latex_escape(part))
    return "".join(escaped)


def comment_plain_text(item: dict[str, Any]) -> str:
    explicit = str(item.get("comment", "")).strip()
    if explicit:
        return explicit

    parts: list[str] = []
    for label, key in (
        ("Issue", "description"),
        ("Analysis", "analysis"),
        ("Suggested fix", "suggested_fix"),
        ("Counterexample analysis", "counterexample_analysis"),
    ):
        value = str(item.get(key, "")).strip()
        if value:
            parts.append(f"{label}: {value}")
    if parts:
        return " ".join(parts)
    return str(item.get("summary", "Review comment")).strip() or "Review comment"


def comment_markdown(item: dict[str, Any], index: int) -> str:
    location = str(item.get("location", "")).strip()
    issue_type = str(item.get("type", item.get("issue_type", ""))).strip()
    prefix = f"Reviewer comment {index}"
    if location:
        prefix += f" ({location})"
    if issue_type:
        prefix += f" [{issue_type}]"
    return f"> **{prefix}.** {comment_plain_text(item)}"


def comment_latex(item: dict[str, Any], index: int) -> str:
    location = str(item.get("location", "")).strip()
    issue_type = str(item.get("type", item.get("issue_type", ""))).strip()
    chunks: list[str] = []
    if location:
        chunks.append(r"\textit{" + latex_escape_preserving_math(f"Location: {location}") + r"}")
    if issue_type:
        chunks.append(r"\textit{" + latex_escape_preserving_math(f"Type: {issue_type}") + r"}")
    chunks.append(latex_escape_preserving_math(comment_plain_text(item)))
    return r"\prskillcomment{" + r"\par ".join(chunks) + "}"


def insert_comment_macro(tex: str) -> str:
    if r"\newcommand{\prskillcomment}" in tex or r"\newcommand\prskillcomment" in tex:
        return tex
    marker = r"\begin{document}"
    index = tex.find(marker)
    if index == -1:
        return (
            "\\documentclass{amsart}\n"
            "\\usepackage[margin=1in]{geometry}\n"
            "\\usepackage{amsmath,amssymb,amsthm}\n"
            + COMMENT_MACRO
            + "\\begin{document}\n"
            + tex
            + "\n\\end{document}\n"
        )
    return tex[:index] + COMMENT_MACRO + tex[index:]


def end_document_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines, start=1):
        if r"\end{document}" in line:
            return index
    return None


def begin_document_line(lines: list[str]) -> int | None:
    for index, line in enumerate(lines, start=1):
        if r"\begin{document}" in line:
            return index
    return None


def group_comments_for_tex(
    comments: list[dict[str, Any]],
    line_count: int,
    min_target: int = 0,
) -> dict[int, list[tuple[int, dict[str, Any]]]]:
    grouped: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, item in enumerate(comments, start=1):
        target = int_field(item, "insert_after_line", "end_line", "line", "start_line")
        if target is None:
            target = line_count
        target = min(max(target, min_target), line_count)
        grouped[target].append((index, item))
    return grouped


def build_tex_with_comments(source: Path, comments: list[dict[str, Any]], output_tex: Path) -> None:
    tex = source.read_text(encoding="utf-8", errors="replace")
    lines = tex.splitlines(keepends=True)
    end_line = end_document_line(lines)
    begin_line = begin_document_line(lines) or 0
    insertion_limit = (end_line - 1) if end_line else len(lines)
    grouped = group_comments_for_tex(comments, insertion_limit, min_target=begin_line)

    output: list[str] = []
    for index, line in enumerate(lines, start=1):
        if end_line and index == end_line and 0 in grouped:
            for comment_index, item in grouped[0]:
                output.append(comment_latex(item, comment_index) + "\n")
        output.append(line)
        if index <= insertion_limit:
            for comment_index, item in grouped.get(index, []):
                output.append(comment_latex(item, comment_index) + "\n")

    for comment_index, item in grouped.get(0, []):
        if not end_line:
            output.append(comment_latex(item, comment_index) + "\n")

    output_tex.write_text(insert_comment_macro("".join(output)), encoding="utf-8")


def heading_location(raw_title: str, level: int) -> dict[str, str]:
    title = re.sub(r"\s+", " ", raw_title.strip()).strip()
    match = SECTION_NUMBER_RE.match(title)
    section_id = match.group(1) if match else ""
    section_name = match.group(2).strip() if match else title
    display = section_name or title
    kind = "Section" if level <= 1 else "Subsection"
    if section_id and display:
        location = f"{kind} {section_id} ({display})"
    elif section_id:
        location = f"{kind} {section_id}"
    elif display:
        location = f"{kind} {display}"
    else:
        location = "Unlabeled section"
    return {"section_id": section_id, "section": display, "location": location}


def normalize_location(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def markdown_heading_targets(lines: list[str]) -> list[tuple[int, dict[str, str]]]:
    targets: list[tuple[int, dict[str, str]]] = []
    for index, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            targets.append((index, heading_location(match.group(2), len(match.group(1)))))
    return targets


def markdown_target_line(item: dict[str, Any], lines: list[str], headings: list[tuple[int, dict[str, str]]]) -> int:
    target = int_field(item, "insert_after_line", "end_line", "line", "start_line")
    if target is not None:
        return min(max(target, 0), len(lines))

    wanted_values = [
        str(item.get("location", "")),
        str(item.get("section_id", "")),
        str(item.get("section", "")),
    ]
    wanted = [normalize_location(value) for value in wanted_values if normalize_location(value)]
    for line_number, info in headings:
        haystack = normalize_location(
            " ".join([info.get("location", ""), info.get("section_id", ""), info.get("section", "")])
        )
        if any(value and value in haystack for value in wanted):
            return line_number
    return len(lines)


def group_comments_for_markdown(
    comments: list[dict[str, Any]], lines: list[str]
) -> dict[int, list[tuple[int, dict[str, Any]]]]:
    grouped: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    headings = markdown_heading_targets(lines)
    for index, item in enumerate(comments, start=1):
        grouped[markdown_target_line(item, lines, headings)].append((index, item))
    return grouped


def write_markdown_with_comments(
    lines: list[str],
    grouped: dict[int, list[tuple[int, dict[str, Any]]]],
    output_md: Path,
) -> None:
    output: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        output.append(line)
        for comment_index, item in grouped.get(line_number, []):
            output.append("")
            output.append(comment_markdown(item, comment_index))
            output.append("")
    for comment_index, item in grouped.get(0, []):
        output.insert(0, "")
        output.insert(0, comment_markdown(item, comment_index))
    output_md.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def flush_paragraph(output: list[str], paragraph: list[str]) -> None:
    if not paragraph:
        return
    text = " ".join(part.strip() for part in paragraph if part.strip())
    if text:
        output.append(latex_escape_preserving_math(text) + "\n")
    paragraph.clear()


def markdown_to_latex(
    lines: list[str],
    grouped: dict[int, list[tuple[int, dict[str, Any]]]],
    output_tex: Path,
    title: str,
) -> None:
    output = [
        "\\documentclass{amsart}\n",
        "\\usepackage[margin=1in]{geometry}\n",
        "\\usepackage{amsmath,amssymb,amsthm}\n",
        "\\usepackage[T1]{fontenc}\n",
        "\\usepackage[utf8]{inputenc}\n",
        COMMENT_MACRO,
        "\\title{" + latex_escape_preserving_math(title) + "}\n",
        "\\author{}\n",
        "\\date{}\n",
        "\\begin{document}\n",
        "\\maketitle\n\n",
    ]
    paragraph: list[str] = []
    in_verbatim = False
    in_itemize = False

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if FENCE_RE.match(stripped):
            flush_paragraph(output, paragraph)
            if in_itemize:
                output.append("\\end{itemize}\n")
                in_itemize = False
            output.append("\\end{verbatim}\n" if in_verbatim else "\\begin{verbatim}\n")
            in_verbatim = not in_verbatim
        elif in_verbatim:
            output.append(line + "\n")
        elif not stripped:
            flush_paragraph(output, paragraph)
            if in_itemize:
                output.append("\\end{itemize}\n")
                in_itemize = False
        elif (heading := HEADING_RE.match(line)):
            flush_paragraph(output, paragraph)
            if in_itemize:
                output.append("\\end{itemize}\n")
                in_itemize = False
            level = len(heading.group(1))
            command = "section" if level == 1 else "subsection" if level == 2 else "subsubsection"
            output.append(
                f"\\{command}*{{{latex_escape_preserving_math(heading.group(2).strip())}}}\n"
            )
        elif stripped.startswith(("- ", "* ")):
            flush_paragraph(output, paragraph)
            if not in_itemize:
                output.append("\\begin{itemize}\n")
                in_itemize = True
            output.append("\\item " + latex_escape_preserving_math(stripped[2:].strip()) + "\n")
        elif stripped.startswith(">"):
            flush_paragraph(output, paragraph)
            quoted = stripped.lstrip(">").strip()
            output.append(r"\begin{quote}" + "\n")
            output.append(latex_escape_preserving_math(re.sub(r"\*\*(.*?)\*\*", r"\textbf{\1}", quoted)) + "\n")
            output.append(r"\end{quote}" + "\n")
        else:
            paragraph.append(line)

        for comment_index, item in grouped.get(line_number, []):
            flush_paragraph(output, paragraph)
            if in_itemize:
                output.append("\\end{itemize}\n")
                in_itemize = False
            output.append(comment_latex(item, comment_index) + "\n")

    flush_paragraph(output, paragraph)
    if in_itemize:
        output.append("\\end{itemize}\n")
    if in_verbatim:
        output.append("\\end{verbatim}\n")
    for comment_index, item in grouped.get(0, []):
        output.append(comment_latex(item, comment_index) + "\n")
    output.append("\\end{document}\n")
    output_tex.write_text("".join(output), encoding="utf-8")


def build_markdown_with_comments(source: Path, comments: list[dict[str, Any]], output_md: Path, output_tex: Path) -> None:
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    grouped = group_comments_for_markdown(comments, lines)
    write_markdown_with_comments(lines, grouped, output_md)
    markdown_to_latex(lines, grouped, output_tex, "Manuscript with Review Comments")


def compile_tex(
    compile_script: Path,
    tex_path: Path,
    output_dir: Path,
    search_dir: Path | None = None,
) -> tuple[str | None, str | None]:
    env = os.environ.copy()
    if search_dir is not None:
        for name in ("TEXINPUTS", "BIBINPUTS"):
            existing = env.get(name, "")
            env[name] = f"{search_dir}//:{existing}" if existing else f"{search_dir}//:"
    completed = subprocess.run(
        [str(compile_script), str(tex_path), str(output_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        return None, completed.stdout
    pdf_path = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    return pdf_path or None, None


def source_format_from_path(path: Path) -> str:
    return "tex" if path.suffix.lower() in {".tex", ".ltx"} else "markdown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a commented manuscript TeX/PDF.")
    parser.add_argument("--source", required=True, help="Original TeX source or OCR Markdown source")
    parser.add_argument("--comments", required=True, help="review_comments.jsonl path")
    parser.add_argument("--output-dir", required=True, help="Directory for manuscript_with_comments outputs")
    parser.add_argument("--source-format", choices=["auto", "tex", "markdown"], default="auto")
    parser.add_argument("--compile-script", default=str(Path(__file__).resolve().with_name("compile_latex.sh")))
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    comments_path = Path(args.comments).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    comments = read_jsonl(comments_path)
    source_format = source_format_from_path(source) if args.source_format == "auto" else args.source_format
    output_tex = output_dir / "manuscript_with_comments.tex"
    output_md = output_dir / "manuscript_with_comments.md"

    if source_format == "tex":
        build_tex_with_comments(source, comments, output_tex)
        output_md = None  # type: ignore[assignment]
    else:
        build_markdown_with_comments(source, comments, output_md, output_tex)

    result: dict[str, Any] = {
        "source": str(source),
        "comments": str(comments_path),
        "comment_count": len(comments),
        "source_format": source_format,
        "manuscript_tex": str(output_tex),
    }
    if output_md is not None:
        result["manuscript_markdown"] = str(output_md)

    if not args.no_compile:
        pdf_path, compile_error = compile_tex(
            Path(args.compile_script).resolve(),
            output_tex,
            output_dir,
            source.parent,
        )
        if pdf_path:
            result["manuscript_pdf"] = pdf_path
        else:
            result["compile_error"] = compile_error
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
