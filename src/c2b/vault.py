"""Module for formatting and atomic saving of Second Brain notes and MOCs in Obsidian."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import List, Optional


def sanitize_filename(name: str) -> str:
    """Sanitize string to be safe for filenames across Windows, macOS and Linux."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "Sem_Titulo"


def _extract_youtube_id(url: Optional[str]) -> Optional[str]:
    """Extract 11-character YouTube video ID from URL if present."""
    if not url:
        return None
    match = re.search(r"(?:v=|\/embed\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def format_lesson_note(
    title: str,
    course_name: str,
    platform: str,
    summary_content: str,
    page_url: str = "",
    local_media_path: Optional[str | Path] = None,
    raw_transcription: str = "",
    links: Optional[List[dict[str, str]]] = None,
    additional_tags: Optional[List[str]] = None,
    media_url: Optional[str] = None,
    space_name: Optional[str] = None,
    section_name: Optional[str] = None,
) -> str:
    """Format full markdown note according to Second Brain standards."""
    clean_course_tag = re.sub(r"[^a-zA-Z0-9_\-]", "", course_name.lower().replace(" ", "-"))
    tags = ["curso", "aula", "second-brain"]
    if clean_course_tag and clean_course_tag not in tags:
        tags.append(f"curso/{clean_course_tag}")

    if additional_tags:
        for t in additional_tags:
            clean_t = t.strip().lstrip("#")
            if clean_t and clean_t not in tags:
                tags.append(clean_t)

    tags_yaml = "\n".join(f"  - {t}" for t in tags)
    today = date.today().isoformat()

    local_media_str = ""
    local_media_md = "Nenhum arquivo local baixado"
    if local_media_path:
        p = Path(local_media_path).expanduser().resolve()
        local_media_str = str(p)
        if p.exists():
            local_media_md = f"[Assistir Vídeo (Local)](file://{p})"

    web_link_md = f"[Acessar Aula na Web]({page_url})" if page_url else "Nenhum link web informado"

    yt_id = _extract_youtube_id(media_url)
    video_embed_section = ""
    video_link_md = ""
    if yt_id:
        canonical_yt_url = (
            media_url
            if "youtube.com" in media_url or "youtu.be" in media_url
            else f"https://www.youtube.com/watch?v={yt_id}"
        )
        video_link_md = f"[Assistir no YouTube ↗]({canonical_yt_url})"
        video_embed_section = f"""## 📺 Vídeo da Aula
<iframe width="100%" height="380" src="https://www.youtube.com/embed/{yt_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

---

"""
    elif media_url and media_url.startswith("http"):
        video_link_md = f"[Assistir Vídeo Online ↗]({media_url})"

    extra_yaml = []
    if space_name:
        extra_yaml.append(f'parte: "{space_name}"')
    if section_name:
        extra_yaml.append(f'topico: "{section_name}"')
    if media_url:
        extra_yaml.append(f'video_url: "{media_url}"')
    extra_yaml_str = ("\n" + "\n".join(extra_yaml)) if extra_yaml else ""

    frontmatter = f"""---
tipo: aula
curso: "{course_name}"
aula: "{title}"
plataforma: "{platform}"
data_estudo: {today}
url_origem: "{page_url}"{extra_yaml_str}
arquivo_midia: "{local_media_str}"
tags:
{tags_yaml}
status: concluido
---"""

    header_items = [
        f"> - **Curso:** [[{course_name}]]",
    ]
    if space_name:
        header_items.append(f"> - **Parte:** {space_name}")
    if section_name:
        header_items.append(f"> - **Tópico:** {section_name}")
    header_items.append(f"> - **Plataforma:** {web_link_md}")
    if video_link_md:
        header_items.append(f"> - **Vídeo:** {video_link_md}")
    if local_media_path:
        header_items.append(f"> - **Mídia Local:** {local_media_md}")

    header = (
        f"""# {title}

> [!INFO] Metadados da Aula
"""
        + "\n".join(header_items)
        + "\n"
    )

    safe_summary = (summary_content or "").strip()
    body = (video_embed_section + safe_summary).strip()

    links_section = ""
    if links:
        link_lines = []
        for item in links:
            txt = item.get("texto", "").strip() or "Link de Referência"
            url = item.get("url", "").strip()
            if url:
                link_lines.append(f"- [{txt}]({url})")
        if link_lines:
            links_section = (
                "\n\n## 🔗 Links e Materiais de Referência\n" + "\n".join(link_lines) + "\n"
            )

    transcription_section = ""
    raw_clean = (raw_transcription or "").strip()
    if raw_clean:
        transcription_section = f"""
---
## 📝 Transcrição & Notas Brutas
<details>
<summary>Clique para expandir a transcrição completa da aula</summary>

{raw_clean}

</details>
"""

    return f"{frontmatter}\n\n{header}\n{body}{links_section}{transcription_section}".strip() + "\n"


