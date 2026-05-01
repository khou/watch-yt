# claude-watch-yt

Watch and analyze videos using **only your existing AI subscription** — no Whisper API, no OpenAI, no Groq, no third-party transcription service. Works with Claude Code, Cursor, and Gemini CLI out of the box.

Inspired by [bradautomates/claude-video](https://github.com/bradautomates/claude-video), but stripped of Whisper. Captions come straight from YouTube (or whatever yt-dlp can scrape). Videos without captions fall back to vision-only analysis.

## How it works

```
URL/file → yt-dlp → video.mp4 + auto-captions.vtt → ffmpeg → frames/*.jpg
                                                     ↓
                                       Your agent reads selectively
```

1. `yt-dlp` pulls the video (max 720p) and YouTube's auto-generated captions.
2. `ffmpeg` extracts frames at an adaptive FPS, downscaled to keep image-token cost low.
3. The orchestrator prints a markdown summary: metadata, transcript, frame index.
4. Your agent reads the transcript and **only the frames it actually needs** to answer.

When captions aren't available (TikTok, some Vimeo, some YouTube), the script switches to a denser frame sampling and Claude infers content from visuals alone.

## Token-cost modes

Pick the trade-off you want:

| Mode       | With captions     | Vision only       | ~Image tokens |
|------------|-------------------|-------------------|---------------|
| `fast`     | 15 frames @ 320px | 30 frames @ 480px | 10-20k        |
| `balanced` (default) | 25 frames @ 384px | 50 frames @ 512px | 25-60k        |
| `accurate` | 60 frames @ 512px | 100 frames @ 768px | 80-200k       |

Captions add a few hundred to a few thousand text tokens on top.

## Install

The pipeline (Python + ffmpeg + yt-dlp) is model-agnostic — drop-in instructions for the major local agentic tools:

| Tool             | Install path                       |
|------------------|------------------------------------|
| **Claude Code**  | `~/.claude/skills/watch/`          |
| **Cursor**       | `.cursor/rules/watch.mdc`          |
| **Gemini CLI**   | `~/.gemini/extensions/watch/`      |

Each one runs the script directly when you ask about a video. `ffmpeg` and `yt-dlp` install automatically on first run (Homebrew on macOS, apt/dnf/pacman on Linux). No API keys. No third-party transcription service.

> macOS: install Homebrew first from https://brew.sh if you don't have it.

### Claude Code

```bash
ln -s "$(pwd)" ~/.claude/skills/watch
# or: git clone <this-repo> ~/.claude/skills/watch
```

Then in any session: *"Summarize https://youtu.be/&lt;id&gt;"*

### Cursor

```bash
git clone <this-repo> ~/.claude/skills/watch    # any path is fine
mkdir -p .cursor/rules
cp ~/.claude/skills/watch/prompts/cursor.mdc .cursor/rules/watch.mdc
```

(Or copy the rule into a global rules folder if your Cursor version supports it.) Cursor's agent picks up the rule, runs the script, and answers. Edit the path inside `cursor.mdc` if you didn't install at `~/.claude/skills/watch`.

### Gemini CLI

```bash
git clone <this-repo> ~/.gemini/extensions/watch
```

Add the contents of `prompts/gemini.md` to your `~/.gemini/GEMINI.md`, or include the file in your project context. Then ask Gemini about a video URL.

## Use it

Once installed, just ask the agent about a video URL:

```
Summarize https://www.youtube.com/watch?v=jNQXAC9IVRw

What does the speaker say about elephants in https://youtu.be/jNQXAC9IVRw ?

What's on the slide at 4:30 in https://youtu.be/<id> ?
```

To force a token budget:

```
Watch this in fast mode: https://...
Watch this in accurate mode: https://...
```

## Use the script directly

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
                [--out-dir DIR] [--keep] [--no-install]
```

- `SOURCE` — URL (any yt-dlp-supported site) or local file path.
- `--mode` — preset, default `balanced`.
- `--max-frames` / `--resolution` — override the preset.
- `--start` / `--end` — accept `SS`, `MM:SS`, or `HH:MM:SS`.
- `--out-dir` — working directory; defaults to a fresh tempdir.
- `--keep` — suppress the cleanup hint.
- `--no-install` — skip the auto-install of ffmpeg/yt-dlp.

## Repo layout

```
.claude-plugin/plugin.json    Claude Code plugin manifest
SKILL.md                      Claude Code skill definition
prompts/
  cursor.mdc                  Cursor rule
  gemini.md                   Gemini CLI instructions
scripts/
  watch.py                    Orchestrator (CLI entry point)
  download.py                 yt-dlp wrapper, captions best-effort
  frames.py                   ffmpeg frame extraction
  captions.py                 WebVTT parser with rolling-cue dedup
setup.sh                      Auto-installs ffmpeg + yt-dlp on first run
```

## Caveats

- Long videos (30+ min) burn tokens fast even in `fast` mode. Use `--start/--end` to narrow before running.
- TikTok / Instagram videos often have no captions. Vision-only mode works but is less precise for spoken content.
- Auto-captions are imperfect on heavily-accented speech, music, or technical jargon. Original-language manual captions are preferred when available — `download.py` tries those first.
- `yt-dlp` can be blocked by some platforms; keep it updated (`brew upgrade yt-dlp`).
