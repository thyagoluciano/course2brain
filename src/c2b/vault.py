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

    frontmatter = f"""---
tipo: aula
curso: "{course_name}"
aula: "{title}"
plataforma: "{platform}"
data_estudo: {today}
url_origem: "{page_url}"
arquivo_midia: "{local_media_str}"
tags:
{tags_yaml}
status: concluido
---"""

    header = f"""# {title}

> [!INFO] Metadados da Aula
> - **Curso:** [[{course_name}]]
> - **Plataforma:** {web_link_md}
> - **Mídia Local:** {local_media_md}
"""

    body = summary_content.strip()

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
    if raw_transcription.strip():
        transcription_section = f"""
---
## 📝 Transcrição & Notas Brutas
<details>
<summary>Clique para expandir a transcrição completa da aula</summary>

{raw_transcription.strip()}

</details>
"""

    return f"{frontmatter}\n\n{header}\n{body}{links_section}{transcription_section}".strip() + "\n"


def update_course_moc(course_dir: Path, course_name: str) -> Path:
    """Generate or update the Course Map of Content (MOC) index."""
    moc_path = course_dir / f"_Indice - {sanitize_filename(course_name)}.md"
    lessons = sorted([f.stem for f in course_dir.glob("*.md") if not f.name.startswith("_")])

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
        f"> Mapa de Conteúdo (MOC) do curso. Total de aulas registradas: **{len(lessons)}**.",
        "",
        "## 📑 Aulas Disponíveis",
        "",
    ]

    for lesson in lessons:
        lines.append(f"- [[{lesson}]]")

    lines.append("")
    moc_path.write_text("\n".join(lines), encoding="utf-8")
    return moc_path


def save_lesson_note(
    vault_path: Path,
    courses_folder: str,
    course_name: str,
    title: str,
    content: str,
) -> Path:
    """Save lesson note inside `<vault>/<courses_folder>/<course_name>/<title>.md`."""
    target_dir = vault_path / courses_folder / sanitize_filename(course_name)
    target_dir.mkdir(parents=True, exist_ok=True)

    note_path = target_dir / f"{sanitize_filename(title)}.md"
    note_path.write_text(content, encoding="utf-8")

    # Keep MOC updated
    update_course_moc(target_dir, course_name)

    return note_path
