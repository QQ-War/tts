import html
import re
from typing import Iterable, List

PUNCTUATION = "。？?！!；;，,、：:;\n"


def escape_ssml(text: str) -> str:
    return html.escape(text)


def _split_by_punctuation(text: str) -> Iterable[str]:
    if not text:
        return []
    pattern = f"([{re.escape(PUNCTUATION)}])"
    parts = re.split(pattern, text)
    buffer: List[str] = []
    for part in parts:
        if not part:
            continue
        if part in PUNCTUATION:
            if buffer:
                buffer[-1] += part
            else:
                buffer.append(part)
        else:
            buffer.append(part)
    return buffer


def merge_segments(segments: Iterable[str], max_length: int) -> List[str]:
    merged: List[str] = []
    current = ""
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        if len(current) + len(segment) <= max_length:
            current = f"{current}{segment}" if current else segment
        else:
            if current:
                merged.append(current)
            if len(segment) > max_length:
                merged.extend(_chunk_text(segment, max_length))
                current = ""
            else:
                current = segment
    if current:
        merged.append(current)
    return merged


def _chunk_text(text: str, max_length: int) -> List[str]:
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


def split_text(text: str, max_length: int) -> List[str]:
    if len(text) <= max_length:
        return [text]
    segments = _split_by_punctuation(text)
    return merge_segments(segments, max_length)
