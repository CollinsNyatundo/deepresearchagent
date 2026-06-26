import asyncio
import subprocess
from pathlib import Path

OPENKB_BASE_DIR = Path("openkb")


def get_workspace_kb_dir(workspace_id: str) -> Path:
    return OPENKB_BASE_DIR / workspace_id


async def ensure_kb_initialized(workspace_id: str) -> Path:
    """Ensure OpenKB is initialized for workspace."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    config_path = kb_dir / ".openkb" / "config.yaml"
    if not config_path.exists():
        kb_dir.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            "openkb", "init",
            cwd=kb_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(input=b"\n\n\n")
        if proc.returncode != 0:
            raise RuntimeError(f"OpenKB init failed: {stderr.decode()}")
    return kb_dir


async def run_openkb_command(workspace_id: str, *args) -> str:
    """Run an OpenKB command in workspace context."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    await ensure_kb_initialized(workspace_id)
    proc = await asyncio.create_subprocess_exec(
        "openkb", *args,
        cwd=kb_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"OpenKB failed: {stderr.decode()}")
    return stdout.decode()


async def add_document(workspace_id: str, file_path: Path) -> str:
    """Add a document to the OpenKB wiki."""
    await ensure_kb_initialized(workspace_id)
    return await run_openkb_command(workspace_id, "add", str(file_path))


async def list_documents(workspace_id: str) -> str:
    """List all documents in the OpenKB wiki."""
    return await run_openkb_command(workspace_id, "list")


async def query_wiki(workspace_id: str, question: str) -> str:
    """Query the OpenKB wiki for a specific question."""
    return await run_openkb_command(workspace_id, "query", question)


async def get_kb_status(workspace_id: str) -> str:
    """Get OpenKB status for workspace."""
    return await run_openkb_command(workspace_id, "status")


async def create_skill(workspace_id: str, name: str, intent: str) -> str:
    """Distill a skill from the OpenKB wiki."""
    return await run_openkb_command(workspace_id, "skill", "new", name, intent)


async def list_skills(workspace_id: str) -> str:
    """List all generated skills in workspace."""
    skills_dir = get_workspace_kb_dir(workspace_id) / "output" / "skills"
    if not skills_dir.exists():
        return ""
    return "\n".join([p.name for p in skills_dir.iterdir() if p.is_dir()])


async def remove_document(workspace_id: str, doc_name: str) -> str:
    """Remove a document from the OpenKB wiki."""
    return await run_openkb_command(workspace_id, "remove", doc_name)


async def recompile_documents(workspace_id: str) -> str:
    """Re-run compile pipeline on all indexed documents."""
    return await run_openkb_command(workspace_id, "recompile", "--all")


async def get_document_path(workspace_id: str, doc_name: str) -> Path:
    """Get the file path of a raw document."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    raw_dir = kb_dir / "raw"
    file_path = raw_dir / doc_name
    if not file_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_name}")
    return file_path


async def get_kb_stats(workspace_id: str) -> dict:
    """Get detailed OpenKB stats for workspace."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    wiki_dir = kb_dir / "wiki"
    raw_dir = kb_dir / "raw"

    stats = {
        "document_count": 0,
        "concept_count": 0,
        "entity_count": 0,
        "summary_count": 0,
        "wiki_size_bytes": 0,
    }

    if raw_dir.exists():
        stats["document_count"] = len(list(raw_dir.iterdir()))

    if wiki_dir.exists():
        for item in wiki_dir.rglob("*.md"):
            stats["wiki_size_bytes"] += item.stat().st_size
            rel = item.relative_to(wiki_dir).as_posix()
            if rel.startswith("concepts/"):
                stats["concept_count"] += 1
            elif rel.startswith("entities/"):
                stats["entity_count"] += 1
            elif rel.startswith("summaries/"):
                stats["summary_count"] += 1

    return stats

