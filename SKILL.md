---
name: watch
description: Analyze the contents of a video. Use whenever the user provides a YouTube/Vimeo/TikTok/X URL or local video file (.mp4/.mov/.mkv/.webm) and asks a question about what's in it — what was said, what was shown, who appears, when something happens, etc. Pulls the transcript via auto-captions (no third-party transcription service) and extracts frames for visual context.
---

# Watch a video

This skill prepares a video for analysis. It downloads YouTube auto-captions for the transcript and extracts a small number of frames for visual context. **No transcription API is used** — captions come straight from the platform when available, and videos without captions fall back to vision-only analysis.

## When to use

Trigger when the user shares a video URL or file path and asks anything about its contents. Examples:

- "Summarize this YouTube video: <url>"
- "What does the speaker say about <topic> in this video?"
- "At what timestamp does <X> happen?"
- "Describe what's on screen at 2:30"
- "Who's in this clip?"

Do NOT trigger for non-video URLs, image-only files, or audio files.

## How to run

The script lives at `scripts/watch.py` inside this skill's directory. Resolve it to an absolute path (the directory containing this `SKILL.md`) before invoking. After running `install.sh`, the canonical path is `~/.claude/skills/watch/scripts/watch.py`.

```bash
python3 <skill-dir>/scripts/watch.py "<source>" [options]
```

Options (all optional):
- `--mode {fast,balanced,accurate}` — token vs. accuracy preset. Default `balanced`. See the table below.
- `--start <time>` and `--end <time>` — trim to a range. Use when the user asks about a specific segment ("what happens in the last 2 minutes").
- `--max-frames N` — override the mode's frame cap.
- `--resolution N` — override the mode's frame width in pixels. Bump to 768+ ONLY when the user needs to read small on-screen text (slide content, code, UI labels).
- `--keep` — don't print the cleanup hint.

### Mode selection

| Mode       | With captions     | Vision only       | When to use |
|------------|-------------------|-------------------|-------------|
| `fast`     | 15 frames @ 320px | 30 frames @ 480px | Summaries, "what's this video about", or anything where the transcript clearly carries the answer. |
| `balanced` | 25 frames @ 384px | 50 frames @ 512px | **Default.** Most general questions. |
| `accurate` | 60 frames @ 512px | 100 frames @ 768px | Visual details that matter — tracking who appears when, reading dense slides, transcribing on-screen code, dense action choreography. Costs 3-4x more tokens. |

Pick the lowest mode that can answer the user's question. If unsure, default to `balanced`. If the user explicitly asks for "thorough" / "detailed visual analysis" / "find every instance of X on screen", use `accurate`.

Time format: `SS`, `MM:SS`, or `HH:MM:SS`.

## Workflow

1. **Run the script.** The output is a markdown summary with metadata, transcript (if available), and a list of frame paths with timestamps.
2. **Read the transcript first.** It's already in your context — that alone often answers the question. For 80%+ of questions about YouTube videos, the transcript is sufficient.
3. **Read frames selectively.** The frame list is an *index*, not a directive to read them all. Use the Read tool only on the frames you actually need:
   - "What is the speaker wearing?" → read 1-2 frames near the start
   - "What does the slide at 3:42 say?" → read the single frame closest to 3:42
   - "Describe the visuals throughout" → read every 4th frame or so
   - Vision-only mode (no transcript) → start with ~6-8 evenly-spaced frames, then drill in
4. **Answer the user's question.** Cite timestamps from the transcript or frames when relevant: "At [02:14], …".
5. **Clean up.** When done with the conversation about this video, delete the work directory shown at the bottom of the summary: `rm -rf <work_dir>`.

## Token discipline

Reading a frame costs ~1k tokens (low-res mode for 384px) to ~1.5k+ for higher resolutions. Don't load all frames if the transcript answers the question.

If a video is over ~15 minutes, prefer narrowing with `--start`/`--end` before running the script, especially if the user asked about a specific segment.

## Examples

**User:** "Summarize https://youtu.be/abc123"

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/watch.py" "https://youtu.be/abc123"
```

Read transcript, summarize. Don't load any frames unless the user asks about visuals.

**User:** "What's on the slide at 5:30 in this talk: <url>"

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/watch.py" "<url>" --start 5:00 --end 6:00 --resolution 768
```

Find the frame closest to 5:30 in the output, read it, transcribe slide contents.

**User:** "Describe what happens in the last 30s of /Users/me/clip.mp4"

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/watch.py" /Users/me/clip.mp4 --start <duration-30s>
```

(First run with no `--start` to see the duration if unknown, then re-run.)

## Setup

`watch.py` auto-installs `ffmpeg` and `yt-dlp` on first run via the bundled `setup.sh` (Homebrew on macOS, apt/dnf/pacman on Linux). You don't need to run anything manually.

If auto-install fails (e.g., Homebrew missing on macOS), the script prints the actual error — relay it to the user and tell them to install Homebrew from https://brew.sh, then try again. Don't try to bypass with `--no-install` unless the user asks.
