from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from c2b.config import Config, GeminiConfig, InterlinkConfig, VaultConfig
from c2b.server import create_app


def test_process_skilljar_lesson_with_youtube_video(tmp_path: Path, monkeypatch):
    """Test full processing of a Skilljar lesson containing an embedded YouTube video."""
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
        lambda *args, **kwargs: "## Resumo Executivo\nSíntese dos fundamentos de AI Fluency.",
    )

    # Mock fetch_youtube_transcript
    mock_fetch = MagicMock(return_value="Transcrição completa extraída do YouTube sobre AI Fluency.")
    monkeypatch.setattr("c2b.server.fetch_youtube_transcript", mock_fetch)

    app = create_app(cfg)
    client = TestClient(app)

    payload = {
        "platform": "skilljar",
        "course_name": "AI Fluency: Framework & Foundations",
        "space_name": None,
        "section_name": "02 - The AI Fluency Framework",
        "title": "01. Why do we need AI Fluency?",
        "captions_text": "",  # Empty from browser -> triggers server fallback
        "notes_text": "By the end of this lesson, you'll be able to understand what AI Fluency means.",
        "links": [
            {"texto": "Share your feedback here.", "url": "https://forms.gle/zURqLbVgdDqGhHZk9"}
        ],
        "page_url": "https://anthropic-partners.skilljar.com/ai-fluency-framework-foundations/291870",
        "media_url": "https://www.youtube.com/watch?v=4szRHy_CT7s",
    }

    resp = client.post("/api/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["title"] == "01. Why do we need AI Fluency?"
    assert data["course"] == "AI Fluency: Framework & Foundations"

    # Verify fetch_youtube_transcript was called with the media URL
    mock_fetch.assert_called_once_with("https://www.youtube.com/watch?v=4szRHy_CT7s")

    # Verify file saved in proper directory structure
    note_file = vault / data["note_file"]
    assert note_file.exists()
    assert "02 - The AI Fluency Framework" in str(note_file.parent)

    # Check note content
    content = note_file.read_text(encoding="utf-8")
    assert 'curso: "AI Fluency: Framework & Foundations"' in content
    assert 'topico: "02 - The AI Fluency Framework"' in content
    assert 'aula: "01. Why do we need AI Fluency?"' in content
    assert 'video_url: "https://www.youtube.com/watch?v=4szRHy_CT7s"' in content
    assert "https://www.youtube.com/embed/4szRHy_CT7s" in content
    assert "[Assistir no YouTube ↗](https://www.youtube.com/watch?v=4szRHy_CT7s)" in content
    assert "Share your feedback here." in content
    assert "Transcrição completa extraída do YouTube sobre AI Fluency." in content

    # Verify MOC file exists
    moc_files = list(note_file.parent.parent.glob("_Indice - *.md"))
    assert len(moc_files) == 1
    moc_content = moc_files[0].read_text(encoding="utf-8")
    assert "01. Why do we need AI Fluency" in moc_content


def test_process_skilljar_quiz_lesson_without_video(tmp_path: Path, monkeypatch):
    """Test processing of a Skilljar quiz/certificate lesson without video."""
    vault = tmp_path / "SecondBrain"
    vault.mkdir(parents=True, exist_ok=True)

    cfg = Config(
        vault=VaultConfig(path=vault, courses_folder="10-Cursos"),
        gemini=GeminiConfig(api_key="test-key", model="gemini-2.5-flash"),
        interlink=InterlinkConfig(enabled=False),
    )

    monkeypatch.setattr(
        "c2b.server.summarize_lesson",
        lambda *args, **kwargs: "## Questionário Final\nAvaliação de conclusão do curso.",
    )

    app = create_app(cfg)
    client = TestClient(app)

    payload = {
        "platform": "skilljar",
        "course_name": "AI Fluency: Framework & Foundations",
        "space_name": None,
        "section_name": "08 - Conclusion & certificate",
        "title": "02. Certificate of completion",
        "captions_text": "",
        "notes_text": "Quiz final para obtenção do certificado de conclusão.",
        "links": [],
        "page_url": "https://anthropic-partners.skilljar.com/ai-fluency-framework-foundations/309598",
        "media_url": None,
    }

    resp = client.post("/api/process", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    note_file = vault / data["note_file"]
    assert note_file.exists()
    content = note_file.read_text(encoding="utf-8")
    assert 'topico: "08 - Conclusion & certificate"' in content
    assert 'aula: "02. Certificate of completion"' in content
    assert "## 📺 Vídeo da Aula" not in content
