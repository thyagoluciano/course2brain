from pathlib import Path

from c2b.config import Config, load_config


def test_load_default_config(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("C2B_VAULT_PATH", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.vault.courses_folder == "10-Cursos"
    assert cfg.vault.concepts_folder == "20-Conceitos"
    assert cfg.gemini.model == "gemini-3.8-flash"
    assert cfg.interlink.enabled is True
    assert cfg.interlink.similarity_threshold == 0.78
    assert cfg.server.port == 8765


def test_load_custom_toml(tmp_path: Path):
    target_vault = (tmp_path / "my-test-vault").resolve()
    toml_content = f"""
    [vault]
    path = "{target_vault}"
    courses_folder = "MeusCursos"

    [gemini]
    api_key = "test-api-key"
    model = "custom-gemini"

    [interlink]
    similarity_threshold = 0.82
    max_links = 3

    [server]
    port = 9000
    """
    cfg_file = tmp_path / "c2b.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.vault.path == target_vault
    assert cfg.vault.courses_folder == "MeusCursos"
    assert cfg.gemini.api_key == "test-api-key"
    assert cfg.gemini.model == "custom-gemini"
    assert cfg.interlink.similarity_threshold == 0.82
    assert cfg.interlink.max_links == 3
    assert cfg.server.port == 9000


def test_env_overrides(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("C2B_VAULT_PATH", str(tmp_path / "env-vault"))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.setenv("C2B_PORT", "9999")

    cfg = load_config()
    assert str(cfg.vault.path) == str(tmp_path / "env-vault")
    assert cfg.gemini.api_key == "env-key"
    assert cfg.server.port == 9999


def test_interlink_folders_config(tmp_path: Path):
    toml_content = """
    [vault]
    courses_folder = "CursosCustom"

    [interlink]
    include_folders = ["50-Conteudo", "20-Conceitos"]
    exclude_folders = [".obsidian", "_sistema", "arquivo"]
    """
    cfg_file = tmp_path / "c2b.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.interlink.include_folders == ["50-Conteudo", "20-Conceitos"]
    assert cfg.interlink.exclude_folders == [".obsidian", "_sistema", "arquivo"]


def test_interlink_folders_defaults_fallback(tmp_path: Path):
    toml_content = """
    [vault]
    courses_folder = "CustomCourses"
    """
    cfg_file = tmp_path / "c2b.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.interlink.include_folders == ["CustomCourses"]
    assert ".obsidian" in cfg.interlink.exclude_folders
    assert "_sistema" in cfg.interlink.exclude_folders


def test_openrouter_and_task_ai_config(tmp_path: Path):
    toml_content = """
    [openrouter]
    api_key = "sk-or-test-123"
    model = "google/gemma-4-31b-it:free"
    rpm_limit = 20

    [ai]
    default_provider = "openrouter"

    [ai.synthesis]
    provider = "openrouter"
    model = "google/gemma-4-31b-it:free"

    [ai.interlink]
    provider = "openrouter"
    model = "qwen/qwen3.8-27b:free"
    """
    cfg_file = tmp_path / "c2b.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.openrouter.api_key == "sk-or-test-123"
    assert cfg.openrouter.model == "google/gemma-4-31b-it:free"
    assert cfg.openrouter.rpm_limit == 20
    assert cfg.ai.default_provider == "openrouter"

    synth_client = cfg.get_llm_client_for_task("synthesis")
    assert synth_client.provider == "openrouter"
    assert synth_client.model == "google/gemma-4-31b-it:free"
    assert synth_client.api_key == "sk-or-test-123"
    assert synth_client.rate_limiter.rpm == 20

    interlink_client = cfg.get_llm_client_for_task("interlink")
    assert interlink_client.provider == "openrouter"
    assert interlink_client.model == "qwen/qwen3.8-27b:free"
    assert interlink_client.api_key == "sk-or-test-123"


def test_task_ai_fallback_to_gemini(tmp_path: Path):
    toml_content = """
    [gemini]
    api_key = "gemini-fallback-key"
    model = "gemini-2.5-flash"
    """
    cfg_file = tmp_path / "c2b.toml"
    cfg_file.write_text(toml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    synth_client = cfg.get_llm_client_for_task("synthesis")
    assert synth_client.provider == "gemini"
    assert synth_client.model == "gemini-2.5-flash"
    assert synth_client.api_key == "gemini-fallback-key"

