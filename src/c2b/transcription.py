"""Module for cleaning and normalizing subtitles and transcriptions (WebVTT / SRT)."""

from __future__ import annotations

import re
import urllib.request


def clean_vtt(content: str) -> str:
    """Convert raw WebVTT or SRT content into clean, readable text paragraphs."""
    if not content:
        return ""

    lines = content.splitlines()
    text_lines = []
    prev_line = ""

    # Timestamp pattern: 00:00.000 --> 00:05.000 or 00:00:00.000 --> 00:00:05.000
    timestamp_regex = re.compile(
        r"\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}"
    )
    # Pattern to strip style/cue tags like <c.color>, <v Voice>, etc.
    tag_regex = re.compile(r"<[^>]+>")

    skip_block = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            skip_block = False
            continue

        if (
            stripped.startswith("WEBVTT")
            or stripped.startswith("NOTE")
            or stripped.startswith("STYLE")
        ):
            skip_block = True
            continue

        if skip_block:
            continue

        # Skip numeric cue identifiers
        if stripped.isdigit():
            continue

        # Skip timestamp lines
        if timestamp_regex.search(stripped):
            continue

        # Clean HTML/VTT tags
        cleaned = tag_regex.sub("", stripped).strip()

        # Deduplicate consecutive identical lines (common in dynamic rolling captions)
        if cleaned and cleaned != prev_line:
            text_lines.append(cleaned)
            prev_line = cleaned

    if not text_lines:
        return ""

    full_text = " ".join(text_lines)
    sentences = re.split(r"([.!?]+(?:\s+|$))", full_text)
    paragraphs = []
    buffer = ""

    i = 0
    while i < len(sentences):
        part = sentences[i]
        if i + 1 < len(sentences):
            punct = sentences[i + 1]
            sent = part + punct
            i += 2
        else:
            sent = part
            i += 1

        if not sent.strip():
            continue

        buffer += (" " if buffer else "") + sent.strip()
        if len(buffer) > 400:  # ~1 paragraph length
            paragraphs.append(buffer.strip())
            buffer = ""

    if buffer:
        paragraphs.append(buffer.strip())

    return "\n\n".join(paragraphs)


def fetch_and_clean_vtt(url_vtt: str) -> str:
    """Download .vtt from URL and return cleaned, paragraph-formatted text."""
    if not url_vtt:
        return ""

    req = urllib.request.Request(
        url_vtt,
        headers={"User-Agent": "Mozilla/5.0 (course2brain/0.1.0)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read().decode("utf-8", errors="ignore")
            return clean_vtt(content)
    except Exception as e:
        return f"[Erro ao baixar transcrição: {e}]"
