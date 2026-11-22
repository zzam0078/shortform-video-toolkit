"""Measure a folder of background-music tracks and write _bgm_index.json.

For each track: BPM, length, loudness, dynamics, brightness, and up to three
usable 30-second sections (start on a beat, high and steady energy).

Mood tags come from an optional tags.json in the same folder, mapping part of a
file name to a list of moods, for example:
    {"sunny_morning": ["upbeat", "day-in-life"], "slow_piano": ["calm", "emotional"]}
Tracks with no match are tagged "untagged".

Usage:
    python bgm_index.py MUSIC_FOLDER

Already-measured tracks are skipped, so re-run it whenever you add music.
Requires: numpy, librosa.
"""
import json
import os
import sys

import librosa
import numpy as np

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac", ".ogg")


def load_tags(folder):
    p = os.path.join(folder, "tags.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def tags_for(name, tags):
    for key, moods in tags.items():
        if key.lower() in name.lower():
            return moods
    return ["untagged"]


def measure(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
    centroid = float(np.median(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))

    candidates = []
    for s in beat_times:
        if s < 5 or s > dur - 50:  # skip intros and the last stretch
            continue
        e = rms[(rms_t >= s) & (rms_t < s + 30)]
        if len(e):
            candidates.append((float(e.mean() - 1.5 * e.std()), float(s)))
    candidates.sort(reverse=True)
    sections = []
    for _, s in candidates:  # three sections at least 20 s apart
        if all(abs(s - x) > 20 for x in sections):
            sections.append(round(s, 2))
        if len(sections) == 3:
            break

    return {
        "bpm": round(float(np.atleast_1d(tempo)[0]), 1),
        "dur_s": round(dur, 1),
        "energy_db": round(float(20 * np.log10(rms.mean() + 1e-9)), 1),
        "dynamics_db": round(float(20 * np.log10((np.percentile(rms, 90) + 1e-9) /
                                                  (np.percentile(rms, 20) + 1e-9))), 1),
        "brightness_hz": int(centroid),
        "sections": sections,
    }


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = sys.argv[1]
    out = os.path.join(folder, "_bgm_index.json")
    old = {r["file"]: r for r in json.load(open(out, encoding="utf-8"))} if os.path.exists(out) else {}
    tags = load_tags(folder)
    rows = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(AUDIO_EXT):
            continue
        r = old.get(f) or {"file": f, **measure(os.path.join(folder, f))}
        r["tags"] = tags_for(f, tags)
        rows.append(r)
        print(f'{r["bpm"]:>6} BPM  {r["energy_db"]:>6} dB  {",".join(r["tags"]):<24} {f}')
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} tracks -> {out}")


if __name__ == "__main__":
    main()
