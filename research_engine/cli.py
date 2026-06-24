"""CLI entrypoint — Typer-based command-line interface for Deep Research Agent."""

from __future__ import annotations

import os
import subprocess
import sys

def _ensure_venv() -> None:
    """Ensure the CLI runs using the project's virtual environment if present."""
    cwd = os.getcwd()
    venv_dir = os.path.join(cwd, ".venv")
    
    if os.path.isdir(venv_dir):
        if sys.platform == "win32":
            venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_dir, "bin", "python")
            
        if os.path.exists(venv_python):
            real_current_py = os.path.normpath(sys.executable).lower()
            real_venv_py = os.path.normpath(venv_python).lower()
            
            if real_current_py != real_venv_py:
                if sys.argv:
                    script_name = os.path.basename(sys.argv[0]).lower()
                    is_cli_run = "research" in script_name or "cli.py" in script_name
                    
                    if is_cli_run:
                        real_venv_dir = os.path.normpath(venv_dir).lower()
                        if not real_current_py.startswith(real_venv_dir + os.sep):
                            try:
                                result = subprocess.run([venv_python, "-m", "research_engine.cli"] + sys.argv[1:])
                                sys.exit(result.returncode)
                            except KeyboardInterrupt:
                                sys.exit(130)
                            except Exception as e:
                                print(f"Error executing virtual environment python: {e}", file=sys.stderr)
                                sys.exit(1)

_ensure_venv()

import asyncio
import logging

import typer
from rich.console import Console
from rich.logging import RichHandler

from research_engine.config import get_config

