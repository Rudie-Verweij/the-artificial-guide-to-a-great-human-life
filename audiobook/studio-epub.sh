#!/usr/bin/env bash
# Build the ElevenLabs Studio import file from the listening script.
# Only `#` titles become chapters; section headings are kept as bold lines so
# Studio doesn't split on them. Needs pandoc and rsvg-convert.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out .cache/epub
rsvg-convert -w 3000 -h 3000 cover.svg -o out/cover.png
for f in script/[0-9][0-9]-*.md; do
  sed -E 's/^#{2,}[[:space:]]+(.*)$/**\1**/' "$f" > ".cache/epub/$(basename "$f")"
done
pandoc .cache/epub/[0-9][0-9]-*.md -o "out/The Artificial Guide - Studio import.epub" \
  --split-level=1 --toc-depth=1 --epub-title-page=false --epub-cover-image=out/cover.png \
  --metadata title="The Artificial Guide to a Great Human Life" \
  --metadata author="Rudie Nolasco Verweij" --metadata lang=en-GB
rm -rf .cache/epub
echo "Wrote audiobook/out/The Artificial Guide - Studio import.epub and audiobook/out/cover.png"
