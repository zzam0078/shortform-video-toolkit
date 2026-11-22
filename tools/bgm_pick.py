"""Pick 3 background-music candidates for a video without reusing the same tracks.

Rules:
- Tracks used in the last N videos (--recent, default 8) are excluded.
- Least-used tracks first, then tracks whose felt tempo fits the video
  (85-125 BPM when there is voice-over, so the music does not fight the narration).
- The candidates differ from each other: different main mood, different artist,
  and at least 10 BPM apart.
- If too few tracks match the mood, neighbouring moods are added.
- When a track is reused, a different 30-second section is suggested.

Reads _bgm_index.json (made by bgm_index.py) and writes _bgm_usage_log.json.
Mood names are whatever you used in tags.json; the video-type presets below are
examples you can edit.

Usage:
    python bgm_pick.py MUSIC_FOLDER --type tour [--vo] [--n 3] [--recent 8]
    python bgm_pick.py MUSIC_FOLDER --mood upbeat day-in-life [--vo]
    python bgm_pick.py MUSIC_FOLDER --record "track.mp3" --video "my_reel_v1" [--start 42.5]
"""
import argparse
import datetime
import json
import os
import sys

VIDEO_TYPES = {  # video type -> moods, first is preferred
    "tour": ["day-in-life", "upbeat", "casual"],
    "vlog": ["day-in-life", "upbeat", "casual"],
    "explainer": ["educational", "hip", "calm"],
    "interview": ["storytelling", "epic", "emotional"],
    "promo": ["exciting", "hip", "upbeat"],
    "meme": ["exciting", "hip", "casual"],
    "before-after": ["emotional", "calm"],
    "twist": ["suspense", "epic", "hip"],
}
NEIGHBOURS = {
    "day-in-life": ["upbeat", "casual"], "upbeat": ["day-in-life", "exciting"],
    "casual": ["hip", "day-in-life"], "educational": ["hip", "calm"],
    "hip": ["casual", "exciting"], "calm": ["emotional", "casual"],
    "storytelling": ["epic", "emotional"], "epic": ["storytelling", "exciting"],
    "emotional": ["calm", "storytelling"], "exciting": ["hip", "upbeat"],
    "suspense": ["epic", "hip"],
}


def felt_bpm(bpm):
    """Fold double/half-time detections into a 65-140 range."""
    while bpm > 140:
        bpm /= 2
    while bpm < 65:
        bpm *= 2
    return round(bpm, 1)


def artist(f):
    return f.split(" - ")[-1].rsplit(".", 1)[0].strip().lower() if " - " in f else f.lower()


def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--type", choices=list(VIDEO_TYPES))
    ap.add_argument("--mood", nargs="+")
    ap.add_argument("--vo", action="store_true", help="video has voice-over")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--recent", type=int, default=8)
    ap.add_argument("--record")
    ap.add_argument("--video")
    ap.add_argument("--start", type=float)
    a = ap.parse_args()

    index = load(os.path.join(a.folder, "_bgm_index.json"), None)
    if index is None:
        sys.exit("No _bgm_index.json found. Run bgm_index.py first.")
    log_path = os.path.join(a.folder, "_bgm_usage_log.json")
    log = load(log_path, [])

    if a.record:
        hit = [r for r in index if r["file"] == a.record or a.record.lower() in r["file"].lower()]
        if len(hit) != 1:
            sys.exit(f"Need exactly one match for {a.record!r}, got {[h['file'] for h in hit]}")
        log.append({"date": datetime.date.today().isoformat(), "video": a.video or "",
                    "file": hit[0]["file"], "start": a.start})
        json.dump(log, open(log_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("recorded:", hit[0]["file"], "/", a.video)
        return

    moods = a.mood or VIDEO_TYPES.get(a.type) or sys.exit("Give --type or --mood")
    recent = {e["file"] for e in log[-a.recent:]}
    uses, starts = {}, {}
    for e in log:
        uses[e["file"]] = uses.get(e["file"], 0) + 1
        if e.get("start") is not None:
            starts.setdefault(e["file"], []).append(e["start"])
    target = 105 if a.vo else 118

    def pool_for(ms):
        return [r for r in index if r["file"] not in recent and set(r["tags"]) & set(ms)]

    pool, widened = pool_for(moods), False
    if len(pool) < a.n * 2:
        pool = pool_for(list(dict.fromkeys(moods + [n for m in moods for n in NEIGHBOURS.get(m, [])])))
        widened = True

    def score(r):
        f = felt_bpm(r["bpm"])
        off = max(0, 85 - f, f - 125) if a.vo else abs(f - target) / 4
        rank = min((moods.index(t) for t in r["tags"] if t in moods), default=len(moods))
        tiebreak = r["dynamics_db"] if a.vo else -r["energy_db"]
        return (uses.get(r["file"], 0), round(off / 10), rank, tiebreak)

    ranked = sorted(pool, key=score)
    pick = []
    for r in ranked:
        f = felt_bpm(r["bpm"])
        if any(r["tags"][0] == p["tags"][0] or artist(r["file"]) == artist(p["file"])
               or abs(f - felt_bpm(p["bpm"])) < 10 for p in pick):
            continue
        pick.append(r)
        if len(pick) == a.n:
            break
    for r in ranked:  # top up if the diversity rules left gaps
        if len(pick) == a.n:
            break
        if r not in pick:
            pick.append(r)

    print(f"moods {moods}{' (+neighbours)' if widened else ''} | "
          f"{len(recent)} recent tracks excluded | pool {len(pool)}")
    for i, r in enumerate(pick, 1):
        prev = starts.get(r["file"], [])
        sec = next((s for s in r["sections"] if all(abs(s - p) > 15 for p in prev)),
                   r["sections"][0] if r["sections"] else 0)
        print(f'{i}. {r["file"]} | {felt_bpm(r["bpm"])} BPM | {",".join(r["tags"])} | '
              f'used {uses.get(r["file"], 0)}x | start at {sec}s')


if __name__ == "__main__":
    main()
