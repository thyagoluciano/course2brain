from pathlib import Path

from c2b.config import Config
from c2b.plugins import run_pre_process_hooks


def test_plugin_pre_process_hook(tmp_path: Path, monkeypatch):
    # Create temporary plugin folder
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    plugin_code = """
def on_pre_process(payload, config):
    payload["local_media_path"] = "/tmp/downloaded_video.mp4"
    payload["modified_by_plugin"] = True
    return payload
"""
    (plugins_dir / "my_custom_plugin.py").write_text(plugin_code, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    cfg = Config()

    initial_payload = {"title": "Aula 01", "media_url": "https://example.com/video.mp4"}
    updated = run_pre_process_hooks(initial_payload, cfg)

    assert updated.get("modified_by_plugin") is True
    assert updated.get("local_media_path") == "/tmp/downloaded_video.mp4"