def update_course_moc(course_dir: Path, course_name: str) -> Path:
    """Generate or update the Course Map of Content (MOC) index."""
    moc_path = course_dir / f"_Indice - {sanitize_filename(course_name)}.md"
    lesson_files = sorted(
        [
            f
            for f in course_dir.rglob("*.md")
            if not f.name.startswith("_") and not f.name.startswith(".")
        ]
    )

    lines = [
        "---",
        "tipo: moc",
        f'curso: "{course_name}"',
        "tags:",
        "  - curso",
        "  - moc",
        "---",
        "",
        f"# 📚 {course_name} (Índice de Aulas)",
        "",
        f"> Mapa de Conteúdo (MOC) do curso. Total de aulas registradas: **{len(lesson_files)}**.",
        "",
        "## 📑 Aulas Disponíveis",
        "",
    ]

    modules: dict[str, list[str]] = {}
    for f in lesson_files:
        try:
            rel = f.parent.relative_to(course_dir)
            mod_name = str(rel) if str(rel) != "." else ""
        except ValueError:
            mod_name = ""
        modules.setdefault(mod_name, []).append(f.stem)

    if len(modules) == 1 and "" in modules:
        for lesson in modules[""]:
            lines.append(f"- [[{lesson}]]")
    else:
        current_space = None
        for mod, lessons in modules.items():
            if not mod:
                for lesson in lessons:
                    lines.append(f"- [[{lesson}]]")
                continue

            parts = Path(mod).parts
            if len(parts) == 1:
                lines.append(f"### {parts[0]}")
            elif len(parts) >= 2:
                space, section = parts[0], parts[1]
                if space != current_space:
                    lines.append(f"### {space}")
                    lines.append("")
                    current_space = space
                lines.append(f"#### {section}")

            for lesson in lessons:
                lines.append(f"- [[{lesson}]]")
            lines.append("")

    lines.append("")
    moc_path.write_text("\n".join(lines), encoding="utf-8")
    return moc_path


def resolve_existing_dir(parent: Path, name: str) -> Path:
    """Find existing child folder matching name case-insensitively, or return parent / name."""
    if parent.is_dir():
        name_lower = name.lower()
        try:
            for child in parent.iterdir():
                if child.is_dir() and child.name.lower() == name_lower:
                    return child
        except Exception:
            pass
    target = parent / name
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_lesson_note(
    vault_path: Path,
    courses_folder: str,
    course_name: str,
    title: str,
    content: str,
    space_name: Optional[str] = None,
    section_name: Optional[str] = None,
) -> Path:
    """Save lesson note inside `<vault>/<courses_folder>/<course_name>/[<space_name>/][<section_name>/]<title>.md`."""
    courses_dir = vault_path / courses_folder
    courses_dir.mkdir(parents=True, exist_ok=True)

    course_dir = resolve_existing_dir(courses_dir, sanitize_filename(course_name))

    current_dir = course_dir
    if space_name:
        current_dir = resolve_existing_dir(current_dir, sanitize_filename(space_name))
    if section_name:
        current_dir = resolve_existing_dir(current_dir, sanitize_filename(section_name))

    note_path = current_dir / f"{sanitize_filename(title)}.md"
    note_path.write_text(content, encoding="utf-8")

    # Keep MOC updated at root course folder
    update_course_moc(course_dir, course_name)

    return note_path


def list_vault_folders(vault_path: Path | str, max_depth: int = 2) -> list[str]:
    """List available top-level and subfolder directories in the vault, ignoring system dirs."""
    root = Path(vault_path).expanduser().resolve()
    if not root.is_dir():
        return []

    ignored = {".obsidian", "_sistema", ".trash", ".git", "__pycache__"}
    result: list[str] = []

    def _scan(current: Path, depth: int):
        if depth > max_depth:
            return
        try:
            for child in sorted(current.iterdir(), key=lambda p: p.name.lower()):
                if child.is_dir() and child.name not in ignored and not child.name.startswith("."):
                    rel = str(child.relative_to(root))
                    result.append(rel)
                    _scan(child, depth + 1)
        except Exception:
            pass

    _scan(root, 1)
    return result
