"""Parse a WebVTT file into compact `[MM:SS] text` lines.

YouTube auto-captions use rolling cues — each phrase appears 2-3 times as
it scrolls onto the screen. We dedup aggressively to save tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
_TAG = re.compile(r"<[^>]+>")


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _ts_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _parse_vtt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    cur_start: Optional[float] = None
    cur_end: Optional[float] = None
    cur_lines: list[str] = []

    def flush():
        nonlocal cur_start, cur_end, cur_lines
        if cur_start is not None and cur_lines:
            joined = " ".join(line.strip() for line in cur_lines if line.strip())
            joined = _TAG.sub("", joined).strip()
            if joined:
                cues.append(Cue(cur_start, cur_end or cur_start, joined))
        cur_start = cur_end = None
        cur_lines = []

    for raw in text.splitlines():
        line = raw.rstrip()
        m = _TS.search(line)
        if m:
            flush()
            cur_start = _ts_to_seconds(*m.group(1, 2, 3, 4))
            cur_end = _ts_to_seconds(*m.group(5, 6, 7, 8))
        elif not line:
            flush()
        elif line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
            continue
        elif cur_start is not None:
            cur_lines.append(line)
    flush()
    return cues


def _dedupe(cues: list[Cue]) -> list[Cue]:
    """YouTube rolling captions: a cue is often a prefix of the next.

    Strategy: walk cues, suppress any cue whose text is a prefix of the
    next cue's text — keep the longer, later one with extended end-time.
    """
    if not cues:
        return cues

    out: list[Cue] = []
    for cue in cues:
        if out:
            prev = out[-1]
            if cue.text == prev.text:
                prev.end = max(prev.end, cue.end)
                continue
            if cue.text.startswith(prev.text + " ") or cue.text.startswith(prev.text):
                # The new cue absorbs the previous — extend the start back
                merged = Cue(start=prev.start, end=max(prev.end, cue.end), text=cue.text)
                out[-1] = merged
                continue
            if prev.text.startswith(cue.text + " ") or prev.text.startswith(cue.text):
                # Previous already covers this cue's text
                prev.end = max(prev.end, cue.end)
                continue
        out.append(Cue(start=cue.start, end=cue.end, text=cue.text))
    return out


def _format_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def load_transcript(
    vtt_path: Path,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> str:
    raw = vtt_path.read_text(encoding="utf-8", errors="replace")
    cues = _dedupe(_parse_vtt(raw))
    if start is not None:
        cues = [c for c in cues if c.end >= start]
    if end is not None:
        cues = [c for c in cues if c.start <= end]
    return "\n".join(f"[{_format_time(c.start)}] {c.text}" for c in cues)


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1])
    print(load_transcript(path))
