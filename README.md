# claude-watch-yt

Watch and analyze videos using **only your existing AI subscription**.

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

### Claude Code (recommended)

Two slash commands — no clone, no symlink, updates handled for you:

```
/plugin marketplace add khou/watch-yt
/plugin install claude-watch-yt@watch-yt
```

### Cursor, Gemini CLI, or any other agent

Just ask the agent to install it. With the repo URL, any agent can do it without you touching the shell:

> *"Install the watch skill from https://github.com/khou/watch-yt"*

The agent reads [AGENTS.md](AGENTS.md), downloads the repo to `~/.local/share/watch-yt`, and symlinks it into `~/.claude/skills/watch` (which both Claude Code and Cursor auto-discover).

If you'd rather do it yourself, the same one-liner the agent uses:

```bash
mkdir -p ~/.local/share && \
  curl -fsSL https://github.com/khou/watch-yt/archive/refs/heads/main.tar.gz | \
  tar xz -C ~/.local/share && \
  rm -rf ~/.local/share/watch-yt && \
  mv ~/.local/share/watch-yt-main ~/.local/share/watch-yt && \
  bash ~/.local/share/watch-yt/install.sh
```

Add `--gemini` to the final `install.sh` to also wire up Gemini CLI.

If you've already cloned the repo, just `bash install.sh` from inside it.

`ffmpeg` and `yt-dlp` install themselves the first time the script runs (Homebrew on macOS, apt/dnf/pacman on Linux). No API keys. No third-party transcription service.

> macOS: install Homebrew first from https://brew.sh if you don't have it.
> Claude Desktop is **not supported** — plugins/skills are a Claude Code (CLI) feature.

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
AGENTS.md                          Tells the agent how to install this skill
SKILL.md                           Skill (loaded after install)
.claude-plugin/plugin.json         Claude Code plugin manifest
.claude-plugin/marketplace.json    Makes the repo its own /plugin marketplace
prompts/gemini.md                  Snippet to append to your ~/.gemini/GEMINI.md
install.sh                         Manual install (symlinks repo into skill dirs)
scripts/
  watch.py                         Orchestrator (CLI entry point)
  download.py                      yt-dlp wrapper, captions best-effort
  frames.py                        ffmpeg frame extraction
  captions.py                      WebVTT parser with rolling-cue dedup
setup.sh                           Auto-installs ffmpeg + yt-dlp on first run
```

## License

[MIT](LICENSE).

## Caveats

- Long videos (30+ min) burn tokens fast even in `fast` mode. Use `--start/--end` to narrow before running.
- TikTok / Instagram videos often have no captions. Vision-only mode works but is less precise for spoken content.
- Auto-captions are imperfect on heavily-accented speech, music, or technical jargon. Original-language manual captions are preferred when available — `download.py` tries those first.
- `yt-dlp` can be blocked by some platforms; keep it updated (`brew upgrade yt-dlp`).
