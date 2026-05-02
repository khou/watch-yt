#!/usr/bin/env bash
# Install ffmpeg, yt-dlp, and whisper.cpp. Idempotent — safe to re-run.

set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1; }

WHISPER_BIN_DIR="$HOME/.cache/watch-yt/bin"
WHISPER_SRC_DIR="$HOME/.cache/watch-yt/whisper.cpp"

have_whisper() {
  need whisper-cli || need whisper-cpp || [[ -x "$WHISPER_BIN_DIR/whisper-cli" ]]
}

install_macos() {
  if ! need brew; then
    echo "Homebrew is required on macOS. Install from https://brew.sh and re-run." >&2
    exit 1
  fi
  local pkgs=()
  need ffmpeg     || pkgs+=(ffmpeg)
  need yt-dlp     || pkgs+=(yt-dlp)
  have_whisper    || pkgs+=(whisper-cpp)
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
    echo "Unsupported Linux distro. Install ffmpeg, yt-dlp, and (optionally) whisper.cpp manually." >&2
    exit 1
  fi

  have_whisper || install_whisper_linux || true
}

install_whisper_linux() {
  # Most distros don't package whisper.cpp — build from source into a private cache dir.
  local missing=()
  for t in git cmake make g++; do
    need "$t" || missing+=("$t")
  done
  if (( ${#missing[@]} > 0 )); then
    echo "Skipping whisper.cpp install: missing build tools (${missing[*]})." >&2
    echo "Install them via your package manager and re-run setup.sh, or transcription will be unavailable." >&2
    return 1
  fi

  mkdir -p "$WHISPER_BIN_DIR"
  if [[ ! -d "$WHISPER_SRC_DIR" ]]; then
    git clone --depth=1 https://github.com/ggerganov/whisper.cpp "$WHISPER_SRC_DIR"
  else
    git -C "$WHISPER_SRC_DIR" pull --ff-only || true
  fi

  (cd "$WHISPER_SRC_DIR" \
    && cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null \
    && cmake --build build -j --target whisper-cli >/dev/null)

  local built
  built="$(find "$WHISPER_SRC_DIR/build" -name whisper-cli -type f -perm -u+x | head -n1)"
  if [[ -z "$built" ]]; then
    echo "whisper.cpp build did not produce a whisper-cli binary." >&2
    return 1
  fi
  cp "$built" "$WHISPER_BIN_DIR/whisper-cli"
  echo "whisper-cli installed at $WHISPER_BIN_DIR/whisper-cli"
}

case "$(uname -s)" in
  Darwin) install_macos ;;
  Linux)  install_linux ;;
  *) echo "Unsupported OS: $(uname -s). Install ffmpeg, yt-dlp, and (optionally) whisper.cpp manually." >&2; exit 1 ;;
esac

echo
echo "Installed:"
for cmd in ffmpeg ffprobe yt-dlp; do
  if need "$cmd"; then
    printf "  %-12s %s\n" "$cmd" "$(command -v "$cmd")"
  else
    printf "  %-12s MISSING\n" "$cmd"
  fi
done
if need whisper-cli; then
  printf "  %-12s %s\n" "whisper-cli" "$(command -v whisper-cli)"
elif need whisper-cpp; then
  printf "  %-12s %s\n" "whisper-cpp" "$(command -v whisper-cpp)"
elif [[ -x "$WHISPER_BIN_DIR/whisper-cli" ]]; then
  printf "  %-12s %s\n" "whisper-cli" "$WHISPER_BIN_DIR/whisper-cli"
else
  printf "  %-12s MISSING (transcription disabled — caption-less videos go to vision-only)\n" "whisper-cli"
fi
