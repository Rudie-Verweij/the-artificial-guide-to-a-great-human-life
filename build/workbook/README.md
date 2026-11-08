# Workbook sources

Working-section pages for the Workbook Edition. `build.sh` inserts each file
after the chapter named in its file name; `personal-notes.md` goes at the end.
The prompts come from the first Workbook Edition (February 2026).

Markup (rendered by `../book.lua`):

- `::: {.working-section chapter="Chapter Three" title="..."}` wraps a file.
- `## Heading` is a bold step label; a paragraph is an italic prompt.
- `::: {.lines n=4}` adds 4 writing lines, `fill=page` fills the rest of the
  page, `pages=1` adds one more full page of lines.
- `::: fields` turns each paragraph into a label with a line after it.
- `::: choices` sets a bullet list as a row of italic options.
- `::: newpage` starts a new page.
