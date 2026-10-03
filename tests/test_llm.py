import json
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from c2b.llm import (
    DEFAULT_PROVIDER_URLS,
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    RateLimiter,
    UnifiedLLMClient,
    extract_json_payload,
)


def test_rate_limiter_interval():
    limiter = RateLimiter(rpm=600)  # 0.1s interval
    assert limiter.interval == pytest.approx(0.1, rel=1e-2)

    t0 = time.monotonic()
    limiter.acquire()
    limiter.acquire()
    t1 = time.monotonic()
    assert (t1 - t0) >= 0.08


def test_rate_limiter_disabled():
    limiter = RateLimiter(rpm=0)
    assert limiter.interval == 0.0
    # Should not raise or block
    limiter.acquire()
    limiter.acquire()


def test_extract_json_payload_direct():
    data = [{"titulo": "Nota A", "relevante": True}]
    raw = json.dumps(data)
    assert extract_json_payload(raw) == data


def test_extract_json_payload_markdown_fence():
    data = {"name": "test", "items": [1, 2, 3]}
    raw = f"```json\n{json.dumps(data, indent=2)}\n```"
    assert extract_json_payload(raw) == data


def test_extract_json_payload_with_surrounding_text():
    data = [{"title": "Concept"}]
    raw = f"Aqui está o resultado:\n```\n{json.dumps(data)}\n```\nEspero ter ajudado!"
    assert extract_json_payload(raw) == data


def test_extract_json_payload_brackets_without_fence():
    data = [{"title": "Direct Bracket"}]
    raw = f"Análise concluída: {json.dumps(data)} fim da análise."
    assert extract_json_payload(raw) == data


def test_extract_json_payload_invalid():
    with pytest.raises(ValueError, match="Não foi possível extrair JSON"):
        extract_json_payload("Isto não é um json de forma alguma.")


def test_unified_client_initialization():
    client = UnifiedLLMClient(
        provider="openrouter",
        api_key="sk-or-test",
        model="google/gemma-4-31b-it:free",
        rpm_limit=15,
    )
    assert client.provider == "openrouter"
    assert client.endpoint == f"{DEFAULT_PROVIDER_URLS['openrouter']}/chat/completions"
    assert client.model == "google/gemma-4-31b-it:free"

    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer sk-or-test"
    assert headers["HTTP-Referer"] == "https://github.com/thyagoluciano/course2brain"


def test_unified_client_generate_text_success():
    client = UnifiedLLMClient(provider="gemini", api_key="test-key", rpm_limit=0)

    mock_resp_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "# Resumo da Aula\n\nConteúdo gerado com sucesso.",
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.generate_text("Explique Zettelkasten", system_prompt="Você é um tutor.")
        assert "Resumo da Aula" in result


def test_unified_client_generate_json_success():
    client = UnifiedLLMClient(provider="openrouter", api_key="test-key", rpm_limit=0)

    expected = [{"titulo": "Obsidian", "relevante": True}]
    mock_resp_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": f"```json\n{json.dumps(expected)}\n```",
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.generate_json("Analise conexões", system_prompt="Retorne JSON.")
        assert result == expected


def test_unified_client_rate_limit_error():
    client = UnifiedLLMClient(provider="openrouter", api_key="test-key", rpm_limit=0)

    err_body = json.dumps({"error": {"message": "Rate limit exceeded: 20 RPM"}})
    mock_fp = MagicMock()
    mock_fp.read.return_value = err_body.encode("utf-8")

    http_err = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=mock_fp,
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(LLMRateLimitError) as exc_info:
            client.generate_text("Prompt teste")
        assert "HTTP 429" in str(exc_info.value)
        assert "openrouter.ai/activity" in str(exc_info.value)


def test_unified_client_auth_error():
    client = UnifiedLLMClient(provider="gemini", api_key="invalid-key", rpm_limit=0)

    err_body = json.dumps({"error": {"message": "API key not valid"}})
    mock_fp = MagicMock()
    mock_fp.read.return_value = err_body.encode("utf-8")

    http_err = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=mock_fp,
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(LLMAuthError) as exc_info:
            client.generate_text("Prompt teste")
        assert "HTTP 401" in str(exc_info.value)
        assert "GEMINI_API_KEY" in str(exc_info.value)


def test_unified_client_server_error():
    client = UnifiedLLMClient(provider="openrouter", api_key="test-key", rpm_limit=0)

    err_body = json.dumps({"error": {"message": "Service Unavailable"}})
    mock_fp = MagicMock()
    mock_fp.read.return_value = err_body.encode("utf-8")

    http_err = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=mock_fp,
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(LLMError) as exc_info:
            client.generate_text("Prompt teste")
        assert "HTTP 503" in str(exc_info.value)
        assert "openrouter/free" in str(exc_info.value)

