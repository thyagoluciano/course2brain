"""Module for knowledge synthesis using Google Gemini (SDK or direct REST API)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

SECOND_BRAIN_SYSTEM_PROMPT = """Você é um especialista em síntese de conhecimento e aprendizagem acelerada (metodologia Second Brain / Zettelkasten).

Sua missão é transformar a transcrição e os materiais da aula abaixo em um documento de estudo completo, denso e de alto valor no Obsidian.

Instruções Estruturais:
1. Resumo Executivo (TL;DR): 3 a 5 pontos essenciais capturando o cerne da aula.
2. Conceitos Fundamentais:
   - Divida em subtópicos lógicos.
   - Explique detalhadamente cada conceito, com exemplos práticos, analogias e motivações.
   - Destaque trade-offs técnicos ou metodológicos (vantagens vs desvantagens, quando usar e quando NÃO usar).
3. Aplicação Prática & Ações:
   - Checklist de passos concretos que o estudante pode aplicar em projetos reais.
4. Perguntas de Fixação (Active Recall):
   - 3 a 4 perguntas reflexivas profundas sobre os conceitos para autoavaliação futura.
5. Recursos & Referências:
   - Se houver ferramentas, bibliotecas, repositórios ou artigos citados na aula ou notas, liste-os contextualizando seu uso.
6. Tags sugeridas: Liste 3 a 5 tags temáticas no final (ex: #arquitetura, #decisao-tecnica, #design-patterns).

Não invente fatos que não estejam presentes na aula ou notas. Mantenha um tom profissional, didático e direto ao ponto. Use Markdown rico com listas, tabelas quando pertinente e negrito nos termos-chave.
"""


def summarize_lesson(
    api_key: str,
    title: str,
    course_name: str,
    notes_page: str,
    transcription: str,
    model: str = "gemini-3.8-flash",
) -> str:
    """Send lesson content to Gemini API and return structured Second Brain Markdown."""
    if not api_key:
        raise ValueError(
            "Chave de API do Gemini não configurada! Defina em c2b.toml ou na variável de ambiente GEMINI_API_KEY."
        )

    content_bundle = f"""
CURSO: {course_name}
TÍTULO DA AULA: {title}

--- NOTAS E MATERIAIS DA PÁGINA ---
{notes_page or "Nenhuma nota escrita fornecida."}

--- TRANSCRIÇÃO / FALA DO INSTRUTOR ---
{transcription or "Nenhuma transcrição de áudio fornecida."}
"""

    # Try official google.genai SDK
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[SECOND_BRAIN_SYSTEM_PROMPT, content_bundle],
        )
        return response.text
    except ImportError:
        # Fallback to direct Gemini REST API
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": SECOND_BRAIN_SYSTEM_PROMPT},
                        {"text": content_bundle},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
            },
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Erro na API do Gemini (HTTP {e.code}): {err_body}") from e
