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
    "eng": "en",
    "en": "en",
    "por": "pt",
    "pt": "pt",
    "spa": "es",
    "es": "es",
    "ger": "de",
    "deu": "de",
    "de": "de",
    "fre": "fr",
    "fra": "fr",
    "fr": "fr",
    "ita": "it",
    "it": "it",
    "jpn": "ja",
    "ja": "ja",
    "kor": "ko",
    "ko": "ko",
    "rus": "ru",
    "ru": "ru"
}

def map_lang(code):
    code = code.lower().strip()
    return LANG_MAP.get(code, code)


# ----------------------------------
# Expand ranges (1,3-5 → 1 3 4 5)
# ----------------------------------
def expand_range(text):
    result = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            if a.isdigit() and b.isdigit():
                result.extend(range(int(a), int(b) + 1))
        elif part.isdigit():
            result.append(int(part))
    return result


# ----------------------------------
# List video files
# ----------------------------------
def list_video_files():
    files = [f for f in sorted(os.listdir()) if f.lower().endswith(('.mkv', '.mp4'))]
    for idx, file in enumerate(files, 1):
        print(f"{idx}: {file}")
    return files


def get_file_selection(files):
    sel = input("\nSelect files (comma-separated, ranges allowed), Enter = all: ").strip()
    if not sel:
        return files

    idxs = expand_range(sel)
    selected = [files[i - 1] for i in idxs if 1 <= i <= len(files)]
    return selected


# ----------------------------------
# MKV: list subtitle tracks
# ----------------------------------
def get_mkv_subtitle_tracks(file):
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

        if "srt" in codec or "subrip" in codec:
            stype = "srt"
        else:
            stype = "ass"

        tracks.append({
            "id": t["id"],
            "lang": lang,
            "type": stype,
            "name": name
        })

    return tracks


# ----------------------------------
# Extract subtitles from MKV
# ----------------------------------
def extract_mkv_subtitle(file, track):
    base = Path(file).with_suffix('')
    lang_out = map_lang(track["lang"])

    outname = f"{base}.{lang_out}.srt"
    temp = f"{base}.track{track['id']}.tmp.{track['type']}"

    # Extract
    cmd_extract = [
        "mkvextract", "tracks", file,
        f"{track['id']}:{temp}"
    ]

    try:
        subprocess.run(cmd_extract, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(f"❌ Failed to extract track {track['id']} from {file}")
        return

    # Convert to SRT
    cmd_convert = ["ffmpeg", "-y", "-i", temp, outname]
    try:
        subprocess.run(cmd_convert, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {file} → {outname}")
    except Exception:
        print(f"❌ Failed to convert track {track['id']} to SRT")

    finally:
        if os.path.exists(temp):
            os.remove(temp)


# ----------------------------------
# MP4 extraction (first subtitle only)
# ----------------------------------
def extract_mp4_subtitle(file):
    base = Path(file).with_suffix('')
    outname = f"{base}.en.srt"

    cmd = ["ffmpeg", "-y", "-i", file, outname]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {file} → {outname}")
    except Exception:
        print(f"❌ Failed extracting subtitles from {file}")


# ----------------------------------
# Main
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

        # MP4:
        if ext == ".mp4":
            extract_mp4_subtitle(file)
            continue

        # MKV
        tracks = get_mkv_subtitle_tracks(file)
        if not tracks:
            print("⚠️ No subtitle tracks found.")
            continue

        print("Subtitle tracks:")
        for t in tracks:
            print(f"  {t['id']}: [{t['type']}] lang={t['lang']} name=\"{t['name']}\"")

        sel = input("\nSelect subtitle tracks (comma-separated, ranges allowed): ").strip()
        if not sel:
            print("Skipping.")
            continue

        ids = expand_range(sel)
        chosen = [t for t in tracks if t["id"] in ids]

        if not chosen:
            print("No valid tracks selected.")
            continue

        for t in chosen:
            extract_mkv_subtitle(file, t)


if __name__ == "__main__":
    main()
