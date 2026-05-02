"""Local transcription via whisper.cpp.

Used as a fallback when a video has no platform-provided captions. Extracts
the audio track with ffmpeg, runs `whisper-cli` to produce a WebVTT file,
and returns its path so the existing captions parser can consume it.

Models live in ~/.cache/watch-yt/models/ and download lazily on first use.
The default `base` model is ~140MB and runs ~5-10x realtime on a modest CPU.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_MODEL = "base"
AVAILABLE_MODELS = ("tiny", "tiny.en", "base", "base.en", "small", "small.en")

_MODEL_BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
CACHE_DIR = Path.home() / ".cache" / "watch-yt"
MODEL_DIR = CACHE_DIR / "models"
LOCAL_BIN = CACHE_DIR / "bin" / "whisper-cli"


def find_binary() -> Optional[str]:
    """Locate whisper-cli on PATH or in our private cache dir."""
    for name in ("whisper-cli", "whisper-cpp"):
        found = shutil.which(name)
        if found:
            return found
    if LOCAL_BIN.is_file():
        return str(LOCAL_BIN)
    return None


def _download_model(model: str) -> Path:
    if model not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unknown model {model!r}. Choose from: {', '.join(AVAILABLE_MODELS)}"
        )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    target = MODEL_DIR / f"ggml-{model}.bin"
    if target.is_file() and target.stat().st_size > 0:
        return target

    url = f"{_MODEL_BASE_URL}/ggml-{model}.bin"
    tmp = target.with_suffix(".bin.partial")
    print(f"Downloading whisper model '{model}' (~one-time setup)...", file=sys.stderr)
    try:
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return target


def _extract_audio(
    video: Path,
    out_path: Path,
    start: Optional[float],
    end: Optional[float],
) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(video)]
    if end is not None and start is not None:
        cmd += ["-t", f"{max(0.0, end - start):.3f}"]
    elif end is not None:
        cmd += ["-to", f"{end:.3f}"]
    cmd += [
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def transcribe(
    video: Path,
    work_dir: Path,
    model: str = DEFAULT_MODEL,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> Optional[Path]:
    """Run whisper.cpp and return a path to the produced .vtt, or None on failure.

    Failure modes are non-fatal — the caller should treat None as "no transcript
    available" and fall back to vision-only analysis.
    """
    binary = find_binary()
    if binary is None:
        print(
            "WARNING: whisper-cli not found; skipping transcription. "
            "Run setup.sh to install it.",
            file=sys.stderr,
        )
        return None

    work_dir.mkdir(parents=True, exist_ok=True)
    audio_path = work_dir / "audio.wav"

    try:
        _extract_audio(video, audio_path, start, end)
    except subprocess.CalledProcessError as e:
        print(f"WARNING: audio extraction failed: {e.stderr or e}", file=sys.stderr)
        return None

    try:
        model_path = _download_model(model)
    except Exception as e:
        print(f"WARNING: failed to fetch whisper model {model!r}: {e}", file=sys.stderr)
        return None

    out_base = work_dir / "transcript"
    cmd = [
        binary,
        "-m", str(model_path),
        "-f", str(audio_path),
        "-ovtt",
        "-of", str(out_base),
        "-l", "auto",
        "-pp",  # print progress to stderr so the caller can see something is happening
    ]
    print(
        f"Transcribing audio with whisper.cpp ({model} model)... "
        "this can take a minute on long videos.",
        file=sys.stderr,
    )
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"WARNING: whisper-cli failed (exit {e.returncode}); skipping transcript.", file=sys.stderr)
        return None
    finally:
        audio_path.unlink(missing_ok=True)

    vtt = out_base.with_suffix(".vtt")
    if not vtt.is_file() or vtt.stat().st_size == 0:
        return None
    return vtt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe a video locally with whisper.cpp.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("./_watch_work"))
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=AVAILABLE_MODELS)
    parser.add_argument("--start", type=float, default=None)
    parser.add_argument("--end", type=float, default=None)
    args = parser.parse_args()

    out = transcribe(args.video, args.out_dir, args.model, args.start, args.end)
    if out is None:
        sys.exit(1)
    print(out)
