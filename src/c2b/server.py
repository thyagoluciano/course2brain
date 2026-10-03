"""Local FastAPI HTTP server for receiving course content from the browser extension."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from c2b import __version__
from c2b.config import Config, load_config
from c2b.interlink import interlink_note
from c2b.plugins import run_post_save_hooks, run_pre_process_hooks
from c2b.summarizer import summarize_lesson
from c2b.transcription import clean_vtt
from c2b.vault import format_lesson_note, list_vault_folders, save_lesson_note

logger = logging.getLogger("uvicorn.error")



class LessonLink(BaseModel):
    texto: str = ""
    url: str = ""


class LessonRequest(BaseModel):
    platform: str = "generic"
    course_name: str = "Curso Online"
    space_name: Optional[str] = None
    section_name: Optional[str] = None
    title: str = "Aula Sem Titulo"
    captions_text: str = ""
    notes_text: str = ""
    links: List[LessonLink] = Field(default_factory=list)
    page_url: str = ""
    media_url: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool
    title: str
    course: str
    note_file: str
    interlinks_count: int = 0
    detail: Optional[str] = None


def create_app(cfg: Optional[Config] = None) -> FastAPI:
    """Create configured FastAPI application instance."""
    app = FastAPI(
        title="course2brain Local Server",
        version=__version__,
        description="Local processing engine connecting Chrome Extension to Obsidian Second Brain",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = cfg or load_config()

    @app.get("/api/health")
    @app.get("/api/status")
    def health_check():
        active_cfg: Config = app.state.config
        synth_client = active_cfg.get_llm_client_for_task("synthesis")
        inter_client = active_cfg.get_llm_client_for_task("interlink")
        return {
            "status": "online",
            "version": __version__,
            "vault": str(active_cfg.vault.path),
            "gemini_model": synth_client.model if synth_client.provider == "gemini" else active_cfg.gemini.model,
            "ai_synthesis_provider": synth_client.provider,
            "ai_synthesis_model": synth_client.model,
            "ai_interlink_provider": inter_client.provider,
            "ai_interlink_model": inter_client.model,
            "interlink_enabled": active_cfg.interlink.enabled,
        }

    @app.get("/api/vault/folders")
    def get_vault_folders():
        active_cfg: Config = app.state.config
        folders = list_vault_folders(active_cfg.vault.path)
        return {
            "status": "ok",
            "vault": str(active_cfg.vault.path),
            "default_folder": active_cfg.vault.courses_folder,
            "folders": folders,
        }

    @app.post("/api/process", response_model=ProcessResponse)
    def process_lesson(req: LessonRequest):
        t_total_start = time.time()
        active_cfg: Config = app.state.config
        payload = req.model_dump()

        raw_title = payload.get("title") or "Aula Sem Titulo"
        raw_course = payload.get("course_name") or "Curso Online"
        logger.info("📥 Recebida requisição para processar aula: '%s' (%s)", raw_title, raw_course)

        # 1. Run pre-processing plugin hooks (e.g. video downloader)
        t_pre = time.time()
        try:
            payload = run_pre_process_hooks(payload, active_cfg)
            elapsed_pre = time.time() - t_pre
            if elapsed_pre > 0.5:
                logger.info("  [1/4] Pré-processamento concluído em %.1fs", elapsed_pre)
        except Exception as e:
            logger.warning("Plugin hook error: %s", e)

        title = payload.get("title") or raw_title
        course_name = payload.get("course_name") or raw_course
        space_name = payload.get("space_name")
        section_name = payload.get("section_name")
        captions_raw = payload.get("captions_text") or ""
        notes_raw = payload.get("notes_text") or ""
        page_url = payload.get("page_url") or ""
        local_media_path = payload.get("local_media_path")
        links = payload.get("links") or []

        # 2. Clean captions
        cleaned_captions = clean_vtt(captions_raw) if "WEBVTT" in captions_raw else captions_raw

        # 3. Cognitive synthesis via configured LLM provider
        try:
            synth_client = active_cfg.get_llm_client_for_task("synthesis")
            logger.info(
                "  [2/4] Gerando síntese via [%s] %s...",
                synth_client.provider.upper(),
                synth_client.model,
            )
            t_synth = time.time()
            summary = summarize_lesson(
                title=title,
                course_name=course_name,
                notes_page=notes_raw,
                transcription=cleaned_captions,
                client=synth_client,
            )
            elapsed_synth = time.time() - t_synth
            logger.info(
                "  [2/4] Síntese concluída em %.1fs (%d caracteres gerados).",
                elapsed_synth,
                len(summary),
            )
        except Exception as e:
            logger.error("LLM synthesis error: %s", e)
            raise HTTPException(status_code=500, detail=f"Erro na síntese de conhecimento: {e}") from e

        # 4. Format Second Brain note
        formatted_md = format_lesson_note(
            title=title,
            course_name=course_name,
            platform=payload.get("platform", "generic"),
            summary_content=summary,
            page_url=page_url,
            local_media_path=local_media_path,
            raw_transcription=cleaned_captions or notes_raw,
            links=links,
            media_url=payload.get("media_url"),
            space_name=space_name,
            section_name=section_name,
        )

        # 5. Save note to Vault
        try:
            saved_path = save_lesson_note(
                vault_path=active_cfg.vault.path,
                courses_folder=active_cfg.vault.courses_folder,
                course_name=course_name,
                title=title,
                content=formatted_md,
                space_name=space_name,
                section_name=section_name,
            )
            logger.info("  [3/4] Nota salva no cofre: %s", saved_path.name)
        except Exception as e:
            logger.error("Error saving note to vault: %s", e)
            raise HTTPException(status_code=500, detail=f"Erro ao salvar nota no vault: {e}") from e

        # 6. Run post-save plugin hooks
        try:
            run_post_save_hooks(saved_path, payload, active_cfg)
        except Exception as e:
            logger.warning("Post-save plugin error: %s", e)

        # 7. Auto-interlink with existing notes
        interlinks_count = 0
        if active_cfg.interlink.enabled:
            try:
                inter_client = active_cfg.get_llm_client_for_task("interlink")
                logger.info(
                    "  [4/4] Validando conexões no grafo via [%s] %s...",
                    inter_client.provider.upper(),
                    inter_client.model,
                )
                t_inter = time.time()
                interlink_res = interlink_note(active_cfg, saved_path)
                interlinks_count = interlink_res.get("links_injected", 0)
                elapsed_inter = time.time() - t_inter
                logger.info(
                    "  [4/4] Auto-interlink concluído em %.1fs (%d conexões inseridas).",
                    elapsed_inter,
                    interlinks_count,
                )
            except Exception as e:
                logger.warning("Auto-interlink error: %s", e)

        total_elapsed = time.time() - t_total_start
        rel_note = str(saved_path.relative_to(active_cfg.vault.path))
        logger.info("✨ Aula processada com sucesso no Second Brain em %.1fs: %s", total_elapsed, rel_note)

        return ProcessResponse(
            success=True,
            title=title,
            course=course_name,
            note_file=rel_note,
            interlinks_count=interlinks_count,
        )

    return app