async def get_wiki_page(workspace_id: str, page_path: str) -> str:
    """Get a specific wiki page as Markdown."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    wiki_dir = kb_dir / "wiki"
    file_path = wiki_dir / page_path
    if not file_path.exists():
        raise FileNotFoundError(f"Wiki page not found: {page_path}")
    return file_path.read_text(encoding="utf-8")


async def validate_skill(workspace_id: str, name: str) -> dict:
    """Validate a skill's schema and structure."""
    skills_dir = get_workspace_kb_dir(workspace_id) / "output" / "skills" / name
    if not skills_dir.exists():
        return {"valid": False, "error": f"Skill '{name}' not found"}

    required = ["skill.yaml", "prompt.md"]
    missing = [f for f in required if not (skills_dir / f).exists()]

    if missing:
        return {"valid": False, "error": f"Missing files: {', '.join(missing)}"}

    return {
        "valid": True,
        "files": [f.name for f in skills_dir.iterdir() if f.is_file()],
        "skill_name": name,
    }


async def evaluate_skill(workspace_id: str, name: str) -> dict:
    """Evaluate a skill's coverage against wiki concepts."""
    skills_dir = get_workspace_kb_dir(workspace_id) / "output" / "skills" / name
    wiki_dir = get_workspace_kb_dir(workspace_id) / "wiki"

    if not skills_dir.exists():
        return {"coverage": 0, "error": f"Skill '{name}' not found"}

    total_concepts = 0
    concepts_dir = wiki_dir / "concepts"
    if concepts_dir.exists():
        total_concepts = len(list(concepts_dir.rglob("*.md")))

    skill_text = ""
    for f in skills_dir.iterdir():
        if f.is_file():
            try:
                skill_text += f.read_text(encoding="utf-8")
            except Exception:
                pass

    matched = 0
    if total_concepts > 0 and concepts_dir.exists():
        for concept_file in concepts_dir.rglob("*.md"):
            concept_name = concept_file.stem.replace("-", " ").replace("_", " ")
            if concept_name.lower() in skill_text.lower():
                matched += 1

    coverage = (matched / total_concepts * 100) if total_concepts > 0 else 0
    return {
        "coverage": round(coverage, 1),
        "concepts_matched": matched,
        "total_concepts": total_concepts,
        "skill_name": name,
    }


async def rollback_skill(workspace_id: str, name: str) -> dict:
    """Rollback a skill to previous version."""
    skills_dir = get_workspace_kb_dir(workspace_id) / "output" / "skills" / name
    backup_dir = skills_dir.parent / f"{name}.backup"

    if not skills_dir.exists():
        return {"success": False, "error": f"Skill '{name}' not found"}

    if not backup_dir.exists():
        return {"success": False, "error": "No backup version available"}

    temp_dir = skills_dir.parent / f"{name}.temp"
    skills_dir.rename(temp_dir)
    backup_dir.rename(skills_dir)
    temp_dir.rename(backup_dir)

    return {"success": True, "message": f"Rolled back skill '{name}' to previous version"}


async def list_wiki_pages(workspace_id: str) -> list[dict]:
    """List all wiki pages in the workspace."""
    kb_dir = get_workspace_kb_dir(workspace_id)
    wiki_dir = kb_dir / "wiki"
    if not wiki_dir.exists():
        return []

    pages = []
    for item in wiki_dir.rglob("*.md"):
        rel = item.relative_to(wiki_dir).as_posix()
        pages.append({
            "path": rel,
            "title": item.stem.replace("-", " ").replace("_", " ").title(),
            "type": _infer_page_type(rel),
        })
    return sorted(pages, key=lambda p: p["path"])


def _infer_page_type(path: str) -> str:
    """Infer wiki page type from path."""
    if path.startswith("concepts/"):
        return "concept"
    elif path.startswith("entities/"):
        return "entity"
    elif path.startswith("summaries/"):
        return "summary"
    elif path.startswith("explorations/"):
        return "exploration"
    elif path == "index.md":
        return "index"
    elif path == "log.md":
        return "log"
    elif path == "AGENTS.md":
        return "agents"
    else:
        return "page"
