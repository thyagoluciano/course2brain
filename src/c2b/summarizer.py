"""Module for knowledge synthesis using universal LLM providers (OpenRouter, Gemini, OpenAI, etc.)."""

from __future__ import annotations

import logging

from c2b.llm import UnifiedLLMClient

logger = logging.getLogger(__name__)


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
7. Idioma & Localização: Todo o conteúdo estruturado gerado DEVE estar em Português do Brasil (PT-BR) claro, didático e de alto nível técnico. Se a aula, notas ou transcrição original estiverem em inglês ou outro idioma, traduza e sintetize integralmente para o Português do Brasil, preservando apenas termos e nomes técnicos padrão da indústria quando conveniente (ex: stop_reason, token budget, prompt caching, harness) sempre explicando seus conceitos em português.

Não invente fatos que não estejam presentes na aula ou notas. Mantenha um tom profissional, didático e direto ao ponto. Use Markdown rico com listas, tabelas quando pertinente e negrito nos termos-chave.
"""


def summarize_lesson(
    api_key: str = "",
    title: str = "",
    course_name: str = "",
    notes_page: str = "",
    transcription: str = "",
    model: str = "",
    *,
    client: UnifiedLLMClient | None = None,
    provider: str = "gemini",
) -> str:
    """Send lesson content to configured LLM provider and return structured Second Brain Markdown."""
    content_bundle = f"""
CURSO: {course_name}
TÍTULO DA AULA: {title}

--- NOTAS E MATERIAIS DA PÁGINA ---
{notes_page or "Nenhuma nota escrita fornecida."}

--- TRANSCRIÇÃO / FALA DO INSTRUTOR ---
{transcription or "Nenhuma transcrição de áudio fornecida."}
""".strip()

    # 1. Use explicit client if provided
    if client is not None:
        return client.generate_text(
            prompt=content_bundle,
            system_prompt=SECOND_BRAIN_SYSTEM_PROMPT,
            temperature=0.4,
        )

    # 2. Try official google.genai SDK if provider is gemini and key exists
    if provider == "gemini" and api_key:
        try:
            from google import genai

            sdk_client = genai.Client(api_key=api_key)
            response = sdk_client.models.generate_content(
                model=model or "gemini-3.8-flash",
                contents=[SECOND_BRAIN_SYSTEM_PROMPT, content_bundle],
            )
            return response.text
        except ImportError:
            pass

    # 3. Fallback to UnifiedLLMClient
    if not api_key:
        raise ValueError(
            "Chave de API de IA não configurada! Defina em c2b.toml ou na variável de ambiente correspondente (ex: OPENROUTER_API_KEY ou GEMINI_API_KEY)."
        )

    resolved_model = model or ("google/gemma-4-31b-it:free" if provider == "openrouter" else "gemini-3.8-flash")
    llm = UnifiedLLMClient(
        provider=provider,
        api_key=api_key,
        model=resolved_model,
    )
    return llm.generate_text(
        prompt=content_bundle,
        system_prompt=SECOND_BRAIN_SYSTEM_PROMPT,
        temperature=0.4,
    )
