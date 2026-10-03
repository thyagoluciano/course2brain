"""Module for cleaning and normalizing subtitles and transcriptions (WebVTT / SRT / YouTube)."""

from __future__ import annotations

import logging
import re
import urllib.request

logger = logging.getLogger(__name__)


def _group_text_into_paragraphs(full_text: str, target_paragraph_len: int = 400) -> str:
    """Format single string of sentences into naturally grouped paragraphs."""
    if not full_text:
        return ""

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
        if len(buffer) > target_paragraph_len:
            paragraphs.append(buffer.strip())
            buffer = ""

    if buffer:
        paragraphs.append(buffer.strip())

    return "\n\n".join(paragraphs)


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
    return _group_text_into_paragraphs(full_text)


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


def extract_youtube_id(url_or_id: str) -> str | None:
    """Extract 11-char YouTube video ID from various YouTube URL formats or return raw ID."""
    if not url_or_id:
        return None
    url_str = str(url_or_id).strip()
    match = re.search(r"(?:v=|\/embed\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})", url_str)
    if match:
        return match.group(1)
    if len(url_str) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", url_str):
        return url_str
    return None


def fetch_youtube_transcript(
    media_url_or_id: str,
    languages: tuple[str, ...] = ("pt", "pt-BR", "en"),
) -> str:
    """Download subtitles/transcription from YouTube and return cleaned paragraphs.

    Supports direct video IDs or full URLs, querying YouTube transcript API
    with fallback languages.
    """
    video_id = extract_youtube_id(media_url_or_id)
    if not video_id:
        return ""

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        logger.warning(
            "youtube-transcript-api não está instalado. Não foi possível baixar a transcrição para %s.",
            video_id,
        )
        return ""

    raw_items = None

    # 1. Try direct get_transcript with requested languages
    try:
        raw_items = YouTubeTranscriptApi.get_transcript(video_id, languages=list(languages))
    except Exception as err:
        logger.debug("Tentativa direta de get_transcript falhou para %s: %s", video_id, err)

    # 2. If direct get_transcript failed, inspect available transcripts
    if not raw_items:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                # Find matching language among available transcripts
                t = transcript_list.find_transcript(list(languages))
                raw_items = t.fetch()
            except Exception:
                # Fallback: try finding any generated transcript
                try:
                    for t in transcript_list:
                        raw_items = t.fetch()
                        break
                except Exception:
                    pass
        except Exception as err:
            logger.info("Não foi possível listar transcrições do YouTube para %s: %s", video_id, err)
            return ""

    if not raw_items:
        return ""

    text_parts = [item.get("text", "").strip() for item in raw_items if item.get("text")]
    text_parts = [p for p in text_parts if p]
    if not text_parts:
        return ""

    full_text = " ".join(text_parts)
    return _group_text_into_paragraphs(full_text)
