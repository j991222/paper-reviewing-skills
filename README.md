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
│   ├── example_report.tex
│   ├── final-report-style.md
│   ├── final-report-template.tex
│   └── paper-review-workflow.md
└── scripts/
    ├── compile_latex.sh
    ├── build_commented_manuscript.py
    ├── mineru_pdf_to_markdown.py
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
local_dir/review_comments.jsonl
local_dir/final_report.tex
local_dir/final_report.pdf
local_dir/manuscript_with_comments.tex
local_dir/manuscript_with_comments.pdf
```

PDF runs also write:

```text
local_dir/paper_ocr.md
local_dir/mineru_ocr/
local_dir/manuscript_with_comments.md
```

If PDF compilation fails, the corresponding `.tex` file is still preserved.

## PDF Requirements

PDF input uses MinerU OCR to produce Markdown first:

- install the Python `requests` package if it is not available
- set `MINERU_API_TOKEN`, or pass `--mineru-token-file`
- output Markdown is written to `local_dir/paper_ocr.md`
- MinerU zip/extract artifacts are written under `local_dir/mineru_ocr/`
- later preparation and review steps use non-empty `local_dir/paper_ocr.md`, not embedded PDF text

Run preparation with:

```bash
MINERU_API_TOKEN="..." python3 scripts/prepare_paper.py \
  --input /path/to/paper.pdf \
  --output-dir /path/to/review-output
```

The token should not be committed into the skill directory. The preparation script can use embedded PDF text only when MinerU fails to produce a non-empty `paper_ocr.md` and fallback is explicitly allowed:

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

Every issue in `verification.md` is also written to `review_comments.jsonl`. The helper `scripts/build_commented_manuscript.py` uses that JSONL file to produce:

- for TeX input: a commented copy of the original LaTeX source
- for PDF input: comments inserted into `paper_ocr.md`, then converted to LaTeX

The compiled output is `local_dir/manuscript_with_comments.pdf`.
