#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $(basename "$0") path/to/file.tex [output_dir]" >&2
  exit 2
fi

tex_file="$1"
out_dir="${2:-$(dirname "$tex_file")}"

if [[ ! -f "$tex_file" ]]; then
  echo "LaTeX file not found: $tex_file" >&2
  exit 1
fi

mkdir -p "$out_dir"

tex_dir="$(cd "$(dirname "$tex_file")" && pwd)"
tex_base="$(basename "$tex_file")"
tex_abs="$tex_dir/$tex_base"
pdf_path="$out_dir/${tex_base%.tex}.pdf"

if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$out_dir" "$tex_abs" >/dev/null
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$out_dir" "$tex_abs" >/dev/null
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$out_dir" "$tex_abs" >/dev/null
else
  echo "Neither latexmk nor pdflatex is available." >&2
  exit 127
fi

if [[ ! -f "$pdf_path" ]]; then
  echo "Expected PDF was not created: $pdf_path" >&2
  exit 1
fi

printf '%s\n' "$pdf_path"
