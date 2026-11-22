# shortform-video-toolkit

Small command-line tools for producing short-form vertical video (Reels, TikTok, Shorts) on modest hardware, built for marketing teams without a dedicated video engineer.

I made these for real weekly production work in a small medical-aesthetics marketing team in Seoul. They solve problems that come up when a single non-engineer handles AI upscaling, music, and captions on one laptop.

## Tools

| Tool | What it does |
|---|---|
| `tools/stitch_chunks.py` | Joins video chunks that were upscaled separately (for example in ComfyUI on a low-VRAM GPU), blends the frames at each seam so the texture change isn't visible, and puts the original audio back. |
| `tools/palette.py` | Samples a clip and suggests accent, secondary and dark colors for captions and motion graphics, plus how strong the text scrim should be. |
| `tools/bgm_index.py` | Measures a music folder: BPM, loudness, dynamics, brightness, and the three best 30-second sections of each track. |
| `tools/bgm_pick.py` | Suggests 3 distinct music candidates for a video, avoiding tracks used recently and keeping the tempo away from voice-over. Logs what you used. |

## Install

```bash
pip install -r requirements.txt
# ffmpeg must be on PATH
```

## Quick start

```bash
# Rebuild one master from upscaled chunks
python tools/stitch_chunks.py master.mp4 original.mp4 chunk_001.mp4 chunk_002.mp4 chunk_003.mp4

# Pick caption colors that match the footage
python tools/palette.py clip.mp4

# Index your music library once, then pick tracks per video
python tools/bgm_index.py ~/Music/bgm
python tools/bgm_pick.py ~/Music/bgm --type explainer --vo
python tools/bgm_pick.py ~/Music/bgm --record "track.mp3" --video "reel_0412"
```

Mood tags for `bgm_index.py` go in a `tags.json` file inside the music folder. See `examples/tags.json`.

## Why chunked upscaling needs stitching

Video upscalers such as SeedVR2 are memory-hungry. On an 8 to 12 GB GPU you have to process roughly 25 frames at a time. Each chunk is upscaled independently, so fine texture (skin, hair, fabric) shifts slightly at the boundaries and you see a flicker every second or so. `stitch_chunks.py` mixes the two frames on either side of each boundary 2/3 to 1/3, which hides the jump without visible ghosting at normal playback speed.

## Music licensing

These tools only analyse files you already have. They do not download music. Make sure you have the rights to use any track in published or commercial video.

## Roadmap

- [ ] Sound-effect placement from a cue sheet (align each effect's peak to the cut)
- [ ] ComfyUI API workflow templates for low-VRAM image-to-video and upscaling
- [ ] Korean documentation
- [ ] Tests and sample media

## License

MIT
