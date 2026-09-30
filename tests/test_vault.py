from pathlib import Path

from c2b.vault import (
    format_lesson_note,
    sanitize_filename,
    save_lesson_note,
)


def test_sanitize_filename():
    assert sanitize_filename("01: Introdução / Setup?") == "01 Introdução Setup"
    assert sanitize_filename("   Aula * Especial <V1> |   ") == "Aula Especial V1"
    assert sanitize_filename("") == "Sem_Titulo"


def test_format_lesson_note():
    md = format_lesson_note(
        title="Fundamentos de CQRS",
        course_name="Arquitetura Avançada",
        platform="Circle.so",
        summary_content="## 📌 Resumo Executivo\nCQRS separa leitura e escrita.",
        page_url="https://app.circle.so/lesson/1",
        raw_transcription="Transcrição de teste",
        links=[{"texto": "Martin Fowler CQRS", "url": "https://martinfowler.com/bliki/CQRS.html"}],
    )

    assert 'aula: "Fundamentos de CQRS"' in md
    assert 'curso: "Arquitetura Avançada"' in md
    assert 'plataforma: "Circle.so"' in md
    assert "[Martin Fowler CQRS](https://martinfowler.com/bliki/CQRS.html)" in md
    assert "## 📝 Transcrição & Notas Brutas" in md
    assert "Transcrição de teste" in md


def test_save_lesson_note_and_moc(tmp_path: Path):
    vault = tmp_path / "MyVault"
    note_path = save_lesson_note(
        vault_path=vault,
        courses_folder="10-Cursos",
        course_name="DDD Pratico",
        title="01 - Bounded Contexts",
        content="# 01 - Bounded Contexts\n\nConteudo da aula.",
    )

    assert note_path.exists()
    assert note_path.name == "01 - Bounded Contexts.md"

    # Verify MOC was automatically created
    moc_path = vault / "10-Cursos" / "DDD Pratico" / "_Indice - DDD Pratico.md"
    assert moc_path.exists()
    moc_content = moc_path.read_text(encoding="utf-8")
    assert "- [[01 - Bounded Contexts]]" in moc_content


def test_save_lesson_note_with_space_and_section(tmp_path: Path):
    vault = tmp_path / "MyVault"
    note_path = save_lesson_note(
        vault_path=vault,
        courses_folder="10-Cursos",
        course_name="Tech Leads club",
        title="02. Tasks, Testes, Quality Gates e Paralelização",
        content="# Conteudo",
        space_name="IA First Dev",
        section_name="03 - Desenvolvimento em Escala com IA",
    )

    expected_path = (
        vault
        / "10-Cursos"
        / "Tech Leads club"
        / "IA First Dev"
        / "03 - Desenvolvimento em Escala com IA"
        / "02. Tasks, Testes, Quality Gates e Paralelização.md"
    )
    assert note_path == expected_path
    assert note_path.exists()

    # Verify MOC at root of course
    moc_path = vault / "10-Cursos" / "Tech Leads club" / "_Indice - Tech Leads club.md"
    assert moc_path.exists()
    moc_content = moc_path.read_text(encoding="utf-8")
    assert "### IA First Dev" in moc_content
    assert "#### 03 - Desenvolvimento em Escala com IA" in moc_content
    assert "- [[02. Tasks, Testes, Quality Gates e Paralelização]]" in moc_content


def test_resolve_existing_dir_case_insensitive(tmp_path: Path):
    vault = tmp_path / "MyVault"
    existing = vault / "10-Cursos" / "Tech Leads club" / "IA First Dev"
    existing.mkdir(parents=True, exist_ok=True)

    note_path = save_lesson_note(
        vault_path=vault,
        courses_folder="10-Cursos",
        course_name="Tech Leads Club",
        title="03. Quando Usar Sub Agents",
        content="# Sub Agents",
        space_name="ia first dev",
        section_name="03 - Desenvolvimento em Escala com IA",
    )

    assert "Tech Leads club/IA First Dev" in str(note_path)
    assert note_path.exists()
