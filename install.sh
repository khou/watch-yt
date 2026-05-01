#!/usr/bin/env bash
# Symlink this repo into the standard skill locations so Claude Code,
# Cursor, and (optionally) Gemini CLI auto-discover it. Idempotent.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

link() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  if [ -L "$target" ]; then
    if [ "$(readlink "$target")" = "$REPO" ]; then
      echo "  already linked  $target"
      return
    fi
    echo "  replacing       $target  ->  $REPO"
    rm "$target"
  elif [ -e "$target" ]; then
    echo "  ERROR: $target exists and is not a symlink. Move or delete it, then re-run." >&2
    exit 1
  else
    echo "  linking         $target  ->  $REPO"
  fi
  ln -s "$REPO" "$target"
}

# ~/.claude/skills/watch covers Claude Code AND Cursor (legacy compat).
link "$HOME/.claude/skills/watch"

# Gemini uses a different path; only do it if asked.
if [ "${1:-}" = "--gemini" ] || [ "${1:-}" = "-g" ]; then
  link "$HOME/.gemini/extensions/watch"
  echo
  echo "Gemini CLI: also add the contents of prompts/gemini.md to ~/.gemini/GEMINI.md"
fi

echo
echo "Done. The 'watch' skill is now available."
