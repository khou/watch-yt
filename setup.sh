#!/usr/bin/env bash
# Install ffmpeg and yt-dlp. Idempotent — safe to re-run.

set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1; }

install_macos() {
  if ! need brew; then
    echo "Homebrew is required on macOS. Install from https://brew.sh and re-run." >&2
    exit 1
  fi
  local pkgs=()
  need ffmpeg  || pkgs+=(ffmpeg)
  need yt-dlp  || pkgs+=(yt-dlp)
  if (( ${#pkgs[@]} > 0 )); then
    brew install "${pkgs[@]}"
  fi
}

install_linux() {
  if need apt-get; then
    sudo apt-get update
    sudo apt-get install -y ffmpeg
    need yt-dlp || sudo pip3 install --break-system-packages yt-dlp || pip3 install --user yt-dlp
  elif need dnf; then
    sudo dnf install -y ffmpeg yt-dlp
  elif need pacman; then
    sudo pacman -S --noconfirm ffmpeg yt-dlp
  else
    echo "Unsupported Linux distro. Install ffmpeg and yt-dlp manually." >&2
    exit 1
  fi
}

case "$(uname -s)" in
  Darwin) install_macos ;;
  Linux)  install_linux ;;
  *) echo "Unsupported OS: $(uname -s). Install ffmpeg and yt-dlp manually." >&2; exit 1 ;;
esac

echo
echo "Installed:"
for cmd in ffmpeg ffprobe yt-dlp; do
  if need "$cmd"; then
    printf "  %-8s %s\n" "$cmd" "$(command -v "$cmd")"
  else
    printf "  %-8s MISSING\n" "$cmd"
  fi
done
