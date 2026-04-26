---
name: verify-sequential-statements
description: Verify a mathematics paper in source order, checking statement-level chunks, proofs, theorem applications, gaps, errors, and typos. Use during paper review after text extraction and chunking.
---

# Verify Sequential Statements

Check every statement-level chunk in the paper in order and update `verification.md`.

## Input Contract

Read:

- `paper_numbered.txt`
- `paper_chunks.jsonl`
- surrounding context from `paper_source.txt`
- current `verification.md`

Use line numbers from `paper_numbered.txt`.

## Procedure

1. Work through chunks in textual order.
2. For each chunk, identify:
   - line range
   - TeX label, if present
   - statement type
   - statement content
   - proof location, if any
3. If the statement has no proof nearby, search the surrounding context and later references for its proof before marking it missing.
4. Verify the proof step by step:
   - logical validity
   - use of hypotheses
   - theorem applications
   - existence claims
   - notation consistency
   - definition and formula compatibility
   - hidden assumptions
   - unsupported transitions
5. Check whether assumptions are used correctly. If an assumption appears unused, decide whether it is redundant or whether the proof silently needs it.
6. When a claim looks false, try to construct a counterexample or explain a counterexample mechanism.
7. Record typos in formulas, notation, references, labels, and mathematically meaningful prose.
8. Do not stop after finding one issue. Continue checking the rest of the statement and proof.

## Output Contract

After each checked chunk, update `verification.md` with:

```markdown
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

Every statement must appear in `verification.md`, including statements with no detected issue.
