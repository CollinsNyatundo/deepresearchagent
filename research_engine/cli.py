"""CLI entrypoint — Typer-based command-line interface for Deep Research Agent."""

from __future__ import annotations

import asyncio
import logging
import sys

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

    from research_engine.models import ResearchRequest, ResearchMode

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
    import uvicorn

    _setup_logging()

    console.print(f"\n[bold blue]🚀 Starting Deep Research API[/bold blue]")
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


if __name__ == "__main__":
    app()
