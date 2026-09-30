from pathlib import Path

from c2b.config import Config, InterlinkConfig, VaultConfig
from c2b.interlink import (
    compute_embedding,
    cosine_similarity,
    deserialize_vector,
    find_candidates,
    index_note,
    interlink_note,
    serialize_vector,
)


def test_vector_serialization_and_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert cosine_similarity(v1, v2) == 1.0
    assert cosine_similarity(v1, v3) == 0.0

    blob = serialize_vector(v1)
    deserialized = deserialize_vector(blob)
    assert len(deserialized) == 3
    assert abs(deserialized[0] - 1.0) < 1e-6


def test_index_and_find_candidates(tmp_path: Path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    courses_dir = vault / "10-Cursos" / "Microservices"
    courses_dir.mkdir(parents=True)

    note1 = courses_dir / "01 - Event-Driven.md"
    note1.write_text(
        """# Event-Driven Architecture
## 📌 Resumo Executivo
Arquitetura orientada a eventos usando Kafka e RabbitMQ para mensageria assíncrona.
""",
        encoding="utf-8",
    )

    note2 = courses_dir / "02 - Kafka Fundamentals.md"
    note2.write_text(
        """# Kafka Fundamentals
## 📌 Resumo Executivo
Uso prático do Apache Kafka para mensageria e streaming de eventos em larga escala.
""",
        encoding="utf-8",
    )

    db_path = vault / "vectors.db"

    # Index both notes
    index_note(vault, note1, db_path)
    index_note(vault, note2, db_path)

    # Search candidates for note 1
    vec1 = compute_embedding("Event-Driven Architecture\nKafka e mensageria")
    candidates = find_candidates(
        vault,
        db_path,
        "10-Cursos/Microservices/01 - Event-Driven.md",
        vec1,
        similarity_threshold=0.0,
    )

    assert len(candidates) == 1
    assert candidates[0]["title"] == "Kafka Fundamentals"


def test_interlink_note_dry_run(tmp_path: Path):
    vault = tmp_path / "Vault"
    vault.mkdir()
    courses_dir = vault / "10-Cursos" / "DDD"
    courses_dir.mkdir(parents=True)

    note1 = courses_dir / "01 - Aggregate.md"
    note1.write_text(
        "# Aggregate\n## 📌 Resumo Executivo\nPadrão de consistência transacional do DDD.",
        encoding="utf-8",
    )

    cfg = Config(
        vault=VaultConfig(path=vault, courses_folder="10-Cursos"),
        interlink=InterlinkConfig(
            enabled=True, similarity_threshold=0.0, db_path=vault / "vectors.db"
        ),
    )

    res = interlink_note(cfg, note1, dry_run=True)
    assert res["status"] == "success"
    assert res["dry_run"] is True


def test_discover_notes_to_index(tmp_path: Path):
    vault = tmp_path / "SecondBrain"
    vault.mkdir()

    # Folders to test
    (vault / "10-Cursos" / "Python").mkdir(parents=True)
    (vault / "50-Conteudo" / "Substack").mkdir(parents=True)
    (vault / "20-Conceitos").mkdir(parents=True)
    (vault / "00-Inbox").mkdir(parents=True)
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "_sistema").mkdir(parents=True)
    (vault / ".trash").mkdir(parents=True)

    # Valid notes
    c1 = vault / "10-Cursos" / "Python" / "Aula 01.md"
    c1.write_text("# Python 101", encoding="utf-8")
    s1 = vault / "50-Conteudo" / "Substack" / "Artigo.md"
    s1.write_text("# Meu Artigo", encoding="utf-8")
    z1 = vault / "20-Conceitos" / "Zettelkasten.md"
    z1.write_text("# Zettelkasten", encoding="utf-8")
    i1 = vault / "00-Inbox" / "Nota Rapida.md"
    i1.write_text("# Inbox", encoding="utf-8")

    # Excluded files
    (vault / ".obsidian" / "workspace.md").write_text("# Workspace", encoding="utf-8")
    (vault / "_sistema" / "template.md").write_text("# Template", encoding="utf-8")
    (vault / ".trash" / "deleted.md").write_text("# Deleted", encoding="utf-8")
    (vault / "10-Cursos" / "Python" / "_hidden.md").write_text("# Hidden", encoding="utf-8")
    (vault / "10-Cursos" / "Python" / ".dotfile.md").write_text("# Dot", encoding="utf-8")
    (vault / "10-Cursos" / "Python" / "slides.pdf").write_text("Binary", encoding="utf-8")

    from c2b.interlink import discover_notes_to_index, is_excluded_path

    # Test exclusions helper
    assert is_excluded_path(Path(".obsidian/config.json")) is True
    assert is_excluded_path(Path("_sistema/vectors.db")) is True
    assert is_excluded_path(Path("10-Cursos/_draft.md")) is True
    assert is_excluded_path(Path("10-Cursos/.hidden.md")) is True
    assert is_excluded_path(Path("10-Cursos/Aula.md")) is False

    # 1. Configured specific folders
    notes = discover_notes_to_index(vault, include_folders=["10-Cursos", "50-Conteudo"])
    paths = [n.relative_to(vault).as_posix() for n in notes]
    assert "10-Cursos/Python/Aula 01.md" in paths
    assert "50-Conteudo/Substack/Artigo.md" in paths
    assert "20-Conceitos/Zettelkasten.md" not in paths
    assert "00-Inbox/Nota Rapida.md" not in paths
    assert len(paths) == 2

    # 2. Whole vault scope ("*")
    all_notes = discover_notes_to_index(vault, include_folders=["*"])
    all_paths = [n.relative_to(vault).as_posix() for n in all_notes]
    assert "10-Cursos/Python/Aula 01.md" in all_paths
    assert "50-Conteudo/Substack/Artigo.md" in all_paths
    assert "20-Conceitos/Zettelkasten.md" in all_paths
    assert "00-Inbox/Nota Rapida.md" in all_paths
    assert not any(p.startswith(".") or p.startswith("_") for p in all_paths)
    assert not any(".obsidian" in p or "_sistema" in p or ".trash" in p for p in all_paths)
    assert len(all_paths) == 4


def test_extract_note_text_universal():
    from c2b.interlink import extract_note_text_for_embedding

    # Format A: Course note with H1 and ## 📌 Resumo Executivo
    content_a = """# Minha Aula
## 📌 Resumo Executivo
Este é o resumo executivo detalhado da aula.
## Conceitos
Pontos chaves.
"""
    title, summary = extract_note_text_for_embedding(content_a)
    assert title == "Minha Aula"
    assert "resumo executivo detalhado" in summary

    # Format B: Substack article with Frontmatter YAML and ## Introdução
    content_b = """---
title: "course2brain no Substack"
description: "Artigo sobre como transformar cursos em notas."
tags: [ia, obsidian]
---
# course2brain: Como transformar horas de vídeo

## Introdução
Neste artigo explicamos a motivação de criar a ferramenta.
"""
    title, summary = extract_note_text_for_embedding(content_b)
    assert title == "course2brain: Como transformar horas de vídeo"
    assert "Neste artigo explicamos a motivação" in summary

    # Format C: Freeform note with only YAML title and description
    content_c = """---
title: "Nota Conceitual"
summary: "Definição do padrão CQRS e segregação de comandos e consultas."
---
Texto corrido sem seções nomeadas.
"""
    title, summary = extract_note_text_for_embedding(content_c)
    assert title == "Nota Conceitual"
    assert "Definição do padrão CQRS" in summary
