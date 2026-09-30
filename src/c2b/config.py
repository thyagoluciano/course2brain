from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VaultConfig:
    path: Path = field(default_factory=lambda: Path.home() / "Obsidian" / "SecondBrain")
    courses_folder: str = "10-Cursos"
    concepts_folder: str = "20-Conceitos"


@dataclass
class GeminiConfig:
    api_key: str = ""
    model: str = "gemini-3.8-flash"


DEFAULT_EXCLUDE_FOLDERS: list[str] = [
    ".obsidian",
    "_sistema",
    ".trash",
    "90-Templates",
    ".git",
]


@dataclass
class InterlinkConfig:
    enabled: bool = True
    similarity_threshold: float = 0.78
    max_links: int = 5
    embedding_model: str = "all-MiniLM-L6-v2"
    db_path: Path | None = None
    include_folders: list[str] = field(default_factory=lambda: ["10-Cursos"])
    exclude_folders: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_FOLDERS))


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class Config:
    vault: VaultConfig = field(default_factory=VaultConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    interlink: InterlinkConfig = field(default_factory=InterlinkConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def find_config_file(explicit_path: Path | str | None = None) -> Path | None:
    """Find configuration file using hierarchical resolution."""
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists():
            return p

    # Local working directory
    local_cfg = Path("c2b.toml").resolve()
    if local_cfg.exists():
        return local_cfg

    # User config directory
    user_cfg = Path.home() / ".config" / "c2b" / "config.toml"
    if user_cfg.exists():
        return user_cfg

    return None


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from TOML file with environment variable overrides."""
    config_file = find_config_file(config_path)
    data: dict = {}

    if config_file and config_file.exists():
        with open(config_file, "rb") as f:
            data = tomllib.load(f)

    # Vault
    v_data = data.get("vault", {})
    raw_vault_path = os.getenv("C2B_VAULT_PATH") or v_data.get("path")
    vault_path = (
        Path(raw_vault_path).expanduser().resolve()
        if raw_vault_path
        else Path.home() / "Obsidian" / "SecondBrain"
    )
    vault = VaultConfig(
        path=vault_path,
        courses_folder=v_data.get("courses_folder", "10-Cursos"),
        concepts_folder=v_data.get("concepts_folder", "20-Conceitos"),
    )

    # Gemini
    g_data = data.get("gemini", {})
    gemini_key = os.getenv("GEMINI_API_KEY") or g_data.get("api_key", "")
    gemini_model = os.getenv("C2B_MODEL") or g_data.get("model", "gemini-3.8-flash")
    gemini = GeminiConfig(
        api_key=gemini_key,
        model=gemini_model,
    )

    # Interlink
    i_data = data.get("interlink", {})
    raw_db_path = i_data.get("db_path")
    db_path = (
        Path(raw_db_path).expanduser().resolve()
        if raw_db_path
        else vault.path / "_sistema" / "vectors.db"
    )

    raw_include_folders = i_data.get("include_folders")
    if raw_include_folders is None:
        include_folders = [vault.courses_folder]
    elif isinstance(raw_include_folders, str):
        include_folders = [raw_include_folders]
    else:
        include_folders = list(raw_include_folders)

    raw_exclude_folders = i_data.get("exclude_folders")
    if raw_exclude_folders is None:
        exclude_folders = list(DEFAULT_EXCLUDE_FOLDERS)
    elif isinstance(raw_exclude_folders, str):
        exclude_folders = [raw_exclude_folders]
    else:
        exclude_folders = list(raw_exclude_folders)

    interlink = InterlinkConfig(
        enabled=i_data.get("enabled", True),
        similarity_threshold=float(i_data.get("similarity_threshold", 0.78)),
        max_links=int(i_data.get("max_links", 5)),
        embedding_model=i_data.get("embedding_model", "all-MiniLM-L6-v2"),
        db_path=db_path,
        include_folders=include_folders,
        exclude_folders=exclude_folders,
    )

    # Server
    s_data = data.get("server", {})
    server_host = os.getenv("C2B_HOST") or s_data.get("host", "127.0.0.1")
    server_port = int(os.getenv("C2B_PORT") or s_data.get("port", 8765))
    server = ServerConfig(
        host=server_host,
        port=server_port,
    )

    return Config(
        vault=vault,
        gemini=gemini,
        interlink=interlink,
        server=server,
    )
