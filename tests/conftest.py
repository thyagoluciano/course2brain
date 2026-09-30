import pytest


@pytest.fixture(autouse=True)
def disable_hf_network(monkeypatch):
    monkeypatch.setenv("C2B_NO_HF", "1")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
