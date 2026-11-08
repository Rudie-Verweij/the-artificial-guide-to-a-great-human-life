#!/usr/bin/env bash
# Build both PDF editions into Book-for-humans/. See build/README.md.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$here/.." && pwd)
out="$here/out"
dest="$root/Book-for-humans"

for tool in pandoc tectonic; do
  command -v "$tool" >/dev/null || {
    echo "build.sh: $tool not found; see build/README.md" >&2
    exit 1
  }
done

# Chapter order. ch01's first lines (title, byline, version) are a document
# header, not body text; header_lines() strips them.
chapters=(
  ch01-introduction.md
  ch02-why-life-sucks.md
  ch03-why-most-goals-fail.md
  ch04-gain-equals-loss.md
  ch05-real-winners-quit.md
  ch06-the-five-pillars.md
  ch07-me-md.md
  ch08-the-story-continues.md
  ch09-acknowledgements.md
  ch10-sources.md
)

# Working sections, inserted after the chapter they belong to.
declare -A working=(
  [ch03-why-most-goals-fail.md]=ch03-effortless-goals.md
  [ch04-gain-equals-loss.md]=ch04-post-achievement-audit.md
  [ch06-the-five-pillars.md]=ch06-pillars-and-seeds.md
  [ch07-me-md.md]=ch07-me-md.md
)

# Version and date: line 3 of ch01, e.g. "## v1.0.1-alpha | February 2026".
header=$(sed -n 3p "$root/chapters/ch01-introduction.md")
if [[ ! $header =~ ^\#\#\ (v[^ ]+)\ \|\ (.+)$ ]]; then
  echo "build.sh: unexpected version line in ch01: $header" >&2
  exit 1
fi
version=${BASH_REMATCH[1]}
date=${BASH_REMATCH[2]}

# Reproducible timestamps: last commit that touched the manuscript.
if [[ -z ${SOURCE_DATE_EPOCH:-} ]]; then
  SOURCE_DATE_EPOCH=$(git -C "$root" log -1 --format=%ct -- chapters 2>/dev/null || true)
  SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}
fi
export SOURCE_DATE_EPOCH
export FORCE_SOURCE_DATE=1

rm -rf "$out"
mkdir -p "$out/src"

# Fonts come from the Tectonic bundle only; an empty fontconfig setup keeps
# system fonts (and their config warnings) out of the build.
printf '<?xml version="1.0"?>\n<fontconfig></fontconfig>\n' >"$out/fonts.conf"
export FONTCONFIG_FILE="$out/fonts.conf"

# Copy the inputs; drop ch01's header block (everything up to the first ---).
for ch in "${chapters[@]}"; do
  if [[ $ch == ch01-* ]]; then
    sed '1,/^---$/d' "$root/chapters/$ch" >"$out/src/$ch"
  else
    cp "$root/chapters/$ch" "$out/src/$ch"
  fi
done

build() { # edition, output file
  local edition=$1 pdf=$2 inputs=() workbook=false
  [[ $edition == Workbook ]] && workbook=true
  for ch in "${chapters[@]}"; do
    inputs+=("$out/src/$ch")
    if $workbook && [[ -n ${working[$ch]:-} ]]; then
      inputs+=("$here/workbook/${working[$ch]}")
    fi
  done
  $workbook && inputs+=("$here/workbook/personal-notes.md")

  local tex="$out/${edition,,}.tex"
  pandoc "${inputs[@]}" \
    --from markdown \
    --to latex \
    --template "$here/template.tex" \
    --lua-filter "$here/book.lua" \
    --top-level-division chapter \
    --metadata title="The Artificial Guide to a Great Human Life" \
    --metadata author="Rudie Nolasco Verweij" \
    --metadata copyright-year=2026 \
    --metadata version="$version" \
    --metadata date="$date" \
    --metadata edition="$edition" \
    $($workbook && echo --metadata workbook=true) \
    --output "$tex"

  tectonic --keep-logs --outdir "$out" "$tex" >"$out/${edition,,}.stdout" 2>&1 || {
    cat "$out/${edition,,}.stdout" >&2
    exit 1
  }
  cp "$out/${edition,,}.pdf" "$dest/$pdf"
  echo "built $pdf ($version, $date)"
}

build Reading "The Artificial Guide - Reading Edition.pdf"
build Workbook "The Artificial Guide - Workbook Edition.pdf"
