"""Plugin system for decoupled extensibility and private hooks."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, List

from c2b.config import Config

logger = logging.getLogger(__name__)


def find_plugin_directories() -> List[Path]:
    """Find valid plugin directory locations."""
    dirs = []
    # 1. Local project plugins/ directory
    local_plugins = Path("plugins").resolve()
    if local_plugins.is_dir():
        dirs.append(local_plugins)

    # 2. User ~/.config/c2b/plugins directory
    user_plugins = Path.home() / ".config" / "c2b" / "plugins"
    if user_plugins.is_dir():
        dirs.append(user_plugins)

    return dirs


def load_plugins() -> List[Any]:
    """Dynamically load Python plugin modules found in plugin directories."""
    modules = []
    plugin_dirs = find_plugin_directories()

    for p_dir in plugin_dirs:
        for py_file in p_dir.glob("*.py"):
            if py_file.name.startswith(("_", ".")):
                continue

            module_name = f"c2b_plugin_{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)
                    modules.append(mod)
                    logger.info("Loaded plugin: %s", py_file.name)
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", py_file, e)

    return modules


def run_pre_process_hooks(payload: dict[str, Any], cfg: Config) -> dict[str, Any]:
    """
    Execute `on_pre_process(payload, config)` in all active plugins.
    Allows private plugins (e.g. video downloaders) to intercept payload and attach
    local paths before summarization.
    """
    plugins = load_plugins()
    current_payload = dict(payload)

    for plugin in plugins:
        hook = getattr(plugin, "on_pre_process", None)
        if callable(hook):
            try:
                res = hook(current_payload, cfg)
                if isinstance(res, dict):
                    current_payload = res
            except Exception as e:
                logger.error("Error executing on_pre_process in plugin %s: %s", plugin, e)

    return current_payload


def run_post_save_hooks(note_path: Path, payload: dict[str, Any], cfg: Config) -> None:
    """
    Execute `on_post_save(note_path, payload, config)` in all active plugins.
    """
    plugins = load_plugins()
    for plugin in plugins:
        hook = getattr(plugin, "on_post_save", None)
        if callable(hook):
            try:
                hook(note_path, payload, cfg)
            except Exception as e:
                logger.error("Error executing on_post_save in plugin %s: %s", plugin, e)
