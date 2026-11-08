#!/usr/bin/env python3
"""Render the audiobook listening script with the ElevenLabs API.

Chunks are rendered as lossless PCM and joined without gaps. Each chapter is
written as a FLAC master and an MP3; --m4b assembles the whole book into one
audiobook file with chapter markers. Standard library only, plus ffmpeg.

  python3 audiobook/tts.py --dry-run            # estimate, spends nothing
  python3 audiobook/tts.py                      # render every chapter
  python3 audiobook/tts.py 01 07                # render chapters 01 and 07
  python3 audiobook/tts.py --m4b                # build the M4B from out/*.flac
  python3 audiobook/tts.py --balance            # show remaining credits

The API key comes from ELEVENLABS_API_KEY, or from the ElevenLabs CLI login
in ~/.config/elevenlabs/auth-keyring.json. It is never printed or stored here.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT_DIR = HERE / "script"
OUT_DIR = HERE / "out"
CACHE_DIR = HERE / ".cache"
CONFIG_PATH = HERE / "config.json"
KEYRING_PATH = Path.home() / ".config" / "elevenlabs" / "auth-keyring.json"


# --- auth -----------------------------------------------------------------

def _jwt_claims(token):
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _refresh_oauth(oauth):
    """Swap the refresh token for a new access token and save it back."""
    claims = _jwt_claims(oauth["access_token"])
    token_url = claims["iss"].rstrip("/") + "/v1/oauth/token"
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": oauth["refresh_token"],
        "client_id": claims["client_id"],
    }).encode()
    req = urllib.request.Request(token_url, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            fresh = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"OAuth refresh failed ({e.code}). Log in again with the ElevenLabs CLI.")
    oauth = dict(oauth)
    oauth["access_token"] = fresh["access_token"]
    if fresh.get("refresh_token"):
        oauth["refresh_token"] = fresh["refresh_token"]
    oauth["expires_at"] = int(time.time()) + int(fresh.get("expires_in", 3600))
    # Write atomically, owner-only, keeping the CLI's file layout.
    fd, tmp = tempfile.mkstemp(dir=KEYRING_PATH.parent, prefix=".keyring-")
    with os.fdopen(fd, "w") as f:
        json.dump({"OAuth": json.dumps(oauth)}, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, KEYRING_PATH)
    return oauth


def auth_headers():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return {"xi-api-key": key}
    if not KEYRING_PATH.exists():
        sys.exit("No ELEVENLABS_API_KEY and no CLI login at " + str(KEYRING_PATH))
    oauth = json.loads(json.loads(KEYRING_PATH.read_text())["OAuth"])
    if oauth.get("expires_at", 0) < time.time() + 120:
        oauth = _refresh_oauth(oauth)
    return {"Authorization": "Bearer " + oauth["access_token"]}


# --- API ------------------------------------------------------------------

class Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.headers = auth_headers()

    def request(self, method, path, body=None, query=None):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        headers = dict(self.headers, Accept="*/*")
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    return resp.read(), resp.headers
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(5 * (attempt + 1))
                    continue
                sys.exit(f"{method} {path} failed: {e.code} {detail}")

    def get_json(self, path, query=None):
        return json.loads(self.request("GET", path, query=query)[0])

    def balance(self):
        sub = self.get_json("/v1/user/subscription")
        used, limit = sub["character_count"], sub["character_limit"]
        return used, limit, sub.get("tier")


# --- text -----------------------------------------------------------------

def paragraphs(md_text, pauses):
    """Turn a script file into spoken paragraphs (markdown stripped).

    Returns (text, is_heading) pairs. Headings get a full stop and a pause.
    """
    out = []
    for block in re.split(r"\n\s*\n", md_text):
        block = block.strip()
        if not block or block.startswith("<!--"):
            continue
        heading = re.match(r"^(#+)\s*", block)
        block = block[heading.end():] if heading else block
        block = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", block)
        block = " ".join(block.split())
        if heading:
            if not block[-1] in ".?!":
                block += "."
            pause = pauses["title"] if len(heading.group(1)) == 1 else pauses["heading"]
            if pause:
                block += f' <break time="{pause}" />'
        out.append((block, bool(heading)))
    return out


def chunk(paras, limit):
    """Group whole sections into chunks of at most `limit` characters.

    Chunks break only at section headings, where the narrator pauses anyway.
    A section longer than `limit` is split at the paragraph break nearest its
    middle (and again if needed).
    """
    size = lambda ps: sum(len(p) + 2 for p, _ in ps)
    sections = []
    for p in paras:
        if len(p[0]) > limit:
            sys.exit(f"Paragraph longer than {limit} chars; split it in the script: {p[0][:60]}...")
        # A heading starts a new section, unless it follows another heading.
        if not sections or (p[1] and not sections[-1][-1][1]):
            sections.append([])
        sections[-1].append(p)

    def split(sec):
        if size(sec) <= limit or len(sec) < 2:
            return [sec]
        half = size(sec) / 2
        best = min(range(1, len(sec)), key=lambda i: abs(size(sec[:i]) - half))
        while best < len(sec) - 1 and sec[best - 1][1]:
            best += 1  # never leave a heading at the end of a chunk
        return split(sec[:best]) + split(sec[best:])

    chunks = []
    for sec in sections:
        for part in split(sec):
            if chunks and size(chunks[-1] + part) <= limit:
                chunks[-1] += part
            else:
                chunks.append(part)
    return ["\n\n".join(p for p, _ in c) for c in chunks]


def truncate(paras, max_chars):
    kept, total = [], 0
    for p in paras:
        if kept and total + len(p[0]) > max_chars:
            break
        kept.append(p)
        total += len(p[0])
    return kept


# --- rendering ------------------------------------------------------------

def cache_key(chunks, i, cfg, voice_id):
    """Audio depends on the neighbouring text sent as context, so that is part of the key."""
    ident = json.dumps({
        "text": chunks[i],
        "previous_text": chunks[i - 1] if i else None,
        "next_text": chunks[i + 1] if i + 1 < len(chunks) else None,
        "stitching": cfg.get("request_stitching", True),
        "voice": voice_id,
        "model": cfg["model_id"],
        "settings": cfg["voice_settings"],
        "format": cfg["output_format"],
    }, sort_keys=True)
    return hashlib.sha256(ident.encode()).hexdigest()[:24]


def render_chapter(api, cfg, voice_id, chunks, out_path):
    CACHE_DIR.mkdir(exist_ok=True)
    parts, fresh_ids, spent = [], [], 0
    for i, text in enumerate(chunks):
        key = cache_key(chunks, i, cfg, voice_id)
        pcm = CACHE_DIR / f"{key}.pcm"
        if not pcm.exists():
            body = {
                "text": text,
                "model_id": cfg["model_id"],
                "voice_settings": cfg["voice_settings"],
                "previous_text": chunks[i - 1] if i else None,
                "next_text": chunks[i + 1] if i + 1 < len(chunks) else None,
            }
            # Only pass ids of the chunks rendered just before this one in this
            # run; previous/next text covers cached neighbours.
            if fresh_ids and cfg.get("request_stitching", True):
                body["previous_request_ids"] = fresh_ids[-3:]
            body = {k: v for k, v in body.items() if v is not None}
            audio, headers = api.request(
                "POST", f"/v1/text-to-speech/{voice_id}", body,
                query={"output_format": cfg["output_format"]})
            tmp = pcm.with_suffix(".part")
            tmp.write_bytes(audio)
            tmp.replace(pcm)
            if headers.get("request-id"):
                fresh_ids.append(headers["request-id"])
            spent += int(headers.get("x-character-count") or len(text))
            print(f"    chunk {i + 1}/{len(chunks)}: rendered {len(text)} chars")
        else:
            fresh_ids = []
            print(f"    chunk {i + 1}/{len(chunks)}: cached")
        parts.append(pcm)
    encode(b"".join(p.read_bytes() for p in parts), cfg, out_path)
    return spent


def pcm_input(cfg):
    """ffmpeg input flags for the raw 16-bit mono PCM the API returns."""
    rate = cfg["output_format"].split("_")[1]
    return ["-f", "s16le", "-ar", rate, "-ac", "1"]


def encode(pcm, cfg, out_path):
    """Write `out_path` as .flac (lossless master) and .mp3 (for players)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix, codec in ((".flac", ["-c:a", "flac"]),
                          (".mp3", ["-c:a", "libmp3lame", "-b:a", cfg["mp3_bitrate"]])):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *pcm_input(cfg), "-i", "-",
                        *codec, str(out_path.with_suffix(suffix))], input=pcm, check=True)


