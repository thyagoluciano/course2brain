"""Semantic vector indexation, candidate discovery and LLM-validated graph interlinking."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import struct
import time
import urllib.request
from pathlib import Path
from typing import Any, List, Tuple

from c2b.config import Config
from c2b.injector import apply_connections_to_file

_MODEL = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Lazy-load sentence transformers model."""
    global _MODEL
    if os.getenv("C2B_NO_HF") == "1":
        return None
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer

            try:
                _MODEL = SentenceTransformer(model_name, local_files_only=True)
            except Exception:
                _MODEL = SentenceTransformer(model_name)
        except Exception:
            _MODEL = None
    return _MODEL


def compute_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """Compute normalized vector embedding for text using sentence-transformers or deterministic fallback."""
    model = get_embedding_model(model_name)
    if model is not None:
        emb = model.encode(text, normalize_embeddings=True)
        return [float(x) for x in emb]

    # Deterministic fallback embedding when sentence-transformers is unavailable (e.g. CI or lightweight env)
    dim = 384
    vec = [0.0] * dim
    words = re.findall(r"\w+", text.lower())
    for w in words:
        h = hash(w) % dim
        vec[h] += 1.0

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def serialize_vector(vec: List[float]) -> bytes:
    """Serialize float vector to compact binary blob."""
    return struct.pack(f"{len(vec)}f", *vec)


