# Audiobook edition

A listening edition of *The Artificial Guide to a Great Human Life*, narrated by the
ElevenLabs voice Cornelius on the Eleven v4 model. `chapters/` stays the source of truth; `script/` is the
same book adapted for the ear.

## The script

| Script file | From |
|---|---|
| `00-opening.md` | New: title, author, edition |
| `01-…` to `08-…` | `chapters/ch01` to `ch08` |
| `09-acknowledgements.md` | `chapters/ch09` |
| `10-closing.md` | New: closing, points to Sources in the PDF |

`chapters/ch10-sources.md` is not read aloud.

What changed for listening: lists and tables became sentences, citations became
names in the prose, numbers and symbols are written as spoken ("ninety-one and a
half percent", "ten times"), "me.md" is written "me dot em dee", and Chapter Seven
describes the template's six sections instead of showing the tree. When the
manuscript changes, update the matching script file by hand.

`#` lines are chapter titles and `##`/`###` lines are section headings; both are
read aloud with a short pause after them.

## Rendering audio

Needs Python 3 (standard library only) and `ffmpeg`.

```sh
python3 audiobook/tts.py --dry-run     # chunk count and credit estimate, spends nothing
python3 audiobook/tts.py --balance     # credits left on the account
python3 audiobook/tts.py               # render all chapters to audiobook/out/
python3 audiobook/tts.py 03 07         # render only some chapters
python3 audiobook/tts.py --m4b         # join rendered chapters into one M4B
```

Voice, model and voice settings live in `config.json`. Each chapter is split at
section headings, where the narrator pauses anyway, into chunks of at most
`max_chunk_chars`; a longer section is split at the paragraph break nearest its
middle. Each chunk is sent with the neighbouring text (and the request ids of the
chunks rendered just before it) so prosody carries over. Rendered chunks are
cached in `audiobook/.cache/` by a hash of their text, neighbouring text, voice,
model and settings, so a re-run only pays for changed chunks.

Chunks are requested as lossless 44.1 kHz PCM and joined without gaps. Each
chapter is written to `out/` as a FLAC master and a 192 kbps MP3. `--m4b` joins
the chapter FLACs into one AAC audiobook file with a chapter marker per file;
`chapter_titles` in `config.json` overrides the spoken title where it should
read differently on screen.

The API key is read from `ELEVENLABS_API_KEY`, or from the ElevenLabs CLI login in
`~/.config/elevenlabs/auth-keyring.json` (an expired login is refreshed in place).
It is never printed or written to the repo.

Audio (`out/`, `samples/`) and the cache are git-ignored.

## ElevenLabs Studio

The Studio API needs a whitelisted account, so Studio is used through the web app.
Build an import file and a square cover from the script, then upload the EPUB
as a new Studio project and the cover as its artwork:

```sh
audiobook/studio-epub.sh   # writes audiobook/out/*.epub and out/cover.png (3000x3000)
```

Each `#` title becomes a Studio chapter; section headings stay as bold lines.
Use the voice Cornelius on Eleven v4, convert, regenerate any paragraph with an
artifact, then export. The cover source is `cover.svg`.
