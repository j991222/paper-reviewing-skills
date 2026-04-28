---
name: paper-reviewing-skills
description: "Use when a user wants to review a mathematics paper. Extract text, split the paper into statement-level chunks, verify each statement and proof, incrementally write verification.md, synthesize final_report.tex, add review comments to the manuscript source, compile both PDFs, and return them."
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
- Mistral PDF OCR-to-Markdown helper: `scripts/mistral_pdf_to_markdown.py`
- arXiv theorem-search API helper: `scripts/search_arxiv_theorems.py`
- LaTeX compiler helper: `scripts/compile_latex.sh`
- Review workflow: `references/paper-review-workflow.md`
- Commented manuscript TeX template: `references/commented-manuscript-template.tex`
- Final report style guide: `references/final-report-style.md`
- Example final report: `references/example_report.tex`
- Final report TeX template: `references/final-report-template.tex`
- Bundled verification subskills: `agent_resources/verification/.agents/skills/`

## Runtime Notes

This is a skill, not a plugin. Do not require custom MCP tools. Use local files, the bundled scripts, and the browser/search tools exposed by the active runtime.

When checking referenced statements, citations, or imported theorems, web search is allowed. Prefer primary sources such as the cited paper, arXiv source, publisher page, author manuscript, or official theorem statement; use the bundled arXiv theorem-search helper as an additional retrieval tool when it is useful.

For PDF input, run the preparation helper. It first uses Mistral OCR to convert the PDF into Markdown at `{local_dir}/paper_ocr.md`, then uses that Markdown for all later extraction, chunking, and review steps. Do not run embedded PDF text extraction when a non-empty `paper_ocr.md` exists. The helper requires the Python `mistralai` package. The API key must come from `MISTRAL_API_KEY`, `--mistral-api-key-file`, or `--mistral-api-key`; never hardcode an API key in this skill. If Mistral OCR fails and does not produce a non-empty `paper_ocr.md`, report the blocker and ask for a key, network access, or a TeX/Markdown source. Use `--allow-pdf-text-fallback` only if the user explicitly accepts embedded PDF text extraction after Mistral fails to produce Markdown.

## Required Artifacts

Every review run must write:

- `paper_source.txt`: extracted plain text
- `paper_numbered.txt`: extracted text with stable line numbers
- `paper_chunks.jsonl`: heuristic statement-level chunks with `location_style` metadata
- `verification.md`: incrementally updated detailed verification report
- `final_report.tex`: final user-facing report
- `final_report.pdf`: compiled report, when LaTeX tooling is available
- `manuscript_with_comments.md`: manuscript content with inline review comments
- `manuscript_with_comments.tex`: manuscript source with review comments inserted
- `manuscript_with_comments.pdf`: compiled commented manuscript, when LaTeX tooling is available

For PDF input, the run must also write:

- `paper_ocr.md`: Mistral OCR Markdown

## Workflow

1. Create the local output directory.
2. Prepare the paper:
   - for TeX or Markdown, preserve source line numbers
   - for PDF, run Mistral OCR-to-Markdown through `scripts/prepare_paper.py` and use section/subsection locations from the OCR Markdown
3. Read `references/paper-review-workflow.md`.
4. Review the paper statement by statement:
   - split into theorem, lemma, proposition, corollary, definition, claim, remark, proof, and paragraph-level chunks as needed
   - check every statement in order
   - if a statement has no proof nearby, search its surrounding context for the proof
   - verify each proof beyond surface issues; look for critical mathematical errors
   - for wrong claims, try to construct counterexamples or explain plausible counterexample mechanisms
5. Incrementally write and update `verification.md` after each chunk.
6. Synthesize `final_report.tex` using `references/final-report-style.md`, `references/example_report.tex`, and `references/final-report-template.tex`.
7. Author `manuscript_with_comments.md`.
   - include the manuscript's original content together with every comment from `verification.md`
   - for PDF input, start from `{local_dir}/paper_ocr.md`
   - for TeX or Markdown input, start from the original source content
   - insert each reviewer comment immediately after the affected statement, proof step, paragraph, or displayed formula
