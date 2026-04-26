---
name: paper-reviewing-skills
description: "Use when a user wants to review a mathematics paper. Extract text, split the paper into statement-level chunks, verify each statement and proof, incrementally write verification.md, synthesize final_report.tex, compile it, and return the PDF."
metadata:
  short-description: Rigorous math paper review
---

# Paper Reviewing Skills

This skill reviews mathematics papers. It accepts:

- a paper file path or pasted paper text
- TeX, Markdown, or PDF input
- optional local output directory

If the user does not specify an output directory, create one under:

```text
paper_review_runs/{run_id}/
```

## Bundled Resources

Resolve paths relative to this skill directory.

- Paper preparation helper: `scripts/prepare_paper.py`
- MinerU PDF OCR-to-Markdown helper: `scripts/mineru_pdf_to_markdown.py`
- arXiv theorem-search API helper: `scripts/search_arxiv_theorems.py`
- LaTeX compiler helper: `scripts/compile_latex.sh`
- Review workflow: `references/paper-review-workflow.md`
- Final report style guide: `references/final-report-style.md`
- Example final report: `references/example_report.tex`
- Final report TeX template: `references/final-report-template.tex`
- Bundled verification subskills: `agent_resources/verification/.agents/skills/`

## Runtime Notes

This is a skill, not a plugin. Do not require custom MCP tools. Use local files, the bundled scripts, and the browser/search tools exposed by the active runtime.

For PDF input, run the preparation helper. It first uses the MinerU API to OCR the PDF into Markdown at `{local_dir}/paper_ocr.md`, then prepares that Markdown for review. The helper requires the Python `requests` package. The API token must come from `MINERU_API_TOKEN`, `--mineru-token-file`, or `--mineru-token`; never hardcode a token in this skill. If MinerU OCR fails, report the blocker and ask for a token, network access, or a TeX/Markdown source. Use `--allow-pdf-text-fallback` only if the user explicitly accepts embedded PDF text extraction instead of OCR.

## Required Artifacts

Every review run must write:

- `paper_source.txt`: extracted plain text
- `paper_numbered.txt`: extracted text with stable line numbers
- `paper_chunks.jsonl`: heuristic statement-level chunks
- `verification.md`: incrementally updated detailed verification report
- `final_report.tex`: final user-facing report
- `final_report.pdf`: compiled report, when LaTeX tooling is available

For PDF input, the run must also write:

- `paper_ocr.md`: MinerU OCR Markdown

## Workflow

1. Create the local output directory.
2. Prepare the paper:
   - for TeX or Markdown, preserve source line numbers
   - for PDF, run MinerU OCR-to-Markdown through `scripts/prepare_paper.py`
3. Read `references/paper-review-workflow.md`.
4. Review the paper statement by statement:
   - split into theorem, lemma, proposition, corollary, definition, claim, remark, proof, and paragraph-level chunks as needed
   - check every statement in order
   - if a statement has no proof nearby, search its surrounding context for the proof
   - verify each proof beyond surface issues; look for critical mathematical errors
   - for wrong claims, try to construct counterexamples or explain plausible counterexample mechanisms
5. Incrementally write and update `verification.md` after each chunk.
6. Synthesize `final_report.tex` using `references/final-report-style.md`, `references/example_report.tex`, and `references/final-report-template.tex`.
7. Compile `final_report.tex` with `scripts/compile_latex.sh`.
8. Return the paths to `verification.md`, `final_report.tex`, and `final_report.pdf` if compilation succeeds.

## Verification Standards

The review must include every checked statement. For every error, gap, or typo, include:

- exact line location
- clear issue description
- analysis of the error
- suggested fix
- counterexample analysis when the claim appears mathematically false

Do not stop after finding a minor gap or typo. Continue checking for deeper mathematical errors in the same proof.

## Final Report Requirements

The final report must:

- first summarize what the paper studies and how it establishes its main results
- then present findings in increasing line-number order
- include every error, gap, or typo recorded in `verification.md`
- avoid page numbers
- start each finding with the line number
- use theorem labels from the TeX source when discussing theorem ids
- never invent theorem ids or labels

If no errors, gaps, or typos are found, say so explicitly after the summary and state the scope of the review.