def build_m4b(cfg, files):
    """Join the chapter FLACs into one M4B with a chapter marker per file."""
    flacs = [OUT_DIR / f"{f.stem}.flac" for f in files]
    missing = [p.name for p in flacs if not p.exists()]
    if missing:
        sys.exit(f"Render these first: {', '.join(missing)}")
    meta, start = [";FFMETADATA1", f"title={cfg['book_title']}", f"artist={cfg['author']}",
                   f"album={cfg['book_title']}", "genre=Audiobook"], 0
    for f, flac in zip(files, flacs):
        secs = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(flac)],
            capture_output=True, text=True, check=True).stdout)
        end = start + round(secs * 1000)
        title = cfg["chapter_titles"].get(f.stem) or f.read_text().splitlines()[0].lstrip("# ")
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={start}", f"END={end}", f"title={title}"]
        start = end
    listing, metafile = CACHE_DIR / "m4b-list.txt", CACHE_DIR / "m4b-meta.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in flacs))
    metafile.write_text("\n".join(meta) + "\n")
    out = OUT_DIR / f"{cfg['book_title']}.m4b"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-i", str(metafile), "-map_metadata", "1", "-map_chapters", "1",
                    "-c:a", "aac", "-b:a", cfg["m4b_bitrate"], str(out)], check=True)
    listing.unlink()
    metafile.unlink()
    print(f"Wrote {out}")


