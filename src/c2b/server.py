"""Local FastAPI HTTP server for receiving course content from the browser extension."""

from __future__ import annotations

import logging
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
from c2b.vault import format_lesson_note, save_lesson_note

logger = logging.getLogger(__name__)


class LessonLink(BaseModel):
    texto: str = ""
    url: str = ""


class LessonRequest(BaseModel):
    platform: str = "generic"
    course_name: str = "Curso Online"
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
        return {
            "status": "online",
            "version": __version__,
            "vault": str(active_cfg.vault.path),
            "gemini_model": active_cfg.gemini.model,
            "interlink_enabled": active_cfg.interlink.enabled,
        }

    @app.post("/api/process", response_model=ProcessResponse)
    def process_lesson(req: LessonRequest):
        active_cfg: Config = app.state.config
        payload = req.model_dump()

        # 1. Run pre-processing plugin hooks (e.g. video downloader)
        try:
            payload = run_pre_process_hooks(payload, active_cfg)
        except Exception as e:
            logger.warning("Plugin hook error: %s", e)

        title = payload.get("title") or "Aula Sem Titulo"
        course_name = payload.get("course_name") or "Curso Online"
        captions_raw = payload.get("captions_text") or ""
        notes_raw = payload.get("notes_text") or ""
        page_url = payload.get("page_url") or ""
        local_media_path = payload.get("local_media_path")
        links = payload.get("links") or []

        # 2. Clean captions
        cleaned_captions = clean_vtt(captions_raw) if "WEBVTT" in captions_raw else captions_raw

        # 3. Cognitive synthesis via Gemini
        try:
            summary = summarize_lesson(
                api_key=active_cfg.gemini.api_key,
                title=title,
                course_name=course_name,
                notes_page=notes_raw,
                transcription=cleaned_captions,
                model=active_cfg.gemini.model,
            )
        except Exception as e:
            logger.error("Gemini synthesis error: %s", e)
            raise HTTPException(status_code=500, detail=f"Erro na síntese com Gemini: {e}") from e

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
        )

        # 5. Save note to Vault
        try:
            saved_path = save_lesson_note(
                vault_path=active_cfg.vault.path,
                courses_folder=active_cfg.vault.courses_folder,
                course_name=course_name,
                title=title,
                content=formatted_md,
            )
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
                interlink_res = interlink_note(active_cfg, saved_path)
                interlinks_count = interlink_res.get("links_injected", 0)
            except Exception as e:
                logger.warning("Auto-interlink error: %s", e)

        rel_note = str(saved_path.relative_to(active_cfg.vault.path))

        return ProcessResponse(
            success=True,
            title=title,
            course=course_name,
            note_file=rel_note,
            interlinks_count=interlinks_count,
        )

    return app
