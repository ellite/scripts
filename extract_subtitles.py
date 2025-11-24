#!/usr/bin/env python3

"""
Extract subtitles from a video, and store them alongside the video file.
"""

import os
import re
import subprocess
from pathlib import Path
import json

# ----------------------------------
# Language mapping
# ----------------------------------
LANG_MAP = {
    "eng": "en", "en": "en",
    "por": "pt", "pt": "pt",
    "spa": "es", "es": "es",
    "ger": "de", "deu": "de", "de": "de",
    "fre": "fr", "fra": "fr", "fr": "fr",
    "ita": "it", "it": "it",
    "jpn": "ja", "ja": "ja",
    "kor": "ko", "ko": "ko",
    "rus": "ru", "ru": "ru"
}

def map_lang(code):
    return LANG_MAP.get(code.lower().strip(), code)


# ----------------------------------
# Parse ranges "1,3-5" → [1,3,4,5]
# ----------------------------------
def expand_range(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            if a.isdigit() and b.isdigit():
                result.extend(range(int(a), int(b)+1))
        elif part.isdigit():
            result.append(int(part))
    return result


# ----------------------------------
# List video files
# ----------------------------------
def list_video_files():
    files = [f for f in sorted(os.listdir()) if f.lower().endswith((".mkv", ".mp4"))]
    for idx, f in enumerate(files, 1):
        print(f"{idx}: {f}")
    return files


def get_file_selection(files):
    sel = input("\nSelect files (comma-separated, ranges allowed), Enter = all: ").strip()
    if not sel:
        return files

    idxs = expand_range(sel)
    return [files[i-1] for i in idxs if 1 <= i <= len(files)]


# ----------------------------------
# MKV: Retrieve subtitle tracks
# ----------------------------------
def get_mkv_tracks(file):
    try:
        proc = subprocess.run(
            ["mkvmerge", "-i", "-F", "json", file],
            capture_output=True, text=True, check=True
        )
    except Exception:
        print(f"❌ mkvmerge failed for {file}")
        return []

    data = json.loads(proc.stdout)
    tracks = []

    for t in data["tracks"]:
        if t["type"] != "subtitles":
            continue

        codec = t["codec"].lower()
        lang = t["properties"].get("language", "und")
        name = t["properties"].get("track_name", "")

        stype = "srt" if ("srt" in codec or "subrip" in codec) else "ass"

        tracks.append({
            "id": t["id"],
            "lang": lang,
            "type": stype,
            "name": name
        })

    return tracks


# ----------------------------------
# MP4: Retrieve subtitle tracks (ffprobe)
# ----------------------------------
def get_mp4_tracks(file):
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", file],
            capture_output=True, text=True, check=True
        )
    except Exception:
        print(f"❌ ffprobe failed for {file}")
        return []

    data = json.loads(proc.stdout)
    tracks = []
    sid = 0  # sequential subtitle track index

    for s in data.get("streams", []):
        if s.get("codec_type") != "subtitle":
            continue

        codec = s.get("codec_name", "sub")
        lang = s.get("tags", {}).get("language", "und")

        stype = "srt" if codec in ("subrip", "srt") else "ass"

        tracks.append({
            "id": sid,
            "lang": lang,
            "type": stype,
            "name": s.get("tags", {}).get("title", "")
        })
        sid += 1

    return tracks


# ----------------------------------
# Extract MKV subtitle track → SRT
# ----------------------------------
def extract_mkv_subtitle(file, track):
    base = Path(file).with_suffix("")
    lang = map_lang(track["lang"])
    tmp = f"{base}.track{track['id']}.tmp.{track['type']}"
    out = f"{base}.{lang}.srt"

    # Extract track
    cmd1 = ["mkvextract", "tracks", file, f"{track['id']}:{tmp}"]
    cmd2 = ["ffmpeg", "-y", "-i", tmp, out]

    try:
        subprocess.run(cmd1, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {file} → {out}")
    except Exception:
        print(f"❌ Error extracting track {track['id']} from {file}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ----------------------------------
# Extract MP4 subtitle track → SRT
# ----------------------------------
def extract_mp4_subtitle(file, track):
    base = Path(file).with_suffix("")
    lang = map_lang(track["lang"])
    out = f"{base}.{lang}.srt"

    cmd = [
        "ffmpeg", "-y",
        "-i", file,
        "-map", f"0:s:{track['id']}",
        out
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {file} → {out}")
    except Exception:
        print(f"❌ Failed extracting subtitle track {track['id']} from {file}")


# ----------------------------------
# MAIN
# ----------------------------------
def main():
    print("\n=== extractsubtitles ===\n")

    files = list_video_files()
    if not files:
        print("No MKV or MP4 files found.")
        return

    selected = get_file_selection(files)

    for file in selected:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"Processing: {file}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        ext = Path(file).suffix.lower()

        if ext == ".mkv":
            tracks = get_mkv_tracks(file)
            extractor = extract_mkv_subtitle
        else:
            tracks = get_mp4_tracks(file)
            extractor = extract_mp4_subtitle

        if not tracks:
            print("⚠️ No subtitle tracks found.")
            continue

        # AUTO-EXTRACT if only ONE track
        if len(tracks) == 1:
            t = tracks[0]
            print(f"➡️ Auto-extracting only subtitle track (ID {t['id']}, lang={t['lang']})...")
            extractor(file, t)
            continue

        # Show available tracks
        print("Subtitle tracks:")
        for t in tracks:
            print(f"  {t['id']}: [{t['type']}] lang={t['lang']} name=\"{t['name']}\"")

        sel = input("\nSelect subtitle tracks (comma-separated / ranges): ").strip()
        if not sel:
            print("Skipping.")
            continue

        ids = expand_range(sel)
        chosen = [t for t in tracks if t["id"] in ids]

        if not chosen:
            print("No valid tracks selected.")
            continue

        for t in chosen:
            extractor(file, t)


if __name__ == "__main__":
    main()

