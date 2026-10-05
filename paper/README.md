# Paper (LaTeX)

Typeset version of `research_paper_draft1.docx`. The wording in `sections/` was
converted from the Word draft without changes; only layout was applied.

## Files
- `main.tex`       title, keywords, settings, and the order of sections
- `preamble.tex`   layout and style only (fonts, headings, tables, header)
- `sections/`      one file per section; edit the text here
- `figures/`       figure images (copied from `../figures/subq1` and `../figures/subq2`)
- `build.sh`       builds `paper.pdf`
- `paper.pdf`      latest compiled PDF
- `build/`         intermediate files; safe to ignore

## Build
    bash build.sh
Requires a LaTeX installation with `latexmk`. The folder can also be uploaded to
Overleaf as is (set `main.tex` as the main document).

## Settings (top of main.tex)
- `\anonymoustrue` / `\anonymousfalse`    hide or show the author block
- `\submissionfalse` / `\submissiontrue`  normal layout, or double spacing with line numbers
