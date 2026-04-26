# Final Report Style

The final report should follow a concise mathematical referee-comment style.

## Structure

Use `references/final-report-template.tex` as the starting file. Inspect `references/example_report.tex` for the desired referee-comment presentation style.

The body should have:

1. A title.
2. A summary section explaining:
   - what the paper studies
   - the main results
   - how the paper establishes those results
3. A remarks/comments section introduced in the style of `references/example_report.tex`, for example:

```tex
\noindent Here is a list of remarks/comments.\bigskip
```

4. Findings in increasing line-number order. Use line numbers from `paper_numbered.txt`.

## Finding Style

Do not separate findings into separate sections for errors, gaps, and typos. Present them in one ordered list. Do not include page numbers.

Each finding should start with the line number and then the content:

```tex
\vv
\noindent Line 128: The proof of Lemma \ref{lem:main-reduction} uses compactness here, but the argument only proves sequential compactness. The missing implication is not valid in this setting. Suggested fix: add a metrizability hypothesis or replace the compactness step with ...
```

For line ranges, write:

```tex
\vv
\noindent Lines 215--223: ...
```

If a theorem, lemma, proposition, or equation has a TeX label, use that label. Do not invent theorem ids.

## Required Content For Issues

Every issue transferred from `verification.md` should include, in prose:

- exact location
- clear description
- mathematical analysis
- suggested fix
- counterexample analysis when the claim appears false

Typos can be shorter, but still state the exact line and correction.

## No-Issue Case

If no errors, gaps, or typos are found, write after the summary:

```tex
\noindent No errors, gaps, or typos were found in the reviewed statement-level chunks. This report is limited to the verification scope described above.
```
