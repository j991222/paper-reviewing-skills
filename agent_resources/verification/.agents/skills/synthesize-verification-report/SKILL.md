---
name: synthesize-verification-report
description: Synthesize an incremental paper verification report into a final TeX referee-style report, preserving every issue and ordering findings by line number.
---

# Synthesize Verification Report

Create the final user-facing report after all statement-level chunks have been checked.

## Input Contract

Read:

- `verification.md`
- `paper_numbered.txt`
- `paper_source.txt`
- `references/final-report-style.md`
- `references/example_report.tex`
- `references/final-report-template.tex`

## Procedure

1. Confirm that every statement-level chunk has an entry in `verification.md`.
2. Extract every error, gap, and typo from `verification.md`.
3. Sort findings by line number.
4. Inspect `references/example_report.tex` for presentation style, then write `final_report.tex` using `references/final-report-template.tex` as the starting template.
5. Start with a summary of:
   - what the paper studies
   - its main results
   - how it establishes those results
6. Then write the remarks/comments list.
7. Each finding must start with `Line <n>:` or `Lines <m>--<n>:`.
8. Include the issue description, analysis, suggested fix, and counterexample analysis when applicable.
9. Use TeX labels from the source when referring to theorem ids. Do not invent labels or theorem ids.
10. Include every issue from `verification.md`; do not drop minor typos.

## Output Contract

Write:

- `{local_dir}/final_report.tex`

Then compile it with:

```bash
{skill_dir}/scripts/compile_latex.sh "{local_dir}/final_report.tex" "{local_dir}"
```

If compilation fails, keep `final_report.tex` and record the compiler failure in the final response.
