"""GitHub MCP integration for Code Research.

Connects to @modelcontextprotocol/server-github via the mcp SDK.
Provides standard SearchProvider and scraper-like interfaces.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from research_engine.config import GithubConfig, get_config
from research_engine.models import ScrapedPage, SearchResult

logger = logging.getLogger(__name__)


class GitHubMCPClient:
    """Singleton wrapper for the GitHub MCP stdout client session.
    
    Since spinning up an entirely new Node process via npx is expensive,
    this class maintains long-lived session context where possible, 
    or simplifies reconnects.
    """

    def __init__(self, config: GithubConfig | None = None):
        self.config = config or get_config().github
        self.personal_access_token = self.config.personal_access_token or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
        self.npx_path = shutil.which("npx")
        
        if not self.npx_path:
            logger.warning("Could not find 'npx' in PATH. GitHub MCP might fail.")
            
    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Executes a tool on the GitHub MCP server and returns the string result."""
        if not self.npx_path:
            return "Error: npx not found in PATH."
            
        env = os.environ.copy()
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self.personal_access_token
        
        server_params = StdioServerParameters(
            command=self.npx_path,
            args=["-y", "@modelcontextprotocol/server-github"],
            env=env
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    
                    if not result.content:
                        return ""
                    
                    # Usually MCP returns text content blocks
                    outputs = []
                    for content in result.content:
                        if content.type == "text":
                            outputs.append(content.text)
                    
                    return "\n".join(outputs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"GitHub MCP Tool execution failed: {e}")
            return f"Error executing {name}: {e}"


class GitHubSearchProvider:
    """Search provider utilizing the GitHub MCP server search_code tool."""
    
    def __init__(self, client: GitHubMCPClient | None = None):
        self.client = client or GitHubMCPClient()
        self.default_repo = get_config().github.default_repo

    async def search(self, query: str, max_results: int = 10, repo: str | None = None) -> list[SearchResult]:
        """Searches GitHub code using the MCP search_code tool.
        
        Query must use GitHub search syntax (e.g. 'repo:org/repo keyword').
        """
        target_repo = repo or self.default_repo
        
        # If the query doesn't explicitly scope to a repo, augment it
        # Actually, GitHub search allows repo: prefix in the query itself.
        search_query = query
        if "repo:" not in search_query:
            search_query = f"repo:{target_repo} {query}"
            
        logger.info(f"Running GitHub MCP Code Search: {search_query}")
        
        # search_code requires `q` as parameter based on MCP server spec
        result_text = await self.client._execute_tool("search_code", {"q": search_query})
        
        # The result string usually contains file paths and matches in plaintext or json
        # We'll create generic SearchResults pointing to the file paths.
        # Since we're parsing string output directly, we'll try to extract file paths.
        # Usually, GitHub native response contains lines like `path/to/file.py`.
        
        results: list[SearchResult] = []
        
        # This is a bit heuristic depending on what exactly server-github outputs.
        # Often it outputs the raw JSON from GitHub's REST API or formatted text.
        # Let's encapsulate the entire matching text as one conceptual result, 
        # or we attempt to parse lines.
        
        # For simplicity, we can return the raw result as one "mega" search result 
        # where the URL is a special pointer, or if we want to fetch specific files, 
        # we return the raw match and rely on the Planner to ask for specific files next.
        
        # Let's extract words that look like file paths inside the target repo.
        import re
        paths = set()
        for word in result_text.split():
            # Very naive file extraction from text blob
            # If word contains a slash and an extension like .py, .ts, .md
            if "/" in word and re.search(r'\.[a-zA-Z0-9]+$', word):
                paths.add(word.strip('",\'[]{}()'))
                
        if not paths and result_text and not result_text.startswith("Error"):
            # fallback: just return the raw payload as a single snippet
            results.append(SearchResult(
                url=f"github://{target_repo}/search?q={query}",
                title="GitHub Code Search Results",
                snippet=result_text[:5000]
            ))
            return results

        for path in list(paths)[:max_results]:
            results.append(SearchResult(
                url=f"github://{target_repo}/{path}",
                title=path,
                snippet=f"Found match in {path}. Use get_file_contents to read."
            ))
            
        return results


class GitHubScraper:
    """Scrapes code files via GitHub MCP get_file_contents."""
    
    def __init__(self, client: GitHubMCPClient | None = None):
        self.client = client or GitHubMCPClient()
        self.default_repo = get_config().github.default_repo
        
    async def fetch_page(self, url: str) -> ScrapedPage:
        # url format: github://CollinsNyatundo/Ulti-IDE/path/to/file.py
        if not url.startswith("github://"):
            return ScrapedPage(url=url, success=False, error="Invalid github URL")
            
        parts = url.replace("github://", "").split("/")
        # e.g. CollinsNyatundo / Ulti-IDE / path / to / file.py
        if len(parts) < 3:
            return ScrapedPage(url=url, success=False, error="URL does not contain owner/repo/path")
            
        owner = parts[0]
        repo = parts[1]
        path = "/".join(parts[2:])
        
        if "?" in path:  # it's a search fallback url
            return ScrapedPage(url=url, success=False, error="Cannot fetch search root as file")
            
        logger.info(f"Fetching GitHub file: {owner}/{repo}/{path}")
        
        content = await self.client._execute_tool("get_file_contents", {
            "owner": owner,
            "repo": repo,
            "path": path
        })
        
        success = not content.startswith("Error")
        return ScrapedPage(
            url=url,
            title=path,
            content=content,
            content_length=len(content),
            success=success,
            error=content if not success else None,
            status_code=200 if success else 500,
            fetcher_used="github_mcp"
        )
        
    async def fetch_pages(self, urls: list[str]) -> list[ScrapedPage]:
        import asyncio
        tasks = [self.fetch_page(url) for url in urls]
        return await asyncio.gather(*tasks)
