from pathlib import Path

from c2b.injector import (
    apply_connections_to_file,
    extract_wikilinks,
    inject_connections_into_markdown,
)


def test_extract_wikilinks():
    texto = "Veja [[Nota A]] e também [[Nota B|Alias]] além de [[Outra Nota.md]]."
    alvos = extract_wikilinks(texto)
    assert "nota a" in alvos
    assert "nota b" in alvos
    assert "outra nota" in alvos


def test_inject_connections_new_section():
    initial = """# Minha Aula

Texto da aula sobre arquitetura.
"""
    conexoes = [
        ("Design Patterns", "Aprofunda o padrão Factory"),
        ("Clean Architecture", "Contextualiza a divisão de camadas"),
    ]
    updated = inject_connections_into_markdown(initial, conexoes)
    assert "## 🔗 Conexões Relacionadas" in updated
    assert "- [[Design Patterns]]: Aprofunda o padrão Factory" in updated
    assert "- [[Clean Architecture]]: Contextualiza a divisão de camadas" in updated


def test_inject_connections_idempotent():
    initial = """# Minha Aula

## 🔗 Conexões Relacionadas
- [[Design Patterns]]: Aprofunda o padrão Factory
"""
    conexoes = [
        ("Design Patterns", "Nova tentativa de motivo"),
        ("Clean Architecture", "Nova conexão"),
    ]
    updated = inject_connections_into_markdown(initial, conexoes)
    # Design Patterns should not be duplicated
    assert updated.count("[[Design Patterns]]") == 1
    assert "- [[Clean Architecture]]: Nova conexão" in updated


def test_inject_before_transcription_section():
    initial = """# Minha Aula

Resumo da aula.

---
## 📝 Transcrição & Notas Brutas
<details>
Texto da transcrição...
</details>
"""
    conexoes = [("Microsserviços", "Padrão de comunicação")]
    updated = inject_connections_into_markdown(initial, conexoes)

    pos_conexoes = updated.find("## 🔗 Conexões Relacionadas")
    pos_transcricao = updated.find("## 📝 Transcrição")
    assert pos_conexoes < pos_transcricao


def test_apply_connections_to_file(tmp_path: Path):
    file_path = tmp_path / "Aula.md"
    file_path.write_text("# Aula Teste\n\nConteúdo.", encoding="utf-8")

    changed = apply_connections_to_file(file_path, [("Nota Destino", "Motivo")])
    assert changed is True
    assert "## 🔗 Conexões Relacionadas" in file_path.read_text(encoding="utf-8")

    # Second run should be no-op
    changed_again = apply_connections_to_file(file_path, [("Nota Destino", "Motivo")])
    assert changed_again is False
