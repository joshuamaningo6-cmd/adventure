# Red Scarf Tales

"What if…?" adventure-fantasy animation channel. Project notes and decisions are in `CLAUDE.md` (the handover).

| Path | What |
|---|---|
| `channel/index.html` | Channel setup kit: preview of the channel page plus a step-by-step checklist with copy-ready name, handle, description, keywords, playlists, upload defaults and the Episode 1 launch captions. Open it in a browser from this folder so the art and videos load. |
| `channel/art/` | `banner_2560x1440.png`, `avatar_800x800.png`, and a banner safe-area check image |
| `scripts/ep01_script.md` | Episode 1 recording script, one block per scene, with ElevenLabs v4 direction tags. Also has the YouTube upload pack (title, description, chapters, tags). |
| `script_ep01.md` | The original full production table: visuals, SFX and music cues |
| `video/teaser.py` | Renderer for the red-scarf hero in Grasslands Chase: 10 s 16:9 teaser, 10 s native 9:16 reel, and the channel art |
| `video/out/` | Rendered `ep01_teaser_10s_16x9.mp4` (1920×1080) and `ep01_reel_10s_9x16.mp4` (1080×1920) |
| `video/episode.py` | Episode 1 renderer: 21 scenes timed to the narration, plus the two 9:16 timelapse Shorts |
| `video/soundtrack.py` | Music cues (day, golden hour, siege, sunrise), SFX timed from the choreography, ducking under the voice, subtitles |
| `audio/narration/` | ElevenLabs "Mike" narration, one MP3 per scene (`timing.json` has the pauses) |
| `video/out/ep01/` | `ep01_what_if_10_hours_web.mp4` (8:11, 1080p, web encode), `ep01_captions.srt`, `ep01_thumbnail.png`. The full-quality master (265 MB) is too big for GitHub and is git-ignored. |
| `video/out/shorts/` | `ep01_short1_10_hours_in_55s_9x16.mp4` (day timelapse), `ep01_short2_surviving_night_one_9x16.mp4` (night timelapse), both 1080×1920 |
| `code/`, `reference/`, `media/` | The original handover pack |

## Re-render

```bash
python3 code/music.py /tmp/bgm.wav
```

```bash
BGM=/tmp/bgm.wav python3 video/teaser.py yt video/out/ep01_teaser_10s_16x9.mp4
```

```bash
BGM=/tmp/bgm.wav python3 video/teaser.py reel video/out/ep01_reel_10s_9x16.mp4
```

```bash
python3 video/teaser.py banner channel/art
```

Quick stills before a full render: `python3 video/teaser.py reel preview 1.0 4.5 9.6`. Each render takes about 1–2 minutes. Needs Pillow, NumPy, ffmpeg and the Inter font.

## Episode 1

```bash
python3 video/episode.py yt timeline
```

```bash
seq 1 21 | xargs -P 4 -I{} sh -c 'python3 video/episode.py yt scene {} video/out/ep01/scenes/scene_$(printf %02d {}).mp4'
```

```bash
python3 video/soundtrack.py episode /tmp/ep01_mix.wav video/out/ep01/ep01_captions.srt
```

Then join the scene files with ffmpeg concat and mux the mix (loudnorm to −14 LUFS) plus the SRT. Shorts: `python3 video/episode.py reel short 1 out.mp4` and `python3 video/soundtrack.py short 1 out.wav`. Quick stills: `python3 video/episode.py yt mpreview 8:10 15:12`.
A full render takes about an hour on 4 cores.
