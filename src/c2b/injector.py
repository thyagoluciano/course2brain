"""Atomic and idempotent injection of connections into Obsidian Markdown notes."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import List, Set, Tuple

SECTION_TITLE = "## 🔗 Conexões Relacionadas"
RE_SECTION = re.compile(r"(?m)^##\s*(?:🔗\s*)?Conexões(?:\s+Relacionadas)?\b")
RE_WIKILINK = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")
RE_FINAL_SECTION = re.compile(r"(?m)^(?:---\s*\n)?##\s*📝\s*Transcrição")


def extract_wikilinks(text: str) -> Set[str]:
    """Extract destination note names from wikilinks in text."""
    targets: Set[str] = set()
    for m in RE_WIKILINK.finditer(text):
        target = m.group(1).strip()
        clean = target.removesuffix(".md").strip().lower()
        if clean:
            targets.add(clean)
    return targets


def inject_connections_into_markdown(
    content: str,
    new_connections: List[Tuple[str, str]],
) -> str:
    """Inject new connections into the '## 🔗 Conexões Relacionadas' section idempotently.

    `new_connections`: list of (target_note_name, rationale) tuples.
    """
    if not new_connections:
        return content

    match_section = RE_SECTION.search(content)

    if match_section:
        start_pos = match_section.start()
        rest = content[match_section.end() :]
        match_next = re.search(r"(?m)^##\s+", rest)
        end_pos = match_section.end() + match_next.start() if match_next else len(content)

        section_content = content[start_pos:end_pos]
        existing_links = extract_wikilinks(section_content)

        new_lines: List[str] = []
        for target, reason in new_connections:
            clean_target = target.removesuffix(".md").strip()
            if clean_target.lower() not in existing_links:
                reason_fmt = f": {reason.strip()}" if reason.strip() else ""
                new_lines.append(f"- [[{clean_target}]]{reason_fmt}")
                existing_links.add(clean_target.lower())

        if not new_lines:
            return content

        updated_section = section_content.rstrip() + "\n" + "\n".join(new_lines) + "\n\n"
        return content[:start_pos] + updated_section + content[end_pos:].lstrip("\n")

    # Section does not exist: avoid duplicating links present anywhere in the note
    body_links = extract_wikilinks(content)
    new_lines = []
    for target, reason in new_connections:
        clean_target = target.removesuffix(".md").strip()
        if clean_target.lower() not in body_links:
            reason_fmt = f": {reason.strip()}" if reason.strip() else ""
            new_lines.append(f"- [[{clean_target}]]{reason_fmt}")
            body_links.add(clean_target.lower())

    if not new_lines:
        return content

    new_block = f"{SECTION_TITLE}\n" + "\n".join(new_lines) + "\n"

    # If raw transcription section exists at the end, insert before it
    match_transcription = RE_FINAL_SECTION.search(content)
    if match_transcription:
        pos = match_transcription.start()
        return content[:pos].rstrip() + "\n\n" + new_block + "\n" + content[pos:].lstrip()

    return content.rstrip() + "\n\n" + new_block


def atomic_save_markdown(file_path: Path, content: str) -> None:
    """Save file atomically using a temporary file in the same directory."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = file_path.parent
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=temp_dir,
        prefix=".tmp_c2b_",
        suffix=".md",
        delete=False,
    ) as f:
        f.write(content)
        temp_name = f.name

    os.replace(temp_name, file_path)


def apply_connections_to_file(
    file_path: Path,
    new_connections: List[Tuple[str, str]],
) -> bool:
    """Read, inject connections and save atomically if changed. Returns True if updated."""
    if not file_path.is_file():
        return False

    original = file_path.read_text(encoding="utf-8")
    updated = inject_connections_into_markdown(original, new_connections)

    if updated != original:
        atomic_save_markdown(file_path, updated)
        return True

    return False
