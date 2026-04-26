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

If the paper is a file, run:

```bash
python3 {skill_dir}/scripts/prepare_paper.py --input "{paper_path}" --output-dir "{local_dir}"
```

If the user pasted paper text, write it to `{local_dir}/paper.md` and run the same helper on that file.

For PDF input, the helper first calls `scripts/mineru_pdf_to_markdown.py` and writes MinerU Markdown to `{local_dir}/paper_ocr.md`. The MinerU API token must come from `MINERU_API_TOKEN`, `--mineru-token-file`, or `--mineru-token`. Never hardcode a token in skill files. If the helper reports a missing token, network failure, or MinerU failure, ask for the missing credential/tooling or a TeX/Markdown source. Do not use embedded PDF text fallback unless the user explicitly accepts it.

Use:

- `{local_dir}/paper_numbered.txt` for line references
- `{local_dir}/paper_chunks.jsonl` for initial statement-level chunks
- `{local_dir}/paper_source.txt` for full context

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

1. Record the line number range and source label if present.
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

Every statement must appear in `verification.md`, even if no issue is found.

## External References

When the paper cites an external result and the validity matters:

1. Check the cited statement against the paper's usage.
2. Use available browser/search tools and, when useful, the theorem-search helper:

```bash
python3 {skill_dir}/scripts/search_arxiv_theorems.py --query "full referenced statement" --num-results 10
```

3. Compare hypotheses, notation, definitions, and ambient categories.
4. Record mismatches as issues.

## Final Report

After all chunks are reviewed, synthesize `{local_dir}/final_report.tex`.

Read `references/final-report-style.md` and inspect `references/example_report.tex` for presentation style. Use `references/final-report-template.tex` as the starting template for the new report.

The final report must:

- start with a summary of what the paper studies
- explain how the paper establishes its main results
- then list findings in increasing line-number order
- include every error, gap, or typo from `verification.md`
- avoid page numbers
- start each finding with the line number
- use theorem labels from the TeX source when referring to theorem ids

Compile the report:

```bash
{skill_dir}/scripts/compile_latex.sh "{local_dir}/final_report.tex" "{local_dir}"
```

If compilation fails, preserve `final_report.tex`, record the compiler error, and return the TeX path.
