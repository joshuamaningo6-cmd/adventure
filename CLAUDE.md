# Handover: "What If" adventure-fantasy YouTube channel

Read this first. It sums up everything decided in Josh's planning chat (17 Nov 2026) so you can continue without re-asking. If this file is in a repo, consider renaming it to `CLAUDE.md` so Claude Code loads it automatically.

## The project in one paragraph

Josh is building a YouTube channel of **"What if…?" stories in an adventure-fantasy world**, animated with a **stick-figure hero who wears a red scarf**, in bright, painterly, anime-style backgrounds. Main videos (~8 min) go to YouTube. Short vertical clips (9:16) cut from each episode go to Instagram, TikTok and Facebook, scheduled through **Metricool**. Josh's existing asset repo for his Claude video editor is `joshuamaningo6-cmd/the-other-you` on GitHub.

## Decisions made (don't revisit unless Josh asks)

| Topic | Decision |
|---|---|
| Genre | "What if" scenarios, adventure fantasy |
| Mood | Jolly, upbeat, adventurous by day; episodes can turn tense at night (see Episode 1) |
| Hero | Black stick figure with a long **red scarf** (his identifying mark), round head, two white eye glints |
| Art style | Painterly anime-fantasy backgrounds, see `reference/branding.webp` and `reference/grasslands_chase.png` |
| Background "looks" | Grasslands Chase, Floating Islands, Ancient Ruins, Skyfarer's Dusk |
| Narration | Second person ("you…"), what-if style. **Open question:** Josh hasn't confirmed whether the hero should instead have a name and voice |
| Narrator voice | ElevenLabs **"Mike – 2D & 3D POV/Storytime YT Voice"**, voice ID `zfc8CJQpe8Kqyl0vvCzo` (middle-aged male, neutral American accent, built for stick-figure storytime animation) |
| Main video | ~8:00, 16:9. Render final at 1920×1080, 30 fps |
| Shorts | 1080×1920 (9:16), 25–55 s, rendered natively vertical (not cropped) |
| Distribution | YouTube first, then Shorts to IG Reels, TikTok and FB Reels via Metricool, about one a day |

## Style guide

- **Hero ("the Scarf"):** black silhouette stick figure. The red scarf should be the only red in most shots, so viewers find him instantly. The scarf always flows behind him, more when he runs or jumps.
- **World:** lush painterly backgrounds with warm light motes (fireflies), floating islands in the far distance, mossy boulders, layered parallax depth, and dark grass or leaf silhouettes framing the bottom edge.
- **Colour script:** saturated green and sky blue by day → gold and orange late afternoon → deep navy at night (glowing orange eyes for enemies) → gold sunrise.
- **UI:** a small sun or timer top-left when the episode has a clock. When something is crafted, a floating icon pops above the hero with a "ding". Keep on-screen text minimal.
- **Captions:** bold white with a dark outline. Shorts: 2–3 words at a time, kept out of the bottom 20%, right 15% and top 10% (platform UI).

## Episode 1 (scripted, ready for production)

