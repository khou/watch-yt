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

```bash
git clone <this-repo> ~/.claude/plugins/claude-watch-yt
bash ~/.claude/plugins/claude-watch-yt/setup.sh
```

`setup.sh` installs `ffmpeg` and `yt-dlp` via Homebrew (macOS) or apt/dnf/pacman (Linux). Both are open-source local tools — no API keys, no paid services.

### Use as a Claude Code plugin

In your Claude Code settings, register the plugin directory. The skill becomes available as `watch`:

> "Summarize https://youtu.be/dQw4w9WgXcQ"

Claude will run the script, read the transcript, and answer. It picks frames selectively when needed.

### Use the script directly

```bash
python3 scripts/watch.py "https://youtu.be/jNQXAC9IVRw"
python3 scripts/watch.py /path/to/local/video.mp4 --mode accurate
python3 scripts/watch.py "<url>" --start 5:00 --end 7:00 --resolution 768
```

The script prints a markdown summary to stdout. The work directory contains the video, captions, frames, and `summary.json` for programmatic use.

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
