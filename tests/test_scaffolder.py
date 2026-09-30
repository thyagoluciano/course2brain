import json
from pathlib import Path

from c2b.scaffolder import init_vault


def test_init_vault_creates_directories_and_files(tmp_path: Path):
    target = tmp_path / "TestVault"
    created = init_vault(target)
    assert len(created) > 0

    assert (target / "00-Inbox").is_dir()
    assert (target / "10-Cursos").is_dir()
    assert (target / "20-Conceitos").is_dir()
    assert (target / "_sistema" / "templates").is_dir()
    assert (target / "_sistema" / "relatorios").is_dir()
    assert (target / ".obsidian").is_dir()

    app_json = target / ".obsidian" / "app.json"
    assert app_json.exists()
    app_data = json.loads(app_json.read_text(encoding="utf-8"))
    assert app_data.get("newFileFolderPath") == "00-Inbox"

    graph_json = target / ".obsidian" / "graph.json"
    assert graph_json.exists()
    graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
    assert "colorGroups" in graph_data

    template_file = target / "_sistema" / "templates" / "Template - Aula de Curso.md"
    assert template_file.exists()
    assert "## 📌 Resumo Executivo" in template_file.read_text(encoding="utf-8")

    dashboard = target / "Dashboard.md"
    assert dashboard.exists()
    assert "Second Brain Knowledge Hub" in dashboard.read_text(encoding="utf-8")


def test_init_vault_idempotency(tmp_path: Path):
    target = tmp_path / "IdempotentVault"
    created_first = init_vault(target)
    assert len(created_first) > 0

    # Running a second time should not recreate or overwrite existing files
    created_second = init_vault(target)
    assert len(created_second) == 0
