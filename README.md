# 🧠 course2brain

> **Transform online courses and communities into an interlinked Obsidian Second Brain knowledge graph.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Chrome Extension Manifest V3](https://img.shields.io/badge/extension-Manifest%20V3-success.svg)](extension/)
[![CI](https://github.com/thyagoluciano/course2brain/actions/workflows/ci.yml/badge.svg)](https://github.com/thyagoluciano/course2brain/actions)

Online courses and learning communities (Circle.so, Skool, Hotmart, etc.) contain hundreds of hours of high-value knowledge. However, watching videos passively often results in fragmented, quickly forgotten notes.

**course2brain** bridges this gap: with a single click in your browser, it captures lesson materials, transcribes and cleans subtitles, structures comprehensive **Second Brain / Zettelkasten** study notes via Google Gemini, and automatically discovers semantic connections across different courses—weaving lessons into a living, interconnected **Obsidian Graph View**.

---

## ✨ Features

- ⚡ **Modular Browser Extension (Manifest V3)**: Minimalist Chrome popup that detects learning platforms and extracts titles, captions, rich notes, and reference links.
- 🔌 **Pluggable Extractor Strategy**: Clean `BaseExtractor` interface making it trivial to add support for any learning platform (`Circle.so`, `Skool`, `Coursera`, etc.).
- 🏗️ **Instant Vault Scaffolder (`c2b init-vault`)**: Bootstraps an Obsidian Second Brain in seconds with study folders (`00-Inbox/`, `10-Cursos/`, `20-Conceitos/`), note templates, and pre-calibrated Graph View colors.
- 🤖 **Deep Cognitive Synthesis**: Generates high-density study notes (Executive Summary, Core Concepts with Trade-offs, Practical Engineering Checklists, Active Recall questions) using Gemini 3.8 Flash.
- 🕸️ **Flexible Vault Indexing & Auto-Interlink**: Discovers conceptually related notes across courses, articles (`50-Conteudo/`), concepts (`20-Conceitos/`), or the entire vault (`["*"]`). Uses vector search (`sqlite-vec`) and AI validation to inject bidirectional wikilinks into `## 🔗 Conexões Relacionadas`.
- 🛡️ **Zero-ToS-Risk & Local Plugin System**: Public codebase has zero video scraping or DRM bypass routines. Private plugins (e.g., local video downloaders for external drives) live safely in the gitignored `plugins/` directory.

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COURSE2BRAIN ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

 [Browser: Course / Community Platform]
       │
       ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ CHROME EXTENSION (Manifest V3)                                          │
 ├─────────────────────────────────────────────────────────────────────────┤
 │ • content.js ➔ Coordenador e despachante dinâmico                       │
 │ • extractors/base.js ➔ Interface do Extrator (Strategy Pattern)         │
 │ • extractors/circle.js ➔ Extrator Circle.so com seletores em cascata    │
 │ • extractors/<plataforma>.js ➔ Plugável pela comunidade                 │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      │ HTTP POST /api/process (JSON)
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ LOCAL ENGINE: c2b serve (FastAPI na porta 8765)                         │
 ├─────────────────────────────────────────────────────────────────────────┤
 │ 1. Plugins Hook: `on_pre_process(payload)` (e.g. private media handler) │
 │ 2. Subtitle Normalizer: WebVTT / SRT to readable paragraphs             │
 │ 3. Cognitive Synthesizer: Google Gemini 3.8 Flash Second Brain prompt   │
 │ 4. Vault Writer: Atomic save to `10-Cursos/<Curso>/<Aula>.md` + MOCs    │
 │ 5. Plugins Hook: `on_post_save(note_path)`                              │
 │ 6. Auto-Interlink Engine: Vector similarity + LLM connection injection  │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ OBSIDIAN KNOWLEDGE GRAPH (Second Brain Vault)                           │
 ├─────────────────────────────────────────────────────────────────────────┤
 │ • 00-Inbox/                                                             │
 │ • 10-Cursos/<Nome_do_Curso>/<Nome_da_Aula>.md                           │
 │ • 20-Conceitos/                                                         │
 │ • _sistema/ (templates, vetores e relatórios)                           │
 │ • Graph View interconectado nativamente                                 │
 └─────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.11 or higher
- [Obsidian](https://obsidian.md/)
- Google Gemini API Key ([Get one for free at Google AI Studio](https://aistudio.google.com/))
- Google Chrome or Chromium-based browser

### 2. Installation

Clone and install dependencies (recommended using [`uv`](https://github.com/astral-sh/uv)):

```bash
git clone https://github.com/thyagoluciano/course2brain.git
cd course2brain

# 1. Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install in editable mode with development dependencies
uv pip install -e ".[dev]"
```

> **Tip**: If you prefer standard Python tools without `uv`:
> ```bash
> python -m venv .venv
> source .venv/bin/activate  # On Windows: .venv\Scripts\activate
> pip install -e ".[dev]"
> ```

### 3. Initialize your Obsidian Study Vault

Create a ready-to-use Second Brain vault (or point to your existing vault):

```bash
c2b init-vault ~/Obsidian/SecondBrain
```

### 4. Configuration

Copy the example configuration:

```bash
cp c2b.example.toml c2b.toml
```

Edit `c2b.toml` or set your environment variables:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export C2B_VAULT_PATH="~/Obsidian/SecondBrain"
```

You can customize which vault folders participate in the semantic graph:

```toml
[interlink]
# Specific folders or ["*"] for the entire vault
include_folders = ["10-Cursos", "50-Conteudo", "20-Conceitos"]
exclude_folders = [".obsidian", "_sistema", ".trash", "90-Templates", ".git"]
```

### 5. Install the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **Load unpacked**
4. Select the `course2brain/extension/` folder in this repository

### 6. Start the Local Engine

```bash
c2b serve
```

---

## 📖 Usage Guide

1. Navigate to your course or community lesson (e.g. on Circle.so).
2. Click the **course2brain** extension icon in your browser toolbar.
3. Verify that the server status indicator shows **Servidor Ativo** (green).
4. Click **Sintetizar & Salvar no Brain**.
5. Switch to Obsidian:
   - Your lesson note is saved under `10-Cursos/<Nome_do_Curso>/<Nome_da_Aula>.md`.
   - The course MOC (`_Indice - <Curso>.md`) is updated automatically.
   - Related lessons are connected in `## 🔗 Conexões Relacionadas` and linked in your Graph View (`Cmd + G` or `Ctrl + G`).

---

## 🛠️ CLI Reference

```bash
# Start local processing server
c2b serve --port 8765

# Initialize or inspect a study vault
c2b init-vault /path/to/vault

# Re-index and interlink notes in configured folders (include_folders)
c2b link --all

# Force re-indexing and interlinking across the ENTIRE Obsidian vault
c2b link --vault

# Index and interlink a specific folder under the vault
c2b link --folder "50-Conteudo"

# Interlink a specific note anywhere in the vault
c2b link "50-Conteudo/Substack/Artigo.md"

# Simulate interlinking without modifying files
c2b link --all --dry-run

# Check current configuration, vault status and active plugins
c2b status
```

> **Tip**: `c2b link`, `c2b interlink`, and `c2b linkar` are fully interchangeable aliases. You can also use `-a` or `--tudo` for `--all`.

---

## 🔌 Creating Local Plugins

To add private automation (such as downloading media to an external drive or triggering webhooks) without committing private code to GitHub:

1. Place your script inside `plugins/` (e.g. `plugins/my_plugin.py`).
2. Implement either hook:
   ```python
   def on_pre_process(payload: dict, config) -> dict:
       # Modify or enrich payload before Gemini summarization
       return payload


   def on_post_save(note_path, payload: dict, config) -> None:
       # Run actions after the note is saved
       pass
   ```
3. See [plugins/README.md](plugins/README.md) for detailed examples.

---

## 🤝 Contributing & Adding New Extractors

Contributions from the community are warmly welcome! If you'd like to add support for a new learning platform:

1. Read our [CONTRIBUTING.md](CONTRIBUTING.md) guide.
2. Create a new extractor subclass in `extension/extractors/<platform>.js` extending `BaseExtractor`.
3. Test extraction on the target platform.
4. Open a Pull Request!

Please make sure tests and linting pass before submitting:
```bash
pytest
ruff check .
```

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

Developed with ❤️ by **[Thyago Luciano](https://github.com/thyagoluciano)**.
