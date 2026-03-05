"""
MCP server for Document Processor.

Exposes semantic search and document management as tools that any
MCP-compatible client (e.g. Claude Desktop) can call.

Usage:
  python mcp_server.py

Claude Desktop config (~/.claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "document-processor": {
        "command": "python",
        "args": ["/absolute/path/to/mcp_server.py"],
        "env": { "DOC_PROCESSOR_URL": "http://localhost:8000" }
      }
    }
  }
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("DOC_PROCESSOR_URL", "http://localhost:8000")

mcp = FastMCP("Document Processor")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _http() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)


def _fmt_score(score: float) -> str:
    return f"{score * 100:.1f}%"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_documents(query: str, limit: int = 10) -> str:
    """
    Semantically search all indexed documents.

    Returns ranked results with filename, page number, relevance score,
    and a content snippet. Scores above 80% indicate strong relevance.

    Args:
        query: Natural-language search query.
        limit: Maximum number of results to return (default 10).
    """
    async with _http() as client:
        res = await client.post("/api/v1/search", json={"query": query, "limit": limit})
        res.raise_for_status()
        data = res.json()

    results = data["results"]
    if not results:
        return f"No results found for: '{query}'"

    lines = [f"Found {len(results)} result(s) for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        page = f"p{r['page']}" if r.get("page") else "—"
        lines.append(
            f"{i}. [{r['filename']}] {page}  score={_fmt_score(r['score'])}  type={r['result_type']}"
        )
        snippet = (r["content"] or "")[:400].replace("\n", " ")
        lines.append(f"   {snippet}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def list_documents() -> str:
    """
    List all documents that have been uploaded and indexed.

    Returns filename, status (pending/processing/ready/error),
    chunk count, and document ID for each document.
    """
    async with _http() as client:
        res = await client.get("/api/v1/documents")
        res.raise_for_status()
        data = res.json()

    docs = data["documents"]
    if not docs:
        return "No documents indexed yet."

    lines = [f"Total: {data['total']} document(s)\n"]
    for d in docs:
        status_icon = {"ready": "✓", "processing": "…", "error": "✗", "pending": "○"}.get(
            d["status"], "?"
        )
        lines.append(
            f"{status_icon} {d['filename']}  [{d['status']}]  "
            f"{d['chunk_count']} chunks  id={d['id']}"
        )
        if d.get("error_message"):
            lines.append(f"  Error: {d['error_message']}")

    return "\n".join(lines)


@mcp.tool()
async def get_document(doc_id: str) -> str:
    """
    Get detailed information about a specific document.

    Args:
        doc_id: The document ID (from list_documents).
    """
    async with _http() as client:
        res = await client.get(f"/api/v1/documents/{doc_id}")
        if res.status_code == 404:
            return f"Document not found: {doc_id}"
        res.raise_for_status()
        d = res.json()

    return (
        f"ID:         {d['id']}\n"
        f"Filename:   {d['filename']}\n"
        f"Type:       {d['file_type'].upper()}\n"
        f"Status:     {d['status']}\n"
        f"Chunks:     {d['chunk_count']}\n"
        f"Created:    {d['created_at']}\n"
        f"Updated:    {d['updated_at']}\n"
        + (f"Error:      {d['error_message']}\n" if d.get("error_message") else "")
    )


@mcp.tool()
async def delete_document(doc_id: str) -> str:
    """
    Delete a document and all its indexed vector data.

    Args:
        doc_id: The document ID to delete (from list_documents).
    """
    async with _http() as client:
        res = await client.delete(f"/api/v1/documents/{doc_id}")
        if res.status_code == 404:
            return f"Document not found: {doc_id}"
        res.raise_for_status()

    return f"Deleted document {doc_id} and all associated vector data."


@mcp.tool()
async def health_check() -> str:
    """Check whether the Document Processor API is running."""
    async with _http() as client:
        try:
            res = await client.get("/api/v1/health")
            res.raise_for_status()
            d = res.json()
            return f"API is running. Status: {d['status']}, Version: {d['version']}"
        except Exception as e:
            return f"API unreachable at {BASE_URL}: {e}"


if __name__ == "__main__":
    mcp.run()