**"What If You Had 10 Hours to Build a Zombie-Proof Home?"**, set in Grasslands Chase. The full script is in `script_ep01.md` (also in Josh's Claude doc: https://claude.ai/artifact/QshBYXvFL8zwHZa9fsoon1, which Josh may have edited since).

- Structure: night-chase hook → rewind → day build and crafting (stone axe, shield, cabin, crystal spear, armour pads) → late-afternoon fortifications (spikes, trench, vine-rope drawbridge, roof lookout, hanging boulder) → night siege (first wave, Brute breaks the gate when the vine rope snaps, close combat, boulder drop) → sunrise turns zombies to ash → "what would you build first?"
- Narration ≈ 940 words (~6.5 min of voice). The rest is silent action.
- 5 Shorts are planned (table in the script file).
- Thumbnail: split day/night, text **10 HOURS TO BUILD**.

## Code and assets in this pack

Everything is Python (Pillow + NumPy) piped into ffmpeg. No paid tools needed.

| File | What it is | Run |
|---|---|---|
| `code/sky_scene.py` | 16 s bright anime sky-island test scene (Floating Islands vibe): parallax layers, sun rays, clouds, an anime hero **Tavi** + cloud sidekick **Puff**, subtitles, title card. A good template for camera, parallax and choreography. | `python3 sky_scene.py out.mp4` or `python3 sky_scene.py preview 2.0 6.4` (PNG frames) |
| `code/music.py` | Original synthesized upbeat adventure cue (C–G–Am–F, 125 BPM, glockenspiel, flute, guitar, drums), ~17 s WAV. Free alternative to ElevenLabs music. | `python3 music.py bgm.wav` |
| `code/scene.py` | Earlier 12 s dark cinematic stick-figure test ("see 3 seconds into the future"). Superseded by the bright style; keep only as a reference for the figure rig. | `python3 scene.py out.mp4` |
| `code/ren.py` | Character sheet + rig for **Ren Ashgrave**, an original edgy isekai swordsman (silver hair, crimson eyes, cursed bandaged arm, chained odachi "Vesperfang"). Side project, not the channel hero. | `python3 ren.py sheet.png` |
| `reference/branding.webp` | Josh's target look: four backgrounds with the red-scarf hero | |
| `reference/grasslands_chase.png` | Close-up of the Grasslands Chase look | |
| `media/what_if_walk_on_clouds.mp4` | Rendered output of `sky_scene.py` + `music.py` | |

Notes on the code:
- All scripts draw at 2× and downscale for anti-aliasing. Characters are drawn as functions with pose parameters (run phase, crouch, air, cheer, etc.), so they can be choreographed per frame.
- Fonts used: Inter (`/usr/share/fonts/opentype/inter/`). Swap paths if they're not installed.
- **The red-scarf hero is not built in code yet.** `scene.py` has a stick-figure rig (black figure, rim light, scarf) that's the closest starting point. Restyle it to match `reference/` (rounder head, eye glints, longer red scarf, no rim light needed in daylight) and pair it with painterly Grasslands Chase backgrounds.

## ElevenLabs (connected in Josh's claude.ai account)

- Voice for all narration: `zfc8CJQpe8Kqyl0vvCzo`. Default TTS model there was `eleven_v4`, which supports inline direction tags like `[whispering]` (useful for the night section).
- Music generation was quoted at **1,650 credits (~US$0.30) for a 16 s track**. **Always tell Josh the credit cost and get a yes before generating anything.** He chose the free coded music for the test scene.

## Research done (competitor: Ifverse, @IfverseTales)

A 63K-subscriber stick-figure "what if" channel that launched in Oct 2026.
- What worked for them: escalating superpower or genius premises (reaction time 10×, 500 IQ: 4.7M and 1.5M views), sequels and series playlists, emotional twist endings.
- What hurt them: copycats flooded the format, and their generic premises stalled at 10–20K views.
- Lesson for Josh: own a recognisable brand (the red scarf, the fantasy worlds), make series and sequels, and don't clone the Ifverse look.

## Next steps (suggested order)

1. Confirm with Josh: second-person narrator vs. a named hero with his own voice.
2. Build the red-scarf hero rig and one Grasslands Chase background in code. Render a 10 s test and get Josh's sign-off.
3. Generate Episode 1 narration with the Mike voice (quote credits first).
4. Produce Episode 1 scene by scene (one file per scene, joined with ffmpeg concat), then add music and SFX.
5. Render the 5 Shorts natively at 1080×1920.
6. Help Josh set up the Metricool schedule.

## Ground rules

- Keep every character and design original. No recognisable existing characters, logos or art.
- Ask before spending ElevenLabs credits or anything else that costs money.
- Josh likes seeing quick previews (a few frames) before full renders.
