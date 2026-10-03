"""Command-line interface (CLI) for course2brain."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from c2b import __version__
from c2b.config import load_config
from c2b.interlink import interlink_all, interlink_note
from c2b.plugins import find_plugin_directories, load_plugins
from c2b.scaffolder import init_vault
from c2b.server import create_app

app = typer.Typer(
    name="c2b",
    help="🧠 course2brain: Transform online courses into an interlinked Obsidian Second Brain knowledge graph.",
    add_completion=False,
)
console = Console()


@app.command("version")
def version():
    """Show installed course2brain version."""
    console.print(f"[bold cyan]course2brain[/bold cyan] v{__version__}")


@app.command("status")
def status(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Caminho do arquivo c2b.toml"
    ),
):
    """Exibe o status da configuração, vault do Obsidian e plugins."""
    cfg = load_config(config_file)
    plugins = load_plugins()
    plugin_dirs = find_plugin_directories()

    table = Table(title="🧠 Status do course2brain", show_header=True, header_style="bold magenta")
    table.add_column("Componente", style="dim", width=22)
    table.add_column("Valor / Configuração")

    table.add_row("Versão", f"v{__version__}")
    table.add_row("Caminho do Vault", str(cfg.vault.path))
    table.add_row(
        "Existe no Disco?", "[green]Sim[/green]" if cfg.vault.path.exists() else "[red]Não[/red]"
    )
    table.add_row("Pasta de Cursos", cfg.vault.courses_folder)
    synth_llm = cfg.get_llm_client_for_task("synthesis")
    inter_llm = cfg.get_llm_client_for_task("interlink")

    table.add_row("Síntese de Aulas", f"[{synth_llm.provider.upper()}] {synth_llm.model}")
    table.add_row(
        "Chave IA Síntese?",
        "[green]Sim[/green]"
        if bool(synth_llm.api_key) or synth_llm.provider == "ollama"
        else "[yellow]Não configurada[/yellow]",
    )
    table.add_row("Validação Interlink", f"[{inter_llm.provider.upper()}] {inter_llm.model}")
    table.add_row(
        "Chave IA Interlink?",
        "[green]Sim[/green]"
        if bool(inter_llm.api_key) or inter_llm.provider == "ollama"
        else "[yellow]Não configurada[/yellow]",
    )

    table.add_row(
        "Auto-Interlink Ativo?",
        "[green]Sim[/green]" if cfg.interlink.enabled else "[yellow]Não[/yellow]",
    )
    table.add_row("Limiar de Similaridade", str(cfg.interlink.similarity_threshold))
    table.add_row("Porta do Servidor", f"{cfg.server.host}:{cfg.server.port}")
    table.add_row("Plugins Detectados", f"{len(plugins)} módulos ativos")

    console.print(table)


    if plugin_dirs:
        console.print(
            f"[dim]Pastas de plugins observadas: {', '.join(str(d) for d in plugin_dirs)}[/dim]"
        )


@app.command("init-vault")
def init_vault_cmd(
    target_path: Path = typer.Argument(
        ..., help="Caminho onde o Vault do Obsidian será inicializado"
    ),
):
    """Inicializa a estrutura do Vault Second Brain para Obsidian."""
    console.print(f"[cyan]Inicializando Second Brain em:[/cyan] [bold]{target_path}[/bold]...")
    created = init_vault(target_path)

    if not created:
        console.print(
            "[yellow]O Vault já possuía todas as pastas e templates configurados![/yellow]"
        )
        return

    console.print(f"[bold green]✓ Sucesso![/bold green] {len(created)} itens estruturados:")
    for item in created:
        rel = (
            item.relative_to(target_path.resolve())
            if item.is_relative_to(target_path.resolve())
            else item
        )
        console.print(f"  [dim]+[/dim] {rel}")

    console.print("\n[bold]Próximos passos:[/bold]")
    console.print("1. Abra esta pasta no Obsidian.")
    console.print("2. Inicie o servidor local: [cyan]c2b serve[/cyan]")
    console.print("3. Instale a extensão no Chrome e comece a estudar!")


@app.command("serve")
def serve(
    host: Optional[str] = typer.Option(None, "--host", "-h", help="Endereço de escuta do servidor"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Porta do servidor HTTP"),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Arquivo c2b.toml customizado"
    ),
):
    """Inicia o servidor local para receber capturas da extensão Chrome."""
    cfg = load_config(config_file)
    listen_host = host or cfg.server.host
    listen_port = port or cfg.server.port

    synth_llm = cfg.get_llm_client_for_task("synthesis")
    inter_llm = cfg.get_llm_client_for_task("interlink")

    banner = f"""[bold cyan]course2brain local server[/bold cyan] [dim]v{__version__}[/dim]