app = typer.Typer(
    name="research",
    help="Deep Research Agent — exhaustive, citation-backed web research.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


@app.command()
def run(
    query: str = typer.Argument(..., help="The research query/topic"),
    model: str | None = typer.Option(
        None, "--model", "-m",
        help="OpenRouter model ID (e.g. nvidia/nemotron-3-super-120b-a12b:free)",
    ),
    depth: int = typer.Option(
        5, "--depth", "-d",
        help="Research depth 1-5 (1=quick, 3=standard, 5=exhaustive)",
        min=1, max=5,
    ),
    search_provider: str | None = typer.Option(
        None, "--search", "-s",
        help="Search provider: duckduckgo, tavily, brave",
    ),
    provider: str | None = typer.Option(
        None, "--provider", "-pr",
        help="LLM provider: openrouter, groq",
    ),
    max_pages: int = typer.Option(
        5, "--max-pages", "-p",
        help="Max pages to scrape per search query",
        min=1, max=20,
    ),
    no_crossover: bool = typer.Option(
        False, "--no-crossover",
        help="Disable candidate crossover (faster, less thorough)",
    ),
    mode: str = typer.Option(
        "web", "--mode",
        help="Research mode: 'web' or 'github'",
    ),
    config_path: str | None = typer.Option(
        None, "--config", "-c",
        help="Path to config.toml file",
    ),
    output_dir: str = typer.Option(
        "outputs", "--output", "-o",
        help="Output directory for research results",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose/debug logging",
    ),
) -> None:
    """Run a deep research query and generate a report + mindmap."""
    _setup_logging(verbose)

    from research_engine.models import ResearchMode, ResearchRequest

    request = ResearchRequest(
        query=query,
        model=model,
        depth=depth,
        max_pages=max_pages,
        enable_crossover=not no_crossover,
        search_provider=search_provider,
        provider=provider,
        mode=ResearchMode(mode) if mode else ResearchMode.WEB,
    )

    asyncio.run(_execute_research(request, config_path, output_dir))


async def _execute_research(
    request,
    config_path: str | None,
    output_dir: str,
) -> None:
    """Execute the research run asynchronously."""
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file

    config = get_config(config_path)

    from research_engine.agent.orchestrator import DeepResearchOrchestrator

    orchestrator = DeepResearchOrchestrator(config)

    try:
        result = await orchestrator.run(request)
        console.print(f"\n[bold green]Report saved to: outputs/{result.run_id}/report.md[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]Research failed: {e}[/bold red]")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            raise
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="API server host"),
    port: int = typer.Option(8000, "--port", "-p", help="API server port"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Start the FastAPI server for the frontend."""
    from dotenv import load_dotenv
    import uvicorn

    # Load .env BEFORE importing or starting anything — this populates
    # DEV_AUTH_BYPASS, SUPABASE_JWT_SECRET, DATABASE_URL, etc.
    load_dotenv()

    _setup_logging()

    console.print("\n[bold blue]🚀 Starting Deep Research API[/bold blue]")
    console.print(f"   http://{host}:{port}")
    console.print(f"   Docs: http://{host}:{port}/docs\n")

    uvicorn.run(
        "research_engine.api:app",
        host=host,
        port=port,
        reload=reload,
    )



@app.command()
def list_runs(
    output_dir: str = typer.Option("outputs", "--output", "-o", help="Output directory"),
) -> None:
    """List all past research runs."""
    from research_engine.output.storage import list_runs as _list_runs

    runs = _list_runs(output_dir)
    if not runs:
        console.print("[dim]No research runs found.[/dim]")
        return

    console.print(f"\n[bold]Research Runs ({len(runs)}):[/bold]\n")
    for run in runs:
        console.print(
            f"  [cyan]{run.id}[/cyan]  "
            f"[white]{run.query}[/white]  "
            f"[dim]{run.created_at}[/dim]  "
            f"[dim]{run.model_used}[/dim]"
        )


@app.command()
def gitnexus_bridge(
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Force rebuild even if a cached graph exists",
    ),
    eval_server_port: int = typer.Option(
        4848, "--port", "-p",
        help="GitNexus eval-server port",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Rebuild the GitNexus codebase architecture graph.

    Runs npx gitnexus analyze then queries the eval-server to build
    outputs/gitnexus_graph.json which the frontend serves as the
    Code Architecture view.

    The eval-server must be running:
        npx gitnexus eval-server --port 4848
    """
    _setup_logging(verbose)
    asyncio.run(_run_gitnexus_bridge(force, eval_server_port))


async def _run_gitnexus_bridge(force: bool, port: int) -> None:
    from research_engine.knowledge_graph.gitnexus_bridge import (
        GRAPH_OUTPUT_PATH,
        build_and_save,
        is_eval_server_running,
    )

    if GRAPH_OUTPUT_PATH.exists() and not force:
        console.print(
            f"[yellow]Cache exists at {GRAPH_OUTPUT_PATH}.[/yellow] "
            "Use --force to rebuild."
        )
        return

    if not await is_eval_server_running():
        console.print(
            "[red]GitNexus eval-server not running.[/red]\n"
            f"Start it first:\n  [bold]npx gitnexus eval-server --port {port}[/bold]"
        )
        raise typer.Exit(code=1)

    console.print("[blue]Running npx gitnexus analyze…[/blue]")
    proc = await asyncio.create_subprocess_exec(
        "npx", "gitnexus", "analyze",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
    if proc.returncode != 0:
        console.print(f"[red]analyze failed:[/red] {stderr.decode(errors='replace')[:300]}")
        raise typer.Exit(code=1)

    console.print("[blue]Building gitnexus_graph.json…[/blue]")
    path = await build_and_save()
    console.print(f"[bold green]✅  Graph saved to {path}[/bold green]")


@app.command()
def gitnexus_wiki(
    gist: bool = typer.Option(
        False, "--gist",
        help="Publish to a public GitHub Gist (requires gh CLI authenticated)",
    ),
    output: str | None = typer.Option(
        None, "--output", "-o",
        help="Save wiki to this local directory instead of .gitnexus/wiki/",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
) -> None:
    """Generate an architecture wiki from the GitNexus knowledge graph.

    Reads the .gitnexus graph and writes comprehensive, human-readable
    architecture documentation covering clusters, processes, and key files.

    Pass --gist to also publish to a public GitHub Gist so you can read it
    beautifully in the browser.
    """
    _setup_logging(verbose)
    asyncio.run(_run_gitnexus_wiki(gist, output))


async def _run_gitnexus_wiki(gist: bool, output: str | None) -> None:
    args = ["npx", "gitnexus", "wiki"]
    if output:
        args += [output]
    if gist:
        args += ["--gist"]

    console.print("[blue]Generating GitNexus architecture wiki…[/blue]")
    console.print(f"  Command: [dim]{' '.join(args)}[/dim]")

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

    if proc.returncode != 0:
        console.print(f"[red]wiki generation failed:[/red] {stderr.decode(errors='replace')[:500]}")
        raise typer.Exit(code=1)

    output_text = stdout.decode(errors="replace")
    console.print(output_text)

    if gist and "https://" in output_text:
        import re
        urls = re.findall(r"https://[^\s]+", output_text)
        if urls:
            console.print("\n[bold green]📚 Wiki published! Open in browser:[/bold green]")
            for url in urls:
                console.print(f"  [link={url}]{url}[/link]")
    else:
        console.print("[bold green]📚 Wiki generated in .gitnexus/wiki/[/bold green]")


@app.command()
def setup_shims() -> None:
    """Setup Windows/WSL path shims/wrappers for GitNexus and ast-grep.

    Creates Windows .cmd shims in %USERPROFILE%/.bin (delegating to WSL)
    or WSL bash wrappers in ~/.local/bin (delegating to Windows) to enable
    seamless mixed-environment execution.
    """
    from research_engine.setup_shims import setup_shims as run_setup

    console.print("[blue]Setting up shims/wrappers for GitNexus and ast-grep...[/blue]")
    try:
        created, message = run_setup()
        for path in created:
            console.print(f"  [green]*[/green] Created: {path}")
        console.print(f"\n[bold green]OK: {message}[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]Failed to setup shims: {e}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
