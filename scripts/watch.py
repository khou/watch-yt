"""Prepare a video for Claude analysis: download, extract frames, dump transcript.

Outputs a markdown-formatted summary on stdout. Designed to be invoked as a
Claude Code skill — Claude reads the printed paths/transcript and decides
which frames to actually load via the Read tool.

Three modes balance token cost against accuracy:

  fast       — minimum viable visual coverage; captions do the work
  balanced   — sensible default; covers most questions
  accurate   — dense frames + bigger images; for precise visual questions

Each mode picks defaults for max-frames and resolution that depend on
whether captions are available. --max-frames and --resolution still
override the mode preset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Allow `python scripts/watch.py` from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from captions import load_transcript  # noqa: E402
from download import download  # noqa: E402
from frames import auto_fps, extract  # noqa: E402


_TIME = re.compile(r"^(?:(\d+):)?(\d+):(\d+)$|^(\d+(?:\.\d+)?)$")


def parse_time(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    m = _TIME.match(value.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"Bad time: {value!r} (use SS, MM:SS, or HH:MM:SS)")
    h, m_, s, plain = m.groups()
    if plain is not None:
        return float(plain)
    return int(h or 0) * 3600 + int(m_) * 60 + int(s)


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# (frames_with_captions, frames_no_captions, width_with_captions, width_no_captions)
MODE_PRESETS = {
    "fast":     (15, 30, 320, 480),
    "balanced": (25, 50, 384, 512),
    "accurate": (60, 100, 512, 768),
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a video for Claude analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes (token-cost vs. accuracy trade-off):\n"
            "  fast       15-30 frames, 320-480px wide  (~10-20k image tokens)\n"
            "  balanced   25-50 frames, 384-512px wide  (~25-60k image tokens, default)\n"
            "  accurate   60-100 frames, 512-768px wide (~80-200k image tokens)\n"
            "The first number is for videos with captions, the second for vision-only."
        ),
    )
    parser.add_argument("source", help="Video URL or local file path")
    parser.add_argument("--mode", choices=list(MODE_PRESETS), default="balanced",
                        help="Token vs. accuracy preset. Default: balanced.")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Override the mode's frame cap.")
    parser.add_argument("--resolution", type=int, default=None,
                        help="Override the mode's frame width in pixels.")
    parser.add_argument("--start", type=parse_time, default=None, help="Start time (SS, MM:SS, HH:MM:SS).")
    parser.add_argument("--end",   type=parse_time, default=None, help="End time.")
    parser.add_argument("--out-dir", default=None, help="Working directory (default: a temp dir).")
    parser.add_argument("--keep", action="store_true", help="Don't print the cleanup hint.")
    args = parser.parse_args(argv)

    work_dir = Path(args.out_dir).resolve() if args.out_dir else Path(tempfile.mkdtemp(prefix="watch_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        info = download(args.source, work_dir)
    except Exception as e:
        print(f"ERROR: download failed: {e}", file=sys.stderr)
        return 2

    transcript: Optional[str] = None
    if info.captions_vtt:
        try:
            transcript = load_transcript(info.captions_vtt, start=args.start, end=args.end)
            if not transcript.strip():
                transcript = None
        except Exception as e:
            print(f"WARNING: failed to parse captions ({e}); continuing in vision-only mode.", file=sys.stderr)
            transcript = None

    has_captions = transcript is not None
    fc, fnc, wc, wnc = MODE_PRESETS[args.mode]
    max_frames = args.max_frames if args.max_frames is not None else (fc if has_captions else fnc)
    width      = args.resolution if args.resolution is not None else (wc if has_captions else wnc)

    span_start = args.start if args.start is not None else 0.0
    span_end   = args.end   if args.end   is not None else info.duration
    span = max(0.0, span_end - span_start)
    if span <= 0:
        print("ERROR: empty time range", file=sys.stderr)
        return 2

    fps = auto_fps(span, max_frames)
    frames_dir = work_dir / "frames"
    frames = extract(
        video=info.path,
        out_dir=frames_dir,
        duration=info.duration,
        fps=fps,
        width=width,
        start=args.start,
        end=args.end,
    )

    # Markdown summary
    lines: list[str] = []
    lines.append(f"# Video ready: {info.title}")
    lines.append("")
    lines.append("## Metadata")
    lines.append(f"- Source: `{info.source}`")
    if info.uploader:
        lines.append(f"- Uploader: {info.uploader}")
    lines.append(f"- Duration: {_format_time(info.duration)} ({info.duration:.1f}s)")
    if args.start is not None or args.end is not None:
        lines.append(f"- Time range: {_format_time(span_start)} – {_format_time(span_end)} ({span:.1f}s)")
    lines.append(f"- Mode: {args.mode} ({'transcript + vision' if has_captions else 'vision only — no captions'})")
    lines.append(f"- Frames: {len(frames)} @ {width}px wide ({fps:.3f} fps)")
    lines.append(f"- Work dir: `{work_dir}`")
    lines.append("")

    if has_captions:
        lines.append("## Transcript")
        lines.append("```")
        lines.append(transcript or "")
        lines.append("```")
        lines.append("")

    lines.append("## Frames")
    lines.append("Read frames selectively — only sample what the question requires.")
    lines.append("")
    for f in frames:
        lines.append(f"- [{_format_time(f.timestamp)}] `{f.path}`")
    lines.append("")

    if not has_captions:
        lines.append("## Note")
        lines.append("No captions were available, so this video has no transcript. "
                     "All content must be inferred from frames.")
        lines.append("")

    if not args.keep:
        lines.append(f"## Cleanup")
        lines.append(f"When done, run: `rm -rf '{work_dir}'`")
        lines.append("")

    sys.stdout.write("\n".join(lines))
    sys.stdout.flush()

    # Side-channel JSON for programmatic consumers
    summary = {
        "title": info.title,
        "duration": info.duration,
        "has_captions": has_captions,
        "frame_count": len(frames),
        "frame_width": width,
        "fps": fps,
        "work_dir": str(work_dir),
        "frames": [{"t": f.timestamp, "path": str(f.path)} for f in frames],
    }
    (work_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
