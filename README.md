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

For full CLI options, run `python3 scripts/watch.py --help`.

## License

[MIT](LICENSE).
