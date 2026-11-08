# Building the PDF editions

`build.sh` turns `chapters/` into the two PDFs in `Book-for-humans/`:

- `The Artificial Guide - Reading Edition.pdf` (A5)
- `The Artificial Guide - Workbook Edition.pdf` (A5 on a 154 × 216 mm sheet
  with crop marks, plus the working sections in `workbook/` and Personal Notes)

The date on the cover and the version and date on the licence page come from
line 3 of `chapters/ch01-introduction.md` (`## v1.0.1-alpha | February 2026`).
Bump them there.

The PDFs take their timestamp from the last commit that touched `chapters/`,
so commit manuscript changes first, then rebuild and commit the PDFs.

## Tools

| Tool     | Version | Install (user-local, no sudo)                                   |
| -------- | ------- | --------------------------------------------------------------- |
| pandoc   | 3.13    | `mise install pandoc@3.13`                                      |
| Tectonic | 0.17.0  | `mise install github:tectonic-typesetting/tectonic@0.17.0`      |

Tectonic is a self-contained XeTeX. On its first run it downloads its TeX
bundle (packages and the fonts used here: TeX Gyre Pagella, TeX Gyre Heros,
DejaVu Sans Mono) and caches it, so the first build needs network access.
No system fonts or TeX installation are used.

## Run

From the repository root:

```sh
mise exec pandoc@3.13 github:tectonic-typesetting/tectonic@0.17.0 -- build/build.sh
```

Or with `pandoc` and `tectonic` on your `PATH`, just `build/build.sh`.

Intermediate files (`.tex`, logs) go to `build/out/`, which git ignores.
Timestamps come from the last commit that touched `chapters/`, so rebuilding
an unchanged manuscript gives byte-identical PDFs. Set `SOURCE_DATE_EPOCH` to
override.

## Files

- `build.sh`: chapter order, which working section follows which chapter.
- `template.tex`: pandoc LaTeX template (page size, fonts, headers, title and
  licence pages, workbook macros).
- `book.lua`: pandoc filter (chapter headings, code blocks, workbook markup).
- `workbook/`: working-section prompts; see `workbook/README.md`.