# --- main -----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapters", nargs="*", help="chapter numbers or file stems (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="estimate only; no API calls")
    ap.add_argument("--balance", action="store_true", help="print credit balance and exit")
    ap.add_argument("--m4b", action="store_true", help="join rendered chapters into one M4B and exit")
    ap.add_argument("--voice", help="voice id (overrides config.json)")
    ap.add_argument("--max-chars", type=int, help="only the first N characters, whole paragraphs")
    ap.add_argument("--output", type=Path, help="output file (one chapter only)")
    args = ap.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text())
    voice_id = args.voice or cfg["voice_id"]
    rate = cfg.get("credits_per_char", 1.0)

    if args.balance:
        used, limit, tier = Api(cfg["api_base"]).balance()
        print(f"{tier}: {used:,} of {limit:,} credits used, {limit - used:,} left")
        return

    files = sorted(SCRIPT_DIR.glob("[0-9][0-9]-*.md"))
    if args.chapters:
        files = [f for f in files if any(f.stem == c or f.stem.startswith(c.zfill(2) + "-") for c in args.chapters)]
    if not files:
        sys.exit("No matching script files.")
    if args.m4b:
        build_m4b(cfg, files)
        return
    if args.output and len(files) != 1:
        sys.exit("--output needs exactly one chapter.")

    plan, total, new = [], 0, 0
    for f in files:
        paras = paragraphs(f.read_text(), cfg["pauses"])
        if args.max_chars:
            paras = truncate(paras, args.max_chars)
        chunks = chunk(paras, cfg["max_chunk_chars"])
        chars = sum(len(c) for c in chunks)
        uncached = sum(len(c)
                       for i, c in enumerate(chunks)
                       if not (CACHE_DIR / f"{cache_key(chunks, i, cfg, voice_id)}.pcm").exists())
        total += chars
        new += uncached
        plan.append((f, chunks))
        print(f"{f.stem}: {len(chunks)} chunks, {chars:,} chars, {uncached:,} not cached")

    print(f"Total {total:,} chars; {new:,} to render = about {round(new * rate):,} credits "
          f"({cfg['model_id']}, {rate} credit/char)")
    if args.dry_run:
        return
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed to encode the audio; install it before rendering.")
    if not cfg["output_format"].startswith("pcm_"):
        sys.exit("output_format must be pcm_<rate>; chunks are joined as raw PCM.")

    api = Api(cfg["api_base"])
    used, limit, _ = api.balance()
    print(f"Balance before: {limit - used:,} credits left")
    if new * rate > limit - used:
        sys.exit("Not enough credits for this run.")
    spent = 0
    for f, chunks in plan:
        out = args.output or OUT_DIR / f"{f.stem}.mp3"  # .flac is written beside it
        print(f"{f.stem} -> {out}")
        spent += render_chapter(api, cfg, voice_id, chunks, out)
    used, limit, _ = api.balance()
    print(f"Rendered {spent:,} chars. Balance after: {limit - used:,} credits left "
          "(the API can take a few minutes to catch up)")


if __name__ == "__main__":
    main()
