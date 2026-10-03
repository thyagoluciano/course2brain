from pathlib import Path

from fastapi.testclient import TestClient

from c2b.config import Config, GeminiConfig, InterlinkConfig, VaultConfig
from c2b.server import create_app


def test_get_vault_folders(tmp_path: Path):
    vault = tmp_path / "SecondBrain"
    (vault / "10-Cursos" / "Tech Leads club").mkdir(parents=True, exist_ok=True)
    (vault / "20-Recursos" / "Leituras").mkdir(parents=True, exist_ok=True)
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)

    cfg = Config(
        vault=VaultConfig(path=vault, courses_folder="10-Cursos"),
        gemini=GeminiConfig(api_key="test-key", model="gemini-2.5-flash"),
        interlink=InterlinkConfig(enabled=False),
    )

    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/vault/folders")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "ok"
    assert "10-Cursos" in data["folders"]
    assert "10-Cursos/Tech Leads club" in data["folders"]
    assert "20-Recursos" in data["folders"]
    assert ".obsidian" not in data["folders"]
    assert data["default_folder"] == "10-Cursos"


def test_process_lesson_endpoint(tmp_path: Path, monkeypatch):
    vault = tmp_path / "SecondBrain"
    vault.mkdir(parents=True, exist_ok=True)

    cfg = Config(
        vault=VaultConfig(path=vault, courses_folder="10-Cursos"),
        gemini=GeminiConfig(api_key="test-key", model="gemini-2.5-flash"),
        interlink=InterlinkConfig(enabled=False),
    )

    # Mock summarize_lesson
    monkeypatch.setattr(
        "c2b.server.summarize_lesson",
        lambda *args, **kwargs: "## Resumo Mock\nConteúdo da aula sintetizado.",
    )

    app = create_app(cfg)
    client = TestClient(app)

    payload = {
        "course_name": "Arquitetura",
        "title": "Aula 01 - Clean Arch",
        "captions_text": "Transcrição da aula",
        "notes_text": "Notas de apoio",
    }

    resp = client.post("/api/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["title"] == "Aula 01 - Clean Arch"
    assert data["course"] == "Arquitetura"
    assert (vault / data["note_file"]).exists()

