# Paper Review Workflow

You are a rigorous mathematics paper reviewer. Your task is to read the paper, understand how it establishes its main results, verify it statement by statement, and produce local review artifacts.

## Inputs

The master agent provides:

- paper path or paper text
- local output directory
- prepared text paths, when already available
- bundled verification subskill directory
- theorem-search helper path

## Preparation

Before any other action, initialize the shell environment:

```bash
source /root/root/bashrc
```

If the runtime launches a fresh shell for each command, make sure commands that depend on that environment are run from a shell where `/root/root/bashrc` has been sourced.

If the paper is a file, run:

```bash
python3 {skill_dir}/scripts/prepare_paper.py --input "{paper_path}" --output-dir "{local_dir}"
```

If the user pasted paper text, write it to `{local_dir}/paper.md` and run the same helper on that file.

For PDF input, the helper first calls `scripts/mistral_pdf_to_markdown.py` and writes Mistral OCR Markdown to `{local_dir}/paper_ocr.md`. If a non-empty `paper_ocr.md` exists, use that Markdown for the remaining preparation and review process; do not run embedded PDF text extraction. The Mistral API key must come from `MISTRAL_API_KEY`, `--mistral-api-key-file`, or `--mistral-api-key`. Never hardcode an API key in skill files. If the helper reports a missing key, network failure, or Mistral failure and no non-empty `paper_ocr.md` exists, ask for the missing credential/tooling or a TeX/Markdown source. Do not use embedded PDF text fallback unless the user explicitly accepts it after Mistral fails to produce Markdown.

Use:

- `{local_dir}/paper_numbered.txt` for line references on TeX or Markdown input
- `{local_dir}/paper_chunks.jsonl` for initial statement-level chunks
- `{local_dir}/paper_source.txt` for full context
- for PDF input, use each chunk's `location`, `section`, `section_id`, and `location_style` fields to cite the nearest section/subsection id or name from `paper_ocr.md`

You may refine the chunking manually while reviewing.

## Review Method

Read the paper in order and identify:

- definitions
- assumptions
- theorems
- lemmas
- propositions
- corollaries
- claims
- remarks with mathematical content
- proofs and proof paragraphs
- important displayed formulas

Review one statement-level chunk at a time. For each statement:

1. Record the location and source label if present. For TeX or Markdown input, use the line number range. For PDF input, use the nearest section/subsection id or name from `paper_ocr.md`, not line numbers.
2. State what the paper claims.
3. Locate the proof. If no proof is immediately attached, search nearby sections and later references for its proof.
4. Verify the proof step by step.
5. Check whether all hypotheses are used correctly.
6. Check theorem applications and cited results.
7. Check for missing assumptions, unjustified existence claims, notation conflicts, hidden changes of definition, and unsupported transitions.
8. If a claim appears false, try to build a counterexample or describe a counterexample mechanism.
9. Record every typo that affects mathematical readability, notation, references, labels, or formulas.

Do not stop at the first gap or typo. Continue looking for deeper mathematical errors in the same proof.

## Incremental Report

Maintain `{local_dir}/verification.md` throughout the review. Append or update after every checked chunk.

Use this structure:

```markdown
# Verification Report

## Paper Summary

...

## Statement-Level Verification

### Lines <start>-<end>: <label or local description>

- Statement:
- Context/proof location:
- Verification analysis:
- Issues:
  - Location:
    Type:
    Description:
    Error analysis:
    Suggested fix:
    Counterexample analysis:
- Status: checked / issue-found / needs-context
```

For PDF input, replace the heading with:

```markdown
### Section/Subsection <id or name>: <label or local description>
```

Every statement must appear in `verification.md`, even if no issue is found. Every issue or substantive comment in `verification.md` must later be inserted into `manuscript_with_comments.md` and `manuscript_with_comments.tex`.

## External References

When the paper cites an external result and the validity matters:

1. Check the cited statement against the paper's usage.
2. Use web search and available browser/search tools to find reliable sources for the cited result. Prefer primary sources such as the cited paper, arXiv source, publisher page, author manuscript, or official theorem statement.
3. When useful, also query the theorem-search helper:

```bash
python3 {skill_dir}/scripts/search_arxiv_theorems.py --query "full referenced statement" --num-results 10
```

4. Compare hypotheses, notation, definitions, and ambient categories.
5. Record mismatches as issues.

## Final Report

After all chunks are reviewed, synthesize `{local_dir}/final_report.tex`.

Read `references/final-report-style.md` and inspect `references/example_report.tex` for presentation style. Use `references/final-report-template.tex` as the starting template for the new report.

The final report must:

- start with a summary of what the paper studies
- explain how the paper establishes its main results
- then list findings in source order
- include every error, gap, or typo from `verification.md`
- avoid page numbers
- for TeX or Markdown input, start each finding with the line number
- for PDF input, start each finding with the section/subsection id or name from `paper_ocr.md`
- use theorem labels from the TeX source when referring to theorem ids

Compile the report:

```bash
{skill_dir}/scripts/compile_latex.sh "{local_dir}/final_report.tex" "{local_dir}"
```

If compilation fails, preserve `final_report.tex`, record the compiler error, and return the TeX path.

## Commented Manuscript

After `verification.md` and `final_report.tex` are complete, author the commented manuscript directly. Do not use a script to construct this artifact.

First write `{local_dir}/manuscript_with_comments.md`:

- include the manuscript's original content, not merely a list of comments
- for PDF input, use `{local_dir}/paper_ocr.md` as the starting manuscript
- for TeX or Markdown input, use the original source content as the starting manuscript
- insert each reviewer comment from `verification.md` immediately after the affected statement, proof step, paragraph, or displayed formula
- write comments in a visually distinct Markdown form, for example a blockquote beginning with `**Reviewer comment.**`
- preserve mathematical notation, labels, theorem statements, and proof text as faithfully as possible

Then write `{local_dir}/manuscript_with_comments.tex` based on `{local_dir}/manuscript_with_comments.md`:

- write real, valid LaTeX that can compile; do not paste raw Markdown into the `.tex` file
- include a complete LaTeX preamble and `\begin{document}` / `\end{document}`
- convert Markdown headings, lists, blockquotes, displayed equations, and inline comments into valid LaTeX structures
- include the manuscript's original content together with the inline comments
- use `\usepackage{xcolor}`
- render reviewer comments in blue, for example:

```tex
\begin{quote}
\color{blue}\textbf{Reviewer comment.} Explain the missing implication here and add the needed hypothesis.
\end{quote}
```

- keep comments near the relevant manuscript text, not collected at the end
- do not overwrite the original manuscript source
- before returning, compile the TeX; if compilation fails, fix the LaTeX and retry when feasible

Compile the commented manuscript:

```bash
{skill_dir}/scripts/compile_latex.sh "{local_dir}/manuscript_with_comments.tex" "{local_dir}"
```

Return both PDFs to the user:

- `{local_dir}/final_report.pdf`
- `{local_dir}/manuscript_with_comments.pdf`
