# Paper Reviewing Skills

`paper-reviewing-skills` is an OpenClaw skill for rigorous statement-level review of mathematics papers.

It accepts papers in:

- TeX
- Markdown
- plain text
- PDF, with OCR required by default

The skill verifies the paper chunk by chunk, writes an incremental `verification.md`, synthesizes a referee-style `final_report.tex`, adds comments to a manuscript copy, compiles both, and returns the report PDF plus `manuscript_with_comments.pdf` when LaTeX is available.

## Package Layout

```text
paper-reviewing-skills/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── agent_resources/
│   └── verification/.agents/skills/
├── references/
│   ├── commented-manuscript-template.tex
│   ├── example_report.tex
│   ├── final-report-style.md
│   ├── final-report-template.tex
│   └── paper-review-workflow.md
└── scripts/
    ├── compile_latex.sh
    ├── mistral_pdf_to_markdown.py
    ├── prepare_paper.py
    └── search_arxiv_theorems.py
```

## Installation

Copy the whole directory into an OpenClaw skills directory.

Workspace installation:

```bash
mkdir -p /path/to/workspace/skills
cp -R paper-reviewing-skills /path/to/workspace/skills/
```

Shared local installation:

```bash
mkdir -p "$HOME/.openclaw/skills"
cp -R paper-reviewing-skills "$HOME/.openclaw/skills/"
```

Restart OpenClaw or run `/new`, then verify:

```bash
openclaw skills list
```

## Usage

The skill first initializes its shell environment with:

```bash
source /root/root/bashrc
```

```text
Use $paper_reviewing_skills to review /path/to/paper.tex.
Write outputs to /path/to/review-output.
```

For pasted text:

```text
Use $paper_reviewing_skills to review the following Markdown paper.
[paste paper here]
```

## Outputs

Each run writes:

```text
local_dir/paper_source.txt
local_dir/paper_numbered.txt
local_dir/paper_chunks.jsonl
local_dir/verification.md
local_dir/final_report.tex
local_dir/final_report.pdf
local_dir/manuscript_with_comments.md
local_dir/manuscript_with_comments.tex
local_dir/manuscript_with_comments.pdf
```

PDF runs also write:

```text
local_dir/paper_ocr.md
local_dir/mistral_ocr/
```

If PDF compilation fails, the corresponding `.tex` file is still preserved.

## PDF Requirements

PDF input uses Mistral OCR to produce Markdown first:

- install the Python `mistralai` package if it is not available
- set `MISTRAL_API_KEY`, or pass `--mistral-api-key-file`
- output Markdown is written to `local_dir/paper_ocr.md`
- Mistral OCR metadata is written under `local_dir/mistral_ocr/`
- later preparation and review steps use non-empty `local_dir/paper_ocr.md`, not embedded PDF text
- `paper_source.txt` is the normalized working copy; for successful PDF OCR it is written from `paper_ocr.md`

Run preparation with:

```bash
MISTRAL_API_KEY="..." python3 scripts/prepare_paper.py \
  --input /path/to/paper.pdf \
  --output-dir /path/to/review-output
```

The API key should not be committed into the skill directory. The preparation script can use embedded PDF text only when Mistral OCR fails to produce a non-empty `paper_ocr.md` and fallback is explicitly allowed:

```bash
python3 scripts/prepare_paper.py \
  --input /path/to/paper.pdf \
  --output-dir /path/to/review-output \
  --allow-pdf-text-fallback
```

## Report Style

The final report follows [references/example_report.tex](references/example_report.tex):

- starts with a summary of the paper and its main proof strategy
- lists findings in source order
- starts each TeX/Markdown finding with a line number
- starts each PDF finding with the relevant section/subsection id or name
- does not use page numbers
- includes every error, gap, or typo from `verification.md`
- uses TeX labels from the source and does not invent theorem ids

## Commented Manuscript

Every issue in `verification.md` is also inserted into the commented manuscript artifacts:

- first write `local_dir/manuscript_with_comments.md` with the original manuscript content and inline reviewer comments
- then write `local_dir/manuscript_with_comments.tex` as valid compilable LaTeX based on that Markdown, not as copied raw Markdown or a line-by-line source dump
- use `references/commented-manuscript-template.tex` as a starting point unless the original TeX source already has a better paper preamble
- format `manuscript_with_comments.tex` like a normal math paper: sections use `\section`/`\subsection`, theorem-like statements use `amsthm` environments, proofs use `proof`, lists use LaTeX list environments, and formulas remain real LaTeX math
- do not leave visible Markdown artifacts such as `#`, `**`, escaped dollar signs, or OCR page headings as the main paper structure
- render reviewer comments in blue in the TeX/PDF output

The compiled output is `local_dir/manuscript_with_comments.pdf`.
