"""Universal LLM client supporting OpenRouter, Gemini, OpenAI, Grok, Ollama and custom providers."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openai": "https://api.openai.com/v1",
    "grok": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "ollama": "http://localhost:11434/v1",
}

DEFAULT_PROVIDER_ENV_VARS: dict[str, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "grok": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

DEFAULT_PROVIDER_MODELS: dict[str, str] = {
    "openrouter": "google/gemma-4-31b-it:free",
    "gemini": "gemini-3.8-flash",
    "openai": "gpt-4o-mini",
    "grok": "grok-2",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.2",
}


class LLMError(RuntimeError):
    """Base error for LLM API failures."""

    def __init__(self, message: str, provider: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class LLMRateLimitError(LLMError):
    """Raised when an LLM provider returns HTTP 429 (rate limit or quota exceeded)."""

    pass


class LLMAuthError(LLMError):
    """Raised when authentication fails (HTTP 401 / missing API key)."""

    pass


class RateLimiter:
    """Thread-safe rate limiter based on sliding window interval."""

    def __init__(self, rpm: int = 15) -> None:
        self.rpm = rpm
        self.interval = 60.0 / max(1, rpm) if rpm > 0 else 0.0
        self.last_call = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Wait if necessary to ensure requests do not exceed the configured RPM."""
        if self.rpm <= 0 or self.interval <= 0:
            return

        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                logger.debug("RateLimiter: aguardando %.2fs para respeitar %d RPM", sleep_time, self.rpm)
                time.sleep(sleep_time)
            self.last_call = time.monotonic()


def extract_json_payload(raw_text: str) -> Any:
    """Extract and parse JSON from model output with defensive fallbacks."""
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("Resposta do modelo está vazia.")

    # 1. Direct parse attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fence (```json ... ``` or ``` ...)
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    matches = fence_pattern.findall(cleaned)
    for block in matches:
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue

    # 3. Locate array [ ... ] or object { ... }
    for open_ch, close_ch in [("[", "]"), ("{", "}")]:
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Não foi possível extrair JSON válido da resposta do modelo:\n{cleaned[:300]}")


class UnifiedLLMClient:
    """Universal LLM client using the OpenAI Chat Completions protocol."""

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        rpm_limit: int = 15,
        timeout: int = 180,
        max_tokens: int | None = None,
    ) -> None:
        self.provider = provider.lower().strip()
        self.api_key = api_key.strip()
        self.model = model.strip() or DEFAULT_PROVIDER_MODELS.get(self.provider, "gemini-3.8-flash")
        self.timeout = timeout
        self.max_tokens = max_tokens or (8192 if self.provider == "openrouter" else None)


        resolved_base_url = base_url.strip() or DEFAULT_PROVIDER_URLS.get(
            self.provider, DEFAULT_PROVIDER_URLS["gemini"]
        )
        self.base_url = resolved_base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rpm=rpm_limit)

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "course2brain/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # OpenRouter optional ranking metadata
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/thyagoluciano/course2brain"
            headers["X-Title"] = "course2brain"

        return headers

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute HTTP POST with rate limiting and structured error handling."""
        self.rate_limiter.acquire()

        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data_bytes,
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = resp.read().decode("utf-8")
                return json.loads(resp_data)
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8", errors="ignore")
            error_message = ""
            try:
                err_json = json.loads(err_text)
                if isinstance(err_json, dict):
                    err_obj = err_json.get("error", {})
                    if isinstance(err_obj, dict):
                        error_message = err_obj.get("message", "")
                    elif isinstance(err_obj, str):
                        error_message = err_obj
            except Exception:
                error_message = err_text.strip()

            if not error_message:
                error_message = err_text.strip() or f"HTTP {e.code}"

            if e.code == 429:
                detail = (
                    f"[{self.provider.upper()}] Limite de requisições ou cota excedida (HTTP 429): {error_message}."
                )
                if self.provider == "openrouter":
                    detail += (
                        "\n💡 Dica: Modelos gratuitos no OpenRouter possuem limite de 20 RPM e cota diária."
                        "\nConsulte o uso em: https://openrouter.ai/activity"
                    )
                raise LLMRateLimitError(detail, provider=self.provider, status_code=429) from e

            if e.code == 401:
                env_var = DEFAULT_PROVIDER_ENV_VARS.get(self.provider, "API_KEY")
                detail = (
                    f"[{self.provider.upper()}] Autenticação falhou (HTTP 401): {error_message}."
                    f"\nVerifique se a chave está configurada no c2b.toml ou na variável de ambiente {env_var}."
                )
                raise LLMAuthError(detail, provider=self.provider, status_code=401) from e

            if e.code in (502, 503, 504):
                detail = (
                    f"[{self.provider.upper()}] Servidor upstream temporariamente indisponível (HTTP {e.code}): "
                    f"{error_message}."
                )
                if self.provider == "openrouter":
                    detail += "\n💡 Dica: O nó do modelo gratuito pode estar sobrecarregado. Tente novamente ou use 'openrouter/free'."
                raise LLMError(detail, provider=self.provider, status_code=e.code) from e

            raise LLMError(
                f"[{self.provider.upper()}] Erro na API (HTTP {e.code}): {error_message}",
                provider=self.provider,
                status_code=e.code,
            ) from e
        except urllib.error.URLError as e:
            raise LLMError(
                f"[{self.provider.upper()}] Falha de conexão com endpoint '{self.endpoint}': {e.reason}",
                provider=self.provider,
            ) from e

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.4,
    ) -> str:
        """Generate text completion from prompt and optional system prompt."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        resp = self._post(payload)
        try:
            choice = resp["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content")
            if content is None or not content.strip():
                # Handle reasoning models or token exhaustion
                reasoning = (msg.get("reasoning") or msg.get("reasoning_content") or "").strip()
                finish_reason = choice.get("finish_reason")
                if finish_reason == "length":
                    if reasoning:
                        logger.warning(
                            "[%s] Modelo esgotou limite de tokens durante raciocínio (finish_reason: length). "
                            "Recuperando texto do raciocínio.",
                            self.provider.upper(),
                        )
                        return reasoning
                    raise LLMError(
                        f"[{self.provider.upper()}] Modelo esgotou limite de tokens (finish_reason: length) "
                        f"sem emitir resposta. Aumente max_tokens ou use modelo de instrução direta.",
                        provider=self.provider,
                    )
                if reasoning:
                    return reasoning
                return ""
            return content
        except (KeyError, IndexError) as err:
            raise LLMError(
                f"[{self.provider.upper()}] Resposta inesperada da API: chave 'choices[0].message' não encontrada.",
                provider=self.provider,
            ) from err

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2,
    ) -> Any:
        """Generate JSON structured response with format enforcement and resilient extraction."""
        messages: list[dict[str, str]] = []
        sys_instructions = (
            system_prompt
            + "\n\nIMPORTANTE: Sua resposta DEVE ser estritamente um JSON válido (array ou objeto), sem qualquer texto adicional ou blocos markdown."
        ).strip()
        messages.append({"role": "system", "content": sys_instructions})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        resp = self._post(payload)
        try:
            choice = resp["choices"][0]
            msg = choice.get("message", {})
            raw_text = msg.get("content")
            if raw_text is None or not raw_text.strip():
                raw_text = msg.get("reasoning") or msg.get("reasoning_content") or ""
        except (KeyError, IndexError) as err:
            raise LLMError(
                f"[{self.provider.upper()}] Resposta inesperada da API: choices não encontrado.",
                provider=self.provider,
            ) from err

        return extract_json_payload(raw_text)
