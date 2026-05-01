"""Extract frames from a video at an adaptive FPS using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Frame:
    path: Path
    timestamp: float  # seconds from start of video


def auto_fps(duration: float, max_frames: int) -> float:
    """Frame rate that yields ~max_frames over the span. Capped at 2 fps.

    The caller has already set max_frames based on whether captions exist;
    this just spreads them evenly.
    """
    if duration <= 0:
        return 1.0
    fps = max_frames / duration
    return max(0.05, min(fps, 2.0))


def _hms(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract(
    video: Path,
    out_dir: Path,
    duration: float,
    fps: float,
    width: int = 512,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> list[Frame]:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not installed. Run setup.sh.")

    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "frame_%05d.jpg"

    start_s = float(start) if start is not None else 0.0
    end_s = float(end) if end is not None else duration
    span = max(0.0, end_s - start_s)
    if span <= 0:
        raise ValueError("Empty time range")

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if start is not None:
        cmd += ["-ss", _hms(start_s)]
    cmd += ["-i", str(video)]
    if end is not None:
        cmd += ["-t", f"{span:.3f}"]
    cmd += [
        "-vf", f"fps={fps},scale={width}:-2:flags=lanczos",
        "-q:v", "4",
        str(pattern),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    files = sorted(out_dir.glob("frame_*.jpg"))
    if not files:
        return []

    # ffmpeg samples at fps starting from t=0 of the input (after -ss),
    # so frame N corresponds to t = start_s + N/fps.
    frames = [Frame(path=p, timestamp=start_s + i / fps) for i, p in enumerate(files)]
    return frames
