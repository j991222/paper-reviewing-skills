# Paper Reviewing Skills

`paper-reviewing-skills` is an OpenClaw skill for rigorous statement-level review of mathematics papers.

It accepts papers in:

- TeX
- Markdown
- plain text
- PDF, with OCR required by default

The skill verifies the paper chunk by chunk, writes an incremental `verification.md`, synthesizes a referee-style `final_report.tex`, compiles it, and returns a PDF report when LaTeX is available.

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
local_dir/final_report.tex
local_dir/final_report.pdf
```

PDF runs also write:

```text
local_dir/paper_ocr.md
local_dir/mineru_ocr/
```

If PDF compilation fails, `final_report.tex` is still preserved.

## PDF Requirements

PDF input uses MinerU OCR to produce Markdown first:

- install the Python `requests` package if it is not available
- set `MINERU_API_TOKEN`, or pass `--mineru-token-file`
- output Markdown is written to `local_dir/paper_ocr.md`
- MinerU zip/extract artifacts are written under `local_dir/mineru_ocr/`

Run preparation with:

```bash
MINERU_API_TOKEN="..." python3 scripts/prepare_paper.py \
  --input /path/to/paper.pdf \
  --output-dir /path/to/review-output
```

The token should not be committed into the skill directory. The preparation script can use embedded PDF text only when explicitly allowed:

```bash
python3 scripts/prepare_paper.py \
  --input /path/to/paper.pdf \
  --output-dir /path/to/review-output \
  --allow-pdf-text-fallback
```

## Report Style

The final report follows [references/example_report.tex](references/example_report.tex):

- starts with a summary of the paper and its main proof strategy
- lists findings in increasing line-number order
- starts each finding with a line number
- does not use page numbers
- includes every error, gap, or typo from `verification.md`
- uses TeX labels from the source and does not invent theorem ids
