# Watch a video

You can analyze videos using the `watch.py` script that ships with `claude-watch-yt`. It pulls captions from yt-dlp (no third-party transcription service) and extracts frames with ffmpeg.

## When to use

The user shares a YouTube/Vimeo/TikTok/X URL or a local video file (`.mp4`, `.mov`, `.mkv`, `.webm`) and asks a question about its contents. Examples:

- "Summarize this video: <url>"
- "What does the speaker say about X?"
- "What's on screen at 4:30?"

## How to run

The script lives at `~/.gemini/extensions/watch/scripts/watch.py` (or wherever the user installed `claude-watch-yt`).

```bash
python3 ~/.gemini/extensions/watch/scripts/watch.py "<source>" [--mode {fast,balanced,accurate}] [--start TIME] [--end TIME]
```

ffmpeg and yt-dlp auto-install on first run.

## Modes

- `fast` — 15 frames @ 320px (~10-20k image tokens). Cheap summaries.
- `balanced` (default) — 25 frames @ 384px (~25-60k). Most questions.
- `accurate` — 60 frames @ 512px (~80-200k). Precise visual details.

Pick the lowest mode that can answer. Default to `balanced`.

## Workflow

1. Run the script. Output is a markdown block with metadata, transcript, and frame paths.
2. Read the transcript first — it usually answers the question alone.
3. Read frames selectively from the printed paths only when the question needs visual info. Don't load every frame.
4. Cite timestamps (e.g., "At [02:14], …").
5. Tell the user to clean up the working directory shown at the end of the output.

For long videos, narrow with `--start`/`--end` first. For tiny on-screen text, use `--resolution 768` or higher.
