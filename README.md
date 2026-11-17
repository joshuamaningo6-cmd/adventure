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
