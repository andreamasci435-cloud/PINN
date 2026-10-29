# L’inconsistenza della natura — LaTeX edition

- `main.tex`: editable manuscript, Italian, with numbered equations and PDF bookmarks.
- `main.pdf`: compiled manuscript.
- `original.pdf`: unchanged supplied manuscript, retained for comparison.
- `../../web/content/inconsistenza-della-natura.pdf`: identical public copy used by the website.

## Rebuild

With Tectonic installed, run from the repository root:

```sh
tectonic docs/research-paper/main.tex
cp docs/research-paper/main.pdf web/content/inconsistenza-della-natura.pdf
npm run build
```

Alternatively open this folder in the Codex LaTeX editor, or upload `main.tex` to Overleaf. Vercel serves the precompiled PDF; no TeX installation or Python backend is needed there.

## Editorial scope

The original Italian argument and examples are retained. Changes are typographical: paragraphs, heading hierarchy, mathematical transcription, punctuation and obvious spelling errors (including Wigner, Rudolf Clausius and Schrödinger). Some parentheses surrounding displayed equations were converted to sentences. A descriptive subtitle, editorial synopsis, keywords and a short edition note were added. No author name, affiliation, bibliography, peer-review status or new research result has been invented. The blank `\AuthorName` macro can be filled when the author's name is supplied; update PDF author metadata as well.

This is a typeset philosophical essay, not the technical report for the PINN benchmark. It has not undergone scientific fact-checking. Assertions about the derivation of physical principles, entropy, global/local symmetry, conservation and the interpretation of experimental confirmation remain the author's assertions, not conclusions established by this conversion. Before presenting it as a scientific paper, the author should review these arguments and supply verifiable references. No unprovided references have been fabricated.