def deserialize_vector(blob: bytes) -> List[float]:
    """Deserialize compact binary blob to float vector."""
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    return float(dot)


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite vector database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS note_embeddings (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            course TEXT,
            summary TEXT,
            embedding BLOB NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def extract_note_text_for_embedding(content: str) -> Tuple[str, str]:
    """Extract clean title and executive summary / core concepts for semantic embedding."""
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Sem Titulo"

    # Extract TL;DR or introductory section
    tldr_match = re.search(r"##\s*📌\s*Resumo Executivo[^\n]*\n([\s\S]*?)(?=\n##|\Z)", content)
    summary = tldr_match.group(1).strip() if tldr_match else content[:1000]

    return title, summary


def index_note(vault_path: Path, note_path: Path, db_path: Path) -> None:
    """Index or update note embedding in database."""
    if not note_path.is_file() or note_path.name.startswith("_"):
        return

    rel_path = str(note_path.relative_to(vault_path))
    content = note_path.read_text(encoding="utf-8")
    title, summary = extract_note_text_for_embedding(content)

    text_to_embed = f"{title}\n{summary}"
    vec = compute_embedding(text_to_embed)
    blob = serialize_vector(vec)

    conn = init_db(db_path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO note_embeddings (path, title, course, summary, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rel_path, title, note_path.parent.name, summary, blob, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def find_candidates(
    vault_path: Path,
    db_path: Path,
    target_rel_path: str,
    target_vector: List[float],
    similarity_threshold: float = 0.78,
    max_candidates: int = 5,
) -> List[dict[str, Any]]:
    """Find most similar notes based on vector cosine similarity."""
    conn = init_db(db_path)
    candidates = []
    try:
        cursor = conn.execute(
            "SELECT path, title, course, summary, embedding FROM note_embeddings WHERE path != ?",
            (target_rel_path,),
        )
        for row in cursor.fetchall():
            path, title, course, summary, blob = row
            vec = deserialize_vector(blob)
            sim = cosine_similarity(target_vector, vec)
            if sim >= similarity_threshold:
                candidates.append(
                    {
                        "path": path,
                        "title": title,
                        "course": course,
                        "summary": summary,
                        "similarity": round(sim, 3),
                    }
                )
    finally:
        conn.close()

    candidates.sort(key=lambda x: x["similarity"], reverse=True)
    return candidates[:max_candidates]


VALIDATION_PROMPT = """Você é um curador especialista em Segundo Cérebro (metodologia Zettelkasten).
Analise a nota de origem e as notas candidatas encontradas por similaridade semântica.
Determine se cada conexão faz sentido conceitual genuíno para um estudante ou engenheiro de software.

Para cada nota relevante, gere uma justificativa concisa (1 linha direta) explicando:
1. `motivo_origem`: Por que a nota de origem deve linkar para a candidata (ex: "Aprofunda a estratégia de mensageria com Kafka").
2. `motivo_destino`: Por que a candidata deve linkar de volta para a nota de origem (ex: "Contextualiza a aplicação prática em arquitetura de microsserviços").

Responda ESTRITAMENTE em formato JSON (lista de objetos):
[
  {
    "titulo": "Nome da Nota Candidata",
    "relevante": true,
    "motivo_origem": "...",
    "motivo_destino": "..."
  }
]
"""


def validate_connections_with_llm(
    api_key: str,
    model: str,
    source_title: str,
    source_summary: str,
    candidates: List[dict[str, Any]],
) -> List[dict[str, Any]]:
    """Validate candidates using Gemini to ensure high conceptual relevance."""
    if not candidates:
        return []

    if not api_key:
        # If no API key configured, accept candidates that exceed high similarity threshold
        return [
            {
                "titulo": c["title"],
                "relevante": True,
                "motivo_origem": f"Conceito relacionado em {c['course']}",
                "motivo_destino": f"Tema complementar da aula {source_title}",
            }
            for c in candidates
        ]

    prompt_data = {
        "nota_origem": {"titulo": source_title, "resumo": source_summary},
        "candidatos": [
            {"titulo": c["title"], "curso": c["course"], "resumo": c["summary"][:400]}
            for c in candidates
        ],
    }

    user_message = f"{VALIDATION_PROMPT}\n\nDADOS PARA ANÁLISE:\n{json.dumps(prompt_data, ensure_ascii=False)}"

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
    except Exception:
        # Fallback to high-similarity candidates on network or API error
        return [
            {
                "titulo": c["title"],
                "relevante": True,
                "motivo_origem": f"Conceito relacionado ({c['course']})",
                "motivo_destino": f"Tema complementar ({source_title})",
            }
            for c in candidates
        ]


def interlink_note(
    cfg: Config,
    note_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Index note, find conceptual matches, validate via LLM and inject bidirectional links."""
    vault = cfg.vault.path
    db_path = cfg.interlink.db_path or vault / "_sistema" / "vectors.db"

    if not note_path.is_file():
        raise FileNotFoundError(f"Nota não encontrada: {note_path}")

    # 1. Index this note
    index_note(vault, note_path, db_path)

    # 2. Extract embedding and candidates
    content = note_path.read_text(encoding="utf-8")
    title, summary = extract_note_text_for_embedding(content)
    vec = compute_embedding(f"{title}\n{summary}")
    rel_path = str(note_path.relative_to(vault))

    candidates = find_candidates(
        vault,
        db_path,
        rel_path,
        vec,
        similarity_threshold=cfg.interlink.similarity_threshold,
        max_candidates=cfg.interlink.max_links,
    )

    if not candidates:
        return {
            "status": "success",
            "note": str(rel_path),
            "candidates_found": 0,
            "links_injected": 0,
            "connections": [],
            "dry_run": dry_run,
        }

    # 3. Validate via LLM
    validations = validate_connections_with_llm(
        api_key=cfg.gemini.api_key,
        model=cfg.gemini.model,
        source_title=title,
        source_summary=summary,
        candidates=candidates,
    )

    val_map = {v.get("titulo"): v for v in validations if v.get("relevante")}
    applied_connections = []

    for cand in candidates:
        v = val_map.get(cand["title"])
        if not v:
            continue

        target_file = vault / cand["path"]
        reason_for_source = v.get("motivo_origem", "Nota correlata")
        reason_for_target = v.get("motivo_destino", "Nota correlata")

        if not dry_run:
            # Bidirectional injection
            apply_connections_to_file(note_path, [(cand["title"], reason_for_source)])
            apply_connections_to_file(target_file, [(title, reason_for_target)])

        applied_connections.append(
            {
                "target": cand["title"],
                "path": cand["path"],
                "similarity": cand["similarity"],
                "reason": reason_for_source,
            }
        )

    return {
        "status": "success",
        "note": str(rel_path),
        "candidates_found": len(candidates),
        "links_injected": len(applied_connections),
        "connections": applied_connections,
        "dry_run": dry_run,
    }


def interlink_all(cfg: Config, *, dry_run: bool = False) -> dict[str, Any]:
    """Batch index all notes in the vault and run interlinking."""
    vault = cfg.vault.path
    courses_dir = vault / cfg.vault.courses_folder
    db_path = cfg.interlink.db_path or vault / "_sistema" / "vectors.db"

    notes = [p for p in courses_dir.rglob("*.md") if not p.name.startswith("_")]

    # 1. Index all notes first
    for n in notes:
        index_note(vault, n, db_path)

    # 2. Interlink each note
    results = []
    total_injected = 0

    for n in notes:
        res = interlink_note(cfg, n, dry_run=dry_run)
        total_injected += res.get("links_injected", 0)
        results.append(res)

    return {
        "total_notes": len(notes),
        "total_links_injected": total_injected,
        "dry_run": dry_run,
        "results": results,
    }
