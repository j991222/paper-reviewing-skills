---
name: check-referenced-statements
description: Check external theorem references, citations, labels, and imported results used in a mathematics paper. Use when a statement-level proof relies on external papers or named results.
---

# Check Referenced Statements

Validate external references that materially support a proof.

## Input Contract

For each cited result, read:

- the line where the citation is used
- the referenced statement as quoted or paraphrased
- the surrounding proof context
- relevant bibliography information, if available

## Procedure

1. Identify the exact current-paper claim supported by the citation.
2. Use web search and available browser/search tools to find reliable sources for the cited result. Prefer primary sources such as the cited paper, arXiv source, publisher page, author manuscript, or official theorem statement.
3. When useful, also query the arXiv theorem-search helper:

```bash
python3 {skill_dir}/scripts/search_arxiv_theorems.py --query "full referenced statement" --num-results 10
```

4. Compare the cited statement with the paper's usage:
   - hypotheses
   - definitions
   - notation
   - ambient category
   - formula variants
   - conclusion strength
5. Check the transition from the external theorem to the current-paper conclusion. A valid citation can still be used incorrectly.
6. If no reliable source is found, record an issue.
7. If the result exists but is used with mismatched assumptions or definitions, record a mathematical error.
8. Update `verification.md` under the relevant statement-level chunk.

## Output Contract

Each reference issue in `verification.md` must include:

- exact line location
- cited result or label
- mismatch or uncertainty
- mathematical analysis
- suggested fix
