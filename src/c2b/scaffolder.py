from __future__ import annotations

import json
from pathlib import Path
from typing import List

GRAPH_CONFIG = {
    "collapse-filter": False,
    "search": "",
    "localJumps": 1,
    "localBacklinks": True,
    "localForelinks": True,
    "localInterlinks": True,
    "showTags": True,
    "showAttachments": False,
    "hideUnresolved": False,
    "showOrphans": True,
    "collapse-color-groups": False,
    "colorGroups": [
        {"query": "tag:#curso", "color": {"a": 1, "rgb": 3669702}},      # Cyan/Teal
        {"query": "tag:#conceito", "color": {"a": 1, "rgb": 15024467}},   # Purple/Magenta
        {"query": "path:10-Cursos", "color": {"a": 1, "rgb": 5753820}},   # Green
        {"query": "path:20-Conceitos", "color": {"a": 1, "rgb": 16098851}} # Orange
    ],
    "collapse-display": False,
    "showArrow": True,
    "textFadeMultiplier": 0,
    "nodeSizeMultiplier": 1.15,
    "lineSizeMultiplier": 1,
    "collapse-forces": False,
    "centerStrength": 0.518,
    "repelStrength": 10,
    "linkStrength": 1,
    "linkDistance": 250,
    "scale": 1.0,
    "close": False
}

APP_CONFIG = {
    "legacyEditor": False,
    "livePreview": True,
    "useTab": True,
    "tabSize": 2,
    "newFileLocation": "folder",
    "newFileFolderPath": "00-Inbox",
    "attachmentFolderPath": "_sistema/anexos"
}

LESSON_TEMPLATE = """---
tipo: aula
curso: "{{curso}}"
plataforma: "{{plataforma}}"
data_processamento: "{{data}}"
tags:
  - curso
  - aula
  - second-brain
---

# {{titulo}}

> **Curso:** [[{{curso}}]]
> **Plataforma:** {{plataforma}} | [Acessar Aula na Web]({{url_aula}})

---

## 📌 Resumo Executivo (TL;DR)
{{resumo_executivo}}

---

## 💡 Conceitos Fundamentais
{{conceitos}}

---

## 🧠 Active Recall & Fixação
{{active_recall}}

---

## 🔗 Conexões Relacionadas
{{conexoes}}
"""

DASHBOARD_TEMPLATE = """# 🧠 Second Brain Knowledge Hub

Bem-vindo ao seu cofre de estudos impulsionado pelo **course2brain**!

Esta estrutura foi calibrada com a metodologia *Zettelkasten* e *Second Brain*, focada em transformar horas passivas assistindo cursos em um grafo ativo de conhecimento permanente.

---

## 📁 Estrutura do Vault

- **[[00-Inbox]]**: Capturas rápidas e anotações brutas que precisam de triagem.
- **[[10-Cursos]]**: Aulas e cursos sintetizados via extensão do navegador. Cada curso possui seu próprio índice (MOC).
- **[[20-Conceitos]]**: Notas atômicas reutilizáveis que conectam ideias aprendidas entre diferentes cursos.
- **`_sistema/`**: Templates de notas, banco de vetores semânticos e relatórios automatizados.

---

## 🚀 Como Usar o course2brain

1. **Inicie o servidor local**:
   ```bash
   c2b serve
   ```
2. **Abra o curso no navegador**:
   Acesse a aula na sua plataforma de estudo (ex: Circle.so, Skool).
3. **Clique na extensão `course2brain`**:
   O conteúdo é automaticamente extraído, transcrito, sintetizado pelo Gemini e gravado neste vault.
4. **Explore o Graph View**:
   Pressione `Ctrl + G` (ou `Cmd + G` no Mac). À medida que novas aulas forem adicionadas, o motor de auto-interligação conectará temas afins automaticamente na seção `## 🔗 Conexões Relacionadas`!

---

*Gerado com sucesso pelo `c2b init-vault`.*
"""


def init_vault(target_path: Path | str) -> List[Path]:
    """
    Initialize an Obsidian Second Brain vault structure.
    Returns list of created directories and files.
    """
    vault = Path(target_path).expanduser().resolve()
    created: List[Path] = []

    # 1. Directory hierarchy
    directories = [
        vault / "00-Inbox",
        vault / "10-Cursos",
        vault / "20-Conceitos",
        vault / "_sistema" / "templates",
        vault / "_sistema" / "relatorios",
        vault / "_sistema" / "anexos",
        vault / ".obsidian",
    ]

    for d in directories:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

    # 2. .obsidian/app.json
    app_json = vault / ".obsidian" / "app.json"
    if not app_json.exists():
        app_json.write_text(json.dumps(APP_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        created.append(app_json)

    # 3. .obsidian/graph.json
    graph_json = vault / ".obsidian" / "graph.json"
    if not graph_json.exists():
        graph_json.write_text(json.dumps(GRAPH_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        created.append(graph_json)

    # 4. _sistema/templates/Template - Aula de Curso.md
    template_file = vault / "_sistema" / "templates" / "Template - Aula de Curso.md"
    if not template_file.exists():
        template_file.write_text(LESSON_TEMPLATE, encoding="utf-8")
        created.append(template_file)

    # 5. Dashboard.md
    dashboard_file = vault / "Dashboard.md"
    if not dashboard_file.exists():
        dashboard_file.write_text(DASHBOARD_TEMPLATE, encoding="utf-8")
        created.append(dashboard_file)

    return created
