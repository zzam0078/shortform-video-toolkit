"""Stitch upscaled video chunks back into one master file.

Long clips are often upscaled in short chunks (for example 25 frames at a time with
SeedVR2 in ComfyUI) to fit in a small GPU. Joining the chunks naively leaves a visible
texture jump at every seam. This script concatenates the chunks, cross-blends the two
frames on either side of each seam, and muxes the original audio back in.

Usage:
    python stitch_chunks.py OUT.mp4 AUDIO_SOURCE.mp4 chunk1.mp4 chunk2.mp4 ... \
        [--size 1080x1920] [--fps 24] [--crf 14]

Requires: ffmpeg on PATH, numpy.
"""
import argparse
import subprocess

import numpy as np


def read_frames(path, w, h):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def blend_seams(frames, seams):
    """Mix the frames on each side of a seam 2/3 : 1/3 so the texture change is gradual."""
    for s in seams:
        a, b = frames[s - 1].astype(np.float32), frames[s].astype(np.float32)
        frames[s - 1] = (a * 2 / 3 + b / 3).round().astype(np.uint8)
        frames[s] = (a / 3 + b * 2 / 3).round().astype(np.uint8)
    return frames


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("audio_source", help="video or audio file whose audio track is kept")
    ap.add_argument("chunks", nargs="+")
    ap.add_argument("--size", default="1080x1920", help="WIDTHxHEIGHT of the chunks")
    ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--crf", type=int, default=14)
    a = ap.parse_args()
    w, h = map(int, a.size.lower().split("x"))

    parts = [read_frames(c, w, h) for c in a.chunks]
    seams, n = [], 0
    for p in parts[:-1]:
        n += len(p)
        seams.append(n)
    frames = blend_seams(np.concatenate(parts).copy(), seams)

    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(a.fps), "-i", "-", "-i", a.audio_source, "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", a.out], stdin=subprocess.PIPE)
    enc.stdin.write(frames.tobytes())
    enc.stdin.close()
    enc.wait()
    print(f"{a.out}: {len(frames)} frames, seams at {seams}")


if __name__ == "__main__":
    main()
