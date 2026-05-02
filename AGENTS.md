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

## Installing without an existing clone

Try these in order — stop at the first one that works:

**1. Claude Code (preferred):**

```
/plugin marketplace add khou/watch-yt
/plugin install claude-watch-yt@watch-yt
```

This is the native path and updates handle themselves. Tell the user to run the two slash commands; you can't invoke them yourself.

**2. Homebrew (macOS / Linuxbrew):**

```bash
brew install khou/watch-yt/watch-yt --HEAD && \
  bash "$(brew --prefix watch-yt)/libexec/install.sh"
```

`brew` is on most users' allowlists; this avoids the raw `curl`/`git clone` paths that the harness sandbox typically denies. Append `--gemini` to the final `install.sh` for Gemini CLI.

**3. Curl one-liner (last resort):**

```bash
mkdir -p ~/.local/share && \
  curl -fsSL https://github.com/khou/watch-yt/archive/refs/heads/main.tar.gz | \
  tar xz -C ~/.local/share && \
  rm -rf ~/.local/share/watch-yt && \
  mv ~/.local/share/watch-yt-main ~/.local/share/watch-yt && \
  bash ~/.local/share/watch-yt/install.sh
```

If both `curl` and `git clone` are denied by the harness, **stop retrying.** Tell the user the network paths are blocked and ask them to run `bash install.sh` from a local clone themselves. Don't paper over a sandbox denial with workarounds.

To update later, re-run whichever path you used; symlinks keep pointing at the install location.

## After install

Once installed, when the user shares a video URL or local file and asks a question, follow the instructions in `SKILL.md`. The first invocation of `scripts/watch.py` auto-installs `ffmpeg`, `yt-dlp`, and `whisper.cpp` via `setup.sh` (Homebrew on macOS, apt/dnf/pacman + source build on Linux) — no further setup needed.

## What this skill does

`watch` analyzes videos using only the user's existing Claude/Cursor/Gemini subscription. It pulls captions from `yt-dlp` when available, transcribes locally with `whisper.cpp` when not, and extracts frames with `ffmpeg`. No third-party transcription service. See `README.md` for details.
