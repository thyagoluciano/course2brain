from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from c2b.llm import (
    DEFAULT_PROVIDER_ENV_VARS,
    DEFAULT_PROVIDER_MODELS,
    DEFAULT_PROVIDER_URLS,
    UnifiedLLMClient,
)


@dataclass
class VaultConfig:
    path: Path = field(default_factory=lambda: Path.home() / "Obsidian" / "SecondBrain")
    courses_folder: str = "10-Cursos"
    concepts_folder: str = "20-Conceitos"


@dataclass
class GeminiConfig:
    api_key: str = ""
    model: str = "gemini-3.8-flash"


@dataclass
class OpenRouterConfig:
    api_key: str = ""
    model: str = "google/gemma-4-31b-it:free"
    rpm_limit: int = 15


@dataclass
class OpenAIConfig:
    api_key: str = ""
    model: str = "gpt-4o-mini"



@dataclass
class TaskAIConfig:
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    rpm_limit: int | None = None


@dataclass
class AIConfig:
    default_provider: str = "gemini"
    synthesis: TaskAIConfig = field(default_factory=TaskAIConfig)
    interlink: TaskAIConfig = field(default_factory=TaskAIConfig)


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
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    interlink: InterlinkConfig = field(default_factory=InterlinkConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    def get_llm_client_for_task(self, task_name: str) -> UnifiedLLMClient:
        """Resolve appropriate LLM client for a specific task ('synthesis' or 'interlink')."""
        task_cfg = self.ai.synthesis if task_name == "synthesis" else self.ai.interlink

        # 1. Determine provider
        provider = (
            task_cfg.provider.lower().strip()
            if task_cfg.provider
            else self.ai.default_provider.lower().strip()
        )

        # 2. Determine API key
        api_key = task_cfg.api_key.strip()
        if not api_key:
            if provider == "openrouter":
                api_key = self.openrouter.api_key
            elif provider == "gemini":
                api_key = self.gemini.api_key
            elif provider == "openai":
                api_key = self.openai.api_key
            else:
                env_var = DEFAULT_PROVIDER_ENV_VARS.get(provider, "")
                if env_var:
                    api_key = os.getenv(env_var, "")

        # 3. Determine Model
        model = task_cfg.model.strip()
        if not model:
            if provider == "openrouter":
                model = self.openrouter.model
            elif provider == "gemini":
                model = self.gemini.model
            elif provider == "openai":
                model = self.openai.model
            else:
                model = DEFAULT_PROVIDER_MODELS.get(provider, "")


        # 4. Determine RPM limit
        rpm_limit = task_cfg.rpm_limit
        if rpm_limit is None:
            if provider == "openrouter":
                rpm_limit = self.openrouter.rpm_limit
            elif provider == "gemini":
                rpm_limit = 0
            else:
                rpm_limit = 0

        # 5. Base URL
        base_url = task_cfg.base_url.strip() or DEFAULT_PROVIDER_URLS.get(provider, "")

        return UnifiedLLMClient(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            rpm_limit=rpm_limit,
        )


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

    # OpenRouter
    o_data = data.get("openrouter", {})
    openrouter_key = os.getenv("OPENROUTER_API_KEY") or o_data.get("api_key", "")
    openrouter_model = os.getenv("OPENROUTER_MODEL") or o_data.get(
        "model", "google/gemma-4-31b-it:free"
    )
    openrouter_rpm = int(o_data.get("rpm_limit", 15))
    openrouter = OpenRouterConfig(
        api_key=openrouter_key,
        model=openrouter_model,
        rpm_limit=openrouter_rpm,
    )

    # OpenAI
    oa_data = data.get("openai", {})
    openai_key = os.getenv("OPENAI_API_KEY") or oa_data.get("api_key", "")
    openai_model = os.getenv("OPENAI_MODEL") or oa_data.get("model", "gpt-4o-mini")
    openai = OpenAIConfig(
        api_key=openai_key,
        model=openai_model,
    )

    # Unified AI / Tasks
    ai_data = data.get("ai", {})
    # Default provider: explicit config -> env -> openai -> openrouter -> gemini
    default_provider = os.getenv("C2B_AI_PROVIDER") or ai_data.get("default_provider", "")
    if not default_provider:
        if openai_key and not gemini_key and not openrouter_key:
            default_provider = "openai"
        elif openrouter_key and not gemini_key:
            default_provider = "openrouter"
        else:
            default_provider = "gemini"


    synth_data = ai_data.get("synthesis", {})
    synthesis = TaskAIConfig(
        provider=synth_data.get("provider", ""),
        model=synth_data.get("model", ""),
        api_key=synth_data.get("api_key", ""),
        base_url=synth_data.get("base_url", ""),
        rpm_limit=int(synth_data["rpm_limit"]) if "rpm_limit" in synth_data else None,
    )

    inter_data = ai_data.get("interlink", {})
    interlink_task = TaskAIConfig(
        provider=inter_data.get("provider", ""),
        model=inter_data.get("model", ""),
        api_key=inter_data.get("api_key", ""),
        base_url=inter_data.get("base_url", ""),
        rpm_limit=int(inter_data["rpm_limit"]) if "rpm_limit" in inter_data else None,
    )

    ai = AIConfig(
        default_provider=default_provider,
        synthesis=synthesis,
        interlink=interlink_task,
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
        openrouter=openrouter,
        openai=openai,
        ai=ai,
        interlink=interlink,
        server=server,
    )

