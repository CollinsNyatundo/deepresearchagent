"""Strategy B — Graphify MCP Bridge.

Starts and communicates with a Graphify MCP stdio server, exposing
knowledge graph queries to the research agent during and after runs.

The Graphify MCP server communicates over stdin/stdout using JSON-RPC 2.0.
We wrap this in an async bridge that the orchestrator and API layer can call.

Usage:
    server = await start_mcp_server(graph_path)
    result = await query_graph("what connects A to B?", server)
    await stop_mcp_server(server)
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from research_engine.models import KGQueryRequest, KGQueryResult

logger = logging.getLogger(__name__)

# Active MCP server process registry (run_id → process)
_active_servers: dict[str, asyncio.subprocess.Process] = {}


async def start_mcp_server(run_id: str, graph_json_path: Path) -> bool:
    """Start a Graphify MCP stdio server for a specific graph.

    The server reads requests from stdin and writes responses to stdout
    following the MCP protocol. We keep the process alive for the session.

    Args:
        run_id: Research run ID (used as registry key).
        graph_json_path: Absolute path to the graph.json file.

    Returns:
        True if server started successfully, False otherwise.
    """
    if run_id in _active_servers:
        logger.info(f"MCP server already running for run: {run_id}")
        return True

    if not graph_json_path.exists():
        logger.error(f"graph.json not found: {graph_json_path}")
        return False

    if not _graphify_available():
        logger.warning("graphify not installed — MCP bridge unavailable")
        return False

    import sys
    args = [
        sys.executable, "-m", "graphify",
        "--mcp",
        "--graph", str(graph_json_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _active_servers[run_id] = proc
        logger.info(f"Graphify MCP server started for run {run_id} (PID: {proc.pid})")
        return True

    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        return False


async def stop_mcp_server(run_id: str) -> None:
    """Stop the MCP server for a run."""
    proc = _active_servers.pop(run_id, None)
    if proc is None:
        return
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()
    except Exception as e:
        logger.warning(f"Error stopping MCP server for {run_id}: {e}")
    logger.info(f"Graphify MCP server stopped for run: {run_id}")


def get_server_status(run_id: str) -> dict:
    """Get the status of the MCP server for a run."""
    proc = _active_servers.get(run_id)
    if proc is None:
        return {"running": False, "run_id": run_id}
    return {
        "running": proc.returncode is None,
        "run_id": run_id,
        "pid": proc.pid,
    }


async def query_graph(
    run_id: str,
    request: KGQueryRequest,
) -> KGQueryResult:
    """Send a query to the Graphify MCP server and return the result.

    Sends a JSON-RPC request to the running MCP server process, parses
    the response, and returns a KGQueryResult.

    Falls back to a CLI-based query if the MCP server is unavailable.

    Args:
        run_id: Research run ID.
        request: Query request with question, mode, and token budget.

    Returns:
        KGQueryResult with answer, traversed nodes, and token cost.
    """
    proc = _active_servers.get(run_id)
    if proc is None or proc.returncode is not None:
        logger.warning(f"MCP server not running for run {run_id} — trying CLI fallback")
        return await _cli_query_fallback(run_id, request)

    # Build MCP JSON-RPC request per graphify's MCP protocol
    rpc_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "graphify_query",
            "arguments": {
                "question": request.question,
                "mode": request.mode,
                "budget": request.budget,
            },
        },
    }

    try:
        payload = (json.dumps(rpc_request) + "\n").encode()
        proc.stdin.write(payload)
        await proc.stdin.drain()

        # Read response line
        response_line = await asyncio.wait_for(
            proc.stdout.readline(),
            timeout=30,
        )
        response = json.loads(response_line.decode())

        if "error" in response:
            logger.error(f"MCP server error: {response['error']}")
            return KGQueryResult(
                answer=f"Graph query failed: {response['error'].get('message', 'unknown error')}",
                query_mode=request.mode,
            )

        result_data = response.get("result", {})
        # MCP tools/call response has content array
        content = result_data.get("content", [])
        answer_text = ""
        for block in content:
            if block.get("type") == "text":
                answer_text += block.get("text", "")

        # Try to parse structured JSON from the answer
        nodes_traversed: list[str] = []
        token_cost = 0
        try:
            parsed = json.loads(answer_text)
            if isinstance(parsed, dict):
                answer_text = parsed.get("answer", answer_text)
                nodes_traversed = parsed.get("nodes_traversed", [])
                token_cost = parsed.get("token_cost", 0)
        except (json.JSONDecodeError, TypeError):
            pass

        return KGQueryResult(
            answer=answer_text or "No answer returned from graph query.",
            nodes_traversed=nodes_traversed,
            token_cost=token_cost,
            query_mode=request.mode,
        )

    except asyncio.TimeoutError:
        logger.error("MCP server query timed out")
        return KGQueryResult(
            answer="Graph query timed out. Try a more specific question.",
            query_mode=request.mode,
        )
    except Exception as e:
        logger.error(f"MCP query error: {e}")
        return KGQueryResult(
            answer=f"Graph query error: {e}",
            query_mode=request.mode,
        )


async def _cli_query_fallback(run_id: str, request: KGQueryRequest) -> KGQueryResult:
    """Fallback: use graphify CLI to query a graph.json directly."""
    import sys
    from research_engine.output.storage import DEFAULT_OUTPUT_DIR

    graph_path = DEFAULT_OUTPUT_DIR / run_id / "knowledge_graph.json"
    if not graph_path.exists():
        return KGQueryResult(
            answer="Knowledge graph not found for this run. Build it first.",
            query_mode=request.mode,
        )

    args = [
        sys.executable, "-m", "graphify",
        "query", request.question,
        "--graph", str(graph_path),
        "--budget", str(request.budget),
    ]
    if request.mode == "dfs":
        args.append("--dfs")

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        answer = stdout.decode().strip()
        return KGQueryResult(
            answer=answer or "No answer from graph query.",
            query_mode=request.mode,
        )
    except Exception as e:
        return KGQueryResult(
            answer=f"CLI query error: {e}",
            query_mode=request.mode,
        )


def _graphify_available() -> bool:
    """Check if graphify is importable."""
    import importlib
    try:
        importlib.import_module("graphify")
        return True
    except ImportError:
        return False