8. Author `manuscript_with_comments.tex` from `manuscript_with_comments.md`.
   - use `references/commented-manuscript-template.tex` as the starting structure unless the original TeX source already has a better paper preamble
   - write real, valid LaTeX that compiles and reads like a normal mathematics paper; do not copy raw Markdown syntax into the `.tex` file
   - be faithful to the original paper's content: preserve the full manuscript text, mathematical statements, proofs, formulas, labels, citations, definitions, and section order except for unavoidable OCR cleanup and LaTeX syntax repair
   - do not produce a compressed reconstruction, summary, paraphrase-only rewrite, or shortened version of the manuscript
   - do not create line-by-line Markdown renderings, `\mline` wrappers, verbatim/texttt dumps, or escaped Markdown artifacts such as `\#`, `\*\*`, or escaped `$...$` in running text
   - include a complete preamble, document environment, required packages, theorem environments, and LaTeX section/list/display-math syntax
   - convert Markdown/OCR structure into professional LaTeX: headings become `\section`, `\subsection`, or `\subsubsection`; theorem, lemma, proposition, corollary, definition, remark, question, conjecture, and example blocks become `amsthm` environments; proofs become `proof` environments; lists become `itemize` or `enumerate`; display equations become LaTeX display math or equation environments
   - preserve the manuscript's original mathematical content as faithfully as possible
   - render review comments in blue, using `xcolor` or the base `color` package and a clear comment style such as `\textcolor{blue}{...}` or a blue boxed/quoted reviewer-comment block
   - do not overwrite the original manuscript source
9. Compile `final_report.tex` and `manuscript_with_comments.tex` with `scripts/compile_latex.sh`.
10. After both PDFs have been generated, inspect `manuscript_with_comments.tex` before returning anything.
   - verify that it satisfies the criteria in this `SKILL.md` and follows the style of `references/commented-manuscript-template.tex`
   - verify that it is faithful to the original paper and has not compressed, summarized, or omitted manuscript content while converting to LaTeX
   - reject it if it still contains line-by-line Markdown renderings, `\mline` wrappers, verbatim/texttt source dumps, escaped Markdown headings such as `\#`, raw `#` headings, or escaped inline math that should be real LaTeX math
   - if it fails this inspection, rewrite `manuscript_with_comments.tex` using `references/commented-manuscript-template.tex` as the structure, convert the manuscript into normal paper-style LaTeX, preserve all reviewer comments in blue, and recompile `manuscript_with_comments.pdf`
11. Return the paths to `verification.md`, `final_report.pdf`, and `manuscript_with_comments.pdf` only after the commented manuscript passes this inspection or after clearly reporting why it could not be corrected.

## Verification Standards

The review must include every checked statement. For every error, gap, or typo, include:

- exact location
- for TeX or Markdown input, use line numbers
- for PDF input, use the nearest section/subsection id or name from `paper_ocr.md`; do not use line numbers as the primary location
- clear issue description
- analysis of the error
- suggested fix
- counterexample analysis when the claim appears mathematically false

Do not stop after finding a minor gap or typo. Continue checking for deeper mathematical errors in the same proof.

Every error, gap, typo, or substantive remark in `verification.md` must also appear as an inline reviewer comment in `manuscript_with_comments.md` and `manuscript_with_comments.tex`.

## Final Report Requirements

The final report must:

- first summarize what the paper studies and how it establishes its main results
- then present findings in source order
- include every error, gap, or typo recorded in `verification.md`
- avoid page numbers
- for TeX or Markdown input, start each finding with the line number
- for PDF input, start each finding with the section/subsection id or name
- use theorem labels from the TeX source when discussing theorem ids
- never invent theorem ids or labels

If no errors, gaps, or typos are found, say so explicitly after the summary and state the scope of the review.

If there are no comments, still produce `manuscript_with_comments.md`, `manuscript_with_comments.tex`, and `manuscript_with_comments.pdf` matching the reviewed source and note that no comments were inserted.
