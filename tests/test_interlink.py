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
    candidates = find_candidates(vault, db_path, "10-Cursos/Microservices/01 - Event-Driven.md", vec1, similarity_threshold=0.0)

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
        interlink=InterlinkConfig(enabled=True, similarity_threshold=0.0, db_path=vault / "vectors.db"),
    )

    res = interlink_note(cfg, note1, dry_run=True)
    assert res["status"] == "success"
    assert res["dry_run"] is True
