# claude-watch-yt

Watch and analyze videos using **only your Claude subscription** — no Whisper API, no OpenAI, no Groq, no third-party transcription service.

Inspired by [bradautomates/claude-video](https://github.com/bradautomates/claude-video), but stripped of Whisper. Captions come straight from YouTube (or whatever yt-dlp can scrape). Videos without captions fall back to vision-only analysis.

## How it works

```
URL/file → yt-dlp → video.mp4 + auto-captions.vtt → ffmpeg → frames/*.jpg
                                                     ↓
                                         Claude reads selectively
```

1. `yt-dlp` pulls the video (max 720p) and YouTube's auto-generated captions.
2. `ffmpeg` extracts frames at an adaptive FPS, downscaled to keep image-token cost low.
3. The orchestrator prints a markdown summary: metadata, transcript, frame index.
4. Claude reads the transcript and **only the frames it actually needs** to answer.

When captions aren't available (TikTok, some Vimeo, some YouTube), the script switches to a denser frame sampling and Claude infers content from visuals alone.

## Token-cost modes

Pick the trade-off you want:

| Mode       | With captions     | Vision only       | ~Image tokens |
|------------|-------------------|-------------------|---------------|
| `fast`     | 15 frames @ 320px | 30 frames @ 480px | 10-20k        |
| `balanced` (default) | 25 frames @ 384px | 50 frames @ 512px | 25-60k        |
| `accurate` | 60 frames @ 512px | 100 frames @ 768px | 80-200k       |

Captions add a few hundred to a few thousand text tokens on top.

## Setup

One-time install of the two CLI tools:

```bash
bash setup.sh
```

This installs `ffmpeg` and `yt-dlp` via Homebrew (macOS) or apt/dnf/pacman (Linux). Both are open-source local tools — no API keys, no paid services.

## Use it from Claude Code (recommended)

Install the skill so Claude Code auto-loads it. Pick one:

**Option A — symlink as a user skill (simplest):**
```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/watch
```

**Option B — clone into the user skills dir:**
```bash
git clone <this-repo> ~/.claude/skills/watch
bash ~/.claude/skills/watch/setup.sh
```

Then in any Claude Code session, just paste a video URL and ask:

```
Summarize https://www.youtube.com/watch?v=jNQXAC9IVRw

What does the speaker mention about elephants in https://youtu.be/jNQXAC9IVRw ?

What's on the slide at 4:30 in https://youtu.be/<id> ?
```

Claude will detect the URL, run the prep script, read the transcript, and load only the frames it needs. To force a specific token budget:

```
Watch this video in fast mode: https://...
Watch this video in accurate mode: https://...
```

## Use the script directly (no Claude Code)

```bash
python3 scripts/watch.py "https://youtu.be/jNQXAC9IVRw"
python3 scripts/watch.py /path/to/local/video.mp4 --mode accurate
python3 scripts/watch.py "<url>" --start 5:00 --end 7:00 --resolution 768
```

The script prints a markdown summary to stdout. The work directory contains the video, captions, frames, and `summary.json` for programmatic use. Pipe the output into anything that consumes markdown.

## Quick examples

```bash
# Default balanced mode, full video
python3 scripts/watch.py "https://youtu.be/jNQXAC9IVRw"

# Cheap summary mode for a long talk — captions carry the content
python3 scripts/watch.py "https://youtu.be/<long-talk>" --mode fast

# Read tiny on-screen text in a slide deck
python3 scripts/watch.py "<url>" --mode accurate --resolution 1024

# Only analyze a 2-minute window
python3 scripts/watch.py "<url>" --start 12:30 --end 14:30

# Local file, keep working dir for inspection
python3 scripts/watch.py ~/Movies/clip.mp4 --keep --out-dir /tmp/clip
```

## CLI

```
watch.py SOURCE [--mode {fast,balanced,accurate}]
                [--max-frames N] [--resolution PX]
                [--start TIME] [--end TIME]
                [--out-dir DIR] [--keep]
```

- `SOURCE` — URL (any yt-dlp-supported site) or local file path.
- `--mode` — preset, default `balanced`.
- `--max-frames` / `--resolution` — override the preset.
- `--start` / `--end` — accept `SS`, `MM:SS`, or `HH:MM:SS`.
- `--out-dir` — working directory; defaults to a fresh tempdir.
- `--keep` — suppress the cleanup hint.

## Repo layout

```
.claude-plugin/plugin.json    Plugin manifest (Claude Code)
SKILL.md                      Skill definition — how Claude uses this
scripts/
  watch.py                    Orchestrator (CLI entry point)
  download.py                 yt-dlp wrapper, captions best-effort
  frames.py                   ffmpeg frame extraction
  captions.py                 WebVTT parser with rolling-cue dedup
setup.sh                      Install ffmpeg + yt-dlp
```

## Caveats

- Long videos (30+ min) burn tokens fast even in `fast` mode. Use `--start/--end` to narrow before running.
- TikTok / Instagram videos often have no captions. Vision-only mode works but is less precise for spoken content.
- Auto-captions are imperfect on heavily-accented speech, music, or technical jargon. Original-language manual captions are preferred when available — `download.py` tries those first.
- `yt-dlp` can be blocked by some platforms; keep it updated (`brew upgrade yt-dlp`).