Escutando em: [green]http://{listen_host}:{listen_port}[/green]
Vault Obsidian: [yellow]{cfg.vault.path}[/yellow]
Síntese de Aulas: [magenta][{synth_llm.provider.upper()}] {synth_llm.model}[/magenta]
Validação Interlink: [magenta][{inter_llm.provider.upper()}] {inter_llm.model}[/magenta]
Auto-Interlink: {"[green]Ativado[/green]" if cfg.interlink.enabled else "[yellow]Desativado[/yellow]"}"""

    console.print(Panel(banner, border_style="cyan"))


    app_instance = create_app(cfg)
    uvicorn.run(app_instance, host=listen_host, port=listen_port, log_level="info")


@app.command("linkar")
@app.command("link")
@app.command("interlink")
def linkar(
    nota: Optional[str] = typer.Argument(None, help="Caminho ou nome da nota a interligar"),
    all_notes: bool = typer.Option(
        False, "--all", "-a", "--tudo", help="Interligar notas do escopo configurado no c2b.toml"
    ),
    vault: bool = typer.Option(
        False, "--vault", help="Forçar interligação em TODO o cofre Obsidian"
    ),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Pasta específica dentro do cofre para interligar"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Apenas simular sem alterar os arquivos"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Arquivo c2b.toml"),
):
    """Executa a descoberta semântica e conecta notas no Grafo do Obsidian."""
    cfg = load_config(config_file)

    if vault or folder or all_notes or not nota:
        folders_param = [folder] if folder else None
        whole_vault = vault

        if whole_vault:
            scope_desc = "em TODO o cofre Obsidian"
        elif folder:
            scope_desc = f"na pasta '{folder}'"
        else:
            inc = cfg.interlink.include_folders or [cfg.vault.courses_folder]
            scope_desc = f"nas pastas configuradas: {', '.join(inc)}"

        console.print(f"[cyan]Executando Auto-Interlink {scope_desc}...[/cyan]")
        res = interlink_all(cfg, folders=folders_param, whole_vault=whole_vault, dry_run=dry_run)
        total_notes = res.get("total_notes", 0)
        total_links = res.get("total_links_injected", 0)
        mode_str = "[yellow](Dry Run)[/yellow]" if dry_run else ""
        console.print(
            f"[bold green]✓ Concluído {mode_str}:[/bold green] {total_notes} notas analisadas, {total_links} conexões injetadas no Grafo!"
        )
        return

    # Interligar nota específica
    caminho_nota = Path(nota)
    if not caminho_nota.is_absolute():
        caminho_nota = (cfg.vault.path / nota).resolve()
        if not caminho_nota.exists():
            caminho_nota = (cfg.vault.path / cfg.vault.courses_folder / nota).resolve()

    if not caminho_nota.exists():
        console.print(f"[red]Erro:[/red] Nota não encontrada em: {caminho_nota}")
        raise typer.Exit(code=1)

    console.print(f"[cyan]Analisando conexões para:[/cyan] [bold]{caminho_nota.name}[/bold]...")
    res = interlink_note(cfg, caminho_nota, dry_run=dry_run)
    conns = res.get("connections", [])

    if not conns:
        console.print("[yellow]Nenhuma nova conexão semântica encontrada acima do limiar.[/yellow]")
        return

    console.print(f"[bold green]✓ {len(conns)} conexão(ões) identificada(s):[/bold green]")
    for c in conns:
        console.print(f"  • [[{c['target']}]] (sim: {c['similarity']}) -> [dim]{c['reason']}[/dim]")


if __name__ == "__main__":
    app()
