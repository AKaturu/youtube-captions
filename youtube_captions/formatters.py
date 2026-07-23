from __future__ import annotations

import json
from typing import List

from youtube_captions.extractor import Transcript


def _format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def to_text(transcript: Transcript) -> str:
    return " ".join(s.text for s in transcript.snippets)


def to_srt(transcript: Transcript) -> str:
    lines: List[str] = []
    for i, snippet in enumerate(transcript.snippets, 1):
        start = _format_timestamp(snippet.start)
        end = _format_timestamp(snippet.start + snippet.duration)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(snippet.text)
        lines.append("")
    return "\n".join(lines)


def to_vtt(transcript: Transcript) -> str:
    lines: List[str] = ["WEBVTT", ""]
    for i, snippet in enumerate(transcript.snippets, 1):
        start = _format_timestamp_vtt(snippet.start)
        end = _format_timestamp_vtt(snippet.start + snippet.duration)
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(snippet.text)
        lines.append("")
    return "\n".join(lines)


def to_json(transcript: Transcript, indent: int = 2) -> str:
    data = {
        "video_id": transcript.video_id,
        "language": transcript.language,
        "language_code": transcript.language_code,
        "is_generated": transcript.is_generated,
        "snippets": [
            {
                "text": s.text,
                "start": s.start,
                "duration": s.duration,
            }
            for s in transcript.snippets
        ],
    }
    return json.dumps(data, indent=indent, ensure_ascii=False)
