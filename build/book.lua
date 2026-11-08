-- Pandoc filter for the PDF editions.
--
-- * Shifts headings up one level: "## Chapter ..." becomes a LaTeX chapter,
--   "###" a section.
-- * Breaks chapter titles after the colon ("Chapter One:" / "Introduction")
--   while keeping the one-line form for the contents and running headers.
-- * Keeps code blocks on one page.
-- * Renders the workbook markup in build/workbook/*.md (working sections,
--   writing lines, fields, Personal Notes) to the macros in template.tex.

local function latex(inlines)
  local s = pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), 'latex')
  return (s:gsub('%s+$', ''))
end

local function raw(s)
  return pandoc.RawBlock('latex', s)
end

local function chapter_header(h)
  local text = latex(h.content)
  local head, tail = text:match('^(Chapter [%a%-]+:)%s+(.+)$')
  if h.level ~= 1 or h.classes:includes('unnumbered') or not head then
    return h
  end
  return raw(('\\chapter[%s]{%s\\\\%s}'):format(text, head, tail))
end

local function shift(h)
  if h.level == 1 then
    error('level-1 heading left in the input: ' .. pandoc.utils.stringify(h))
  end
  h.level = h.level - 1
  return chapter_header(h)
end

-- Code blocks (the me.md tree) are short; keep each on one page.
local function code_block(c)
  return raw('\\begin{Verbatim}[samepage=true]\n' .. c.text .. '\n\\end{Verbatim}')
end

-- Workbook blocks -----------------------------------------------------------

local function lines_block(div)
  local a = div.attributes
  local out = {}
  if a.n then
    out[#out + 1] = ('\\wblines{%d}'):format(tonumber(a.n))
  end
  if a.fill then
    out[#out + 1] = '\\wbfill'
  end
  for _ = 1, tonumber(a.pages or 0) do
    out[#out + 1] = '\\wbpage'
  end
  if #out == 0 then
    error('.lines div needs n=, fill= or pages=')
  end
  return raw(table.concat(out, '\n'))
end

local function working_block(b)
  if b.t == 'Header' then
    return raw(('\\wbstep{%s}'):format(latex(b.content)))
  elseif b.t == 'Para' or b.t == 'Plain' then
    return raw(('\\wbprompt{%s}'):format(latex(b.content)))
  elseif b.t == 'Div' and b.classes:includes('lines') then
    return lines_block(b)
  elseif b.t == 'Div' and b.classes:includes('fields') then
    local out = {}
    for _, p in ipairs(b.content) do
      out[#out + 1] = ('\\wbfield{%s}'):format(latex(p.content))
    end
    return raw(table.concat(out, '\n'))
  elseif b.t == 'Div' and b.classes:includes('choices') then
    local items = {}
    for _, item in ipairs(b.content[1].content) do
      items[#items + 1] = latex(item[1].content)
    end
    return raw(('\\wbchoices{%s}'):format(table.concat(items, '\\quad ')))
  elseif b.t == 'Div' and b.classes:includes('newpage') then
    return raw('\\clearpage')
  end
  error('unsupported block in working section: ' .. b.t)
end

local function working_blocks(blocks)
  local out = {}
  for _, b in ipairs(blocks) do
    out[#out + 1] = working_block(b)
  end
  return out
end

local function div(d)
  if d.classes:includes('working-section') then
    local a = d.attributes
    local out = { raw(('\\begin{workingsection}{%s}{%s}'):format(
      latex({ pandoc.Str(a.chapter) }), latex({ pandoc.Str(a.title) }))) }
    for _, b in ipairs(working_blocks(d.content)) do
      out[#out + 1] = b
    end
    out[#out + 1] = raw('\\end{workingsection}')
    return out
  elseif d.classes:includes('personal-notes') then
    return raw(('\\personalnotes{%d}'):format(tonumber(d.attributes.pages)))
  end
end

-- Working-section divs are handled whole, before their headers get shifted.
return {
  { Div = div },
  { Header = shift, CodeBlock = code_block },
}
