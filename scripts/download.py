"""Download a video (and auto-captions, when available) via yt-dlp.

Local files are probed with ffprobe and returned as-is.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VideoInfo:
    path: Path
    captions_vtt: Optional[Path]
    title: str
    uploader: str
    duration: float
    source: str
    is_local: bool


def _run(cmd: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)


def _ffprobe_duration(path: Path) -> float:
    out = _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]).stdout
    return float(json.loads(out)["format"]["duration"])


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _pick_caption_file(work_dir: Path, basename: str) -> Optional[Path]:
    """Prefer en > en-US > en-GB > any .vtt in the dir."""
    candidates = sorted(work_dir.glob(f"{basename}*.vtt"))
    if not candidates:
        return None
    for pref in ("en.vtt", "en-US.vtt", "en-GB.vtt"):
        for c in candidates:
            if c.name.endswith(f".{pref}") or c.name.endswith(pref):
                return c
    return candidates[0]


def download(source: str, work_dir: Path) -> VideoInfo:
    """Resolve a URL or local path into a VideoInfo with frames-ready video file."""
    work_dir.mkdir(parents=True, exist_ok=True)

    if not _is_url(source):
        local = Path(source).expanduser().resolve()
        if not local.is_file():
            raise FileNotFoundError(f"Local video not found: {source}")
        return VideoInfo(
            path=local,
            captions_vtt=None,
            title=local.stem,
            uploader="",
            duration=_ffprobe_duration(local),
            source=str(local),
            is_local=True,
        )

    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp not installed. Run setup.sh.")

    # Cap height at 720p — frames get downscaled anyway, no need to pull 4K.
    out_template = str(work_dir / "video.%(ext)s")
    fmt = "bv*[height<=720]+ba/b[height<=720]/best[height<=720]/best"

    # 1) Video + metadata (must succeed)
    _run([
        "yt-dlp",
        "--no-playlist",
        "--restrict-filenames",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--write-info-json",
        "--no-write-subs",
        "--no-write-auto-subs",
        "-o", out_template,
        source,
    ])

    # 2) Captions (best-effort — many videos have none, and YT sometimes 429s
    #    on the auto-translated variants). We want manual `en` first, then
    #    auto `en`. Skip translated locales like `en-de` to avoid 429s.
    for sub_args in (
        ["--write-subs",      "--sub-langs", "en"],
        ["--write-auto-subs", "--sub-langs", "en"],
    ):
        try:
            _run([
                "yt-dlp",
                "--no-playlist",
                "--skip-download",
                "--sub-format", "vtt",
                "--convert-subs", "vtt",
                "-o", out_template,
                *sub_args,
                source,
            ])
            if list(work_dir.glob("video*.vtt")):
                break
        except subprocess.CalledProcessError:
            continue

    video_files = sorted(p for p in work_dir.glob("video.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"})
    if not video_files:
        raise RuntimeError("yt-dlp did not produce a video file")
    video_path = video_files[0]

    info_path = work_dir / "video.info.json"
    info: dict = {}
    if info_path.is_file():
        info = json.loads(info_path.read_text())

    captions = _pick_caption_file(work_dir, "video")

    return VideoInfo(
        path=video_path,
        captions_vtt=captions,
        title=info.get("title") or video_path.stem,
        uploader=info.get("uploader") or info.get("channel") or "",
        duration=float(info.get("duration") or _ffprobe_duration(video_path)),
        source=source,
        is_local=False,
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--out", default="./_watch_work")
    args = parser.parse_args()

    info = download(args.source, Path(args.out))
    print(json.dumps({
        "path": str(info.path),
        "captions": str(info.captions_vtt) if info.captions_vtt else None,
        "title": info.title,
        "uploader": info.uploader,
        "duration": info.duration,
        "is_local": info.is_local,
    }, indent=2))
