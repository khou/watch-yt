# Agent instructions

If the user has just opened this repo and says anything like "set this up", "install this", "make this work", or similar, perform the install:

1. Find the absolute path of this repo (the directory containing this `AGENTS.md`).
2. Create a symlink from `~/.claude/skills/watch` to that path:
   ```bash
   ln -s "<repo-abs-path>" "$HOME/.claude/skills/watch"
   ```
   - If `~/.claude/skills/watch` already exists and points to this repo, skip.
   - If it exists but points elsewhere, ask the user before replacing.
   - Make sure `~/.claude/skills/` exists (`mkdir -p`).
3. If the user mentions Gemini CLI, also create `~/.gemini/extensions/watch` pointing at this repo, and tell them to append the contents of `prompts/gemini.md` to their `~/.gemini/GEMINI.md`.
4. Confirm to the user: the `watch` skill is now installed. They can ask about a video URL in any new session.

There's a `bash install.sh` that does the same thing — feel free to run it instead of doing the steps manually.

## After install

Once installed, when the user shares a video URL or local file and asks a question, follow the instructions in `SKILL.md`. The first invocation of `scripts/watch.py` auto-installs `ffmpeg` and `yt-dlp` via `setup.sh` (Homebrew on macOS, apt/dnf/pacman on Linux) — no further setup needed.

## What this skill does

`watch` analyzes videos using only the user's existing Claude/Cursor/Gemini subscription. It pulls captions from `yt-dlp` (no third-party transcription service) and extracts frames with `ffmpeg`. See `README.md` for details.
