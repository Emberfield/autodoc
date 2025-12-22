#!/usr/bin/env python3
"""
MCP (Model Context Protocol) server for autodoc.

Exposes context pack tools for AI assistants to query and understand codebases.

Usage:
    # Run as MCP server
    python -m autodoc.mcp_server

    # Or via CLI
    autodoc mcp-server
"""

import json
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from .config import AutodocConfig

# Initialize FastMCP server
mcp = FastMCP(
    "autodoc",
    description="Code documentation and context pack tools for understanding codebases",
)


def get_config() -> AutodocConfig:
    """Load autodoc configuration."""
    return AutodocConfig.load()


@mcp.tool
def pack_list(
    tag: Optional[str] = None,
    security: Optional[str] = None,
) -> str:
    """List all configured context packs.

    Args:
        tag: Filter packs by tag (e.g., 'auth', 'security')
        security: Filter by security level ('critical', 'high', 'normal')

    Returns:
        JSON array of pack information
    """
    config = get_config()
    packs = config.context_packs

    if not packs:
        return json.dumps({"error": "No context packs configured", "packs": []})

    # Apply filters
    if tag:
        packs = [p for p in packs if tag in p.tags]
    if security:
        packs = [p for p in packs if p.security_level == security]

    result = []
    for p in packs:
        result.append({
            "name": p.name,
            "display_name": p.display_name,
            "description": p.description,
            "files_count": len(p.files),
            "tables": p.tables,
            "dependencies": p.dependencies,
            "security_level": p.security_level,
            "tags": p.tags,
        })

    return json.dumps({"packs": result, "total": len(result)})


@mcp.tool
def pack_info(
    name: str,
    include_dependencies: bool = False,
) -> str:
    """Get detailed information about a specific context pack.

    Args:
        name: The pack name (e.g., 'authentication', 'goals')
        include_dependencies: Include resolved dependency chain

    Returns:
        JSON object with pack details
    """
    config = get_config()
    pack = config.get_pack(name)

    if not pack:
        available = [p.name for p in config.context_packs]
        return json.dumps({
            "error": f"Pack '{name}' not found",
            "available_packs": available,
        })

    result = {
        "name": pack.name,
        "display_name": pack.display_name,
        "description": pack.description,
        "files": pack.files,
        "tables": pack.tables,
        "dependencies": pack.dependencies,
        "security_level": pack.security_level,
        "tags": pack.tags,
    }

    if include_dependencies:
        resolved = config.resolve_pack_dependencies(name)
        result["dependency_chain"] = [
            {"name": p.name, "display_name": p.display_name}
            for p in resolved if p.name != name
        ]

    # Check if pack has been built
    pack_file = Path(f".autodoc/packs/{name}.json")
    if pack_file.exists():
        with open(pack_file) as f:
            pack_data = json.load(f)
            result["built"] = True
            result["entity_count"] = len(pack_data.get("entities", []))
            result["has_embeddings"] = pack_data.get("has_embeddings", False)
            if pack_data.get("llm_summary"):
                result["llm_summary"] = pack_data["llm_summary"]
    else:
        result["built"] = False

    return json.dumps(result)


@mcp.tool
def pack_query(
    name: str,
    query: str,
    limit: int = 5,
) -> str:
    """Search within a context pack using semantic or keyword search.

    Args:
        name: The pack name to search within
        query: Search query (natural language or keywords)
        limit: Maximum number of results (default 5)

    Returns:
        JSON array of matching entities with scores
    """
    import asyncio

    config = get_config()
    pack = config.get_pack(name)

    if not pack:
        return json.dumps({"error": f"Pack '{name}' not found"})

    pack_file = Path(f".autodoc/packs/{name}.json")
    if not pack_file.exists():
        return json.dumps({
            "error": f"Pack '{name}' not built yet",
            "hint": f"Run: autodoc pack build {name}",
        })

    with open(pack_file) as f:
        pack_data = json.load(f)

    entities = pack_data.get("entities", [])
    if not entities:
        return json.dumps({"results": [], "search_type": "none", "message": "No entities in pack"})

    results = []
    search_type = "keyword"

    # Try semantic search if embeddings available
    if pack_data.get("has_embeddings", False):
        chromadb_dir = Path(f".autodoc/packs/{name}_chromadb")
        if chromadb_dir.exists():
            try:
                from .chromadb_embedder import ChromaDBEmbedder
                collection_name = f"autodoc_pack_{name}"

                embedder = ChromaDBEmbedder(
                    collection_name=collection_name,
                    persist_directory=str(chromadb_dir),
                    embedding_model=config.embeddings.chromadb_model,
                )

                search_results = asyncio.get_event_loop().run_until_complete(
                    embedder.search(query, limit=limit)
                )

                search_type = "semantic"
                for r in search_results:
                    results.append({
                        "type": r["entity"]["type"],
                        "name": r["entity"]["name"],
                        "file": r["entity"]["file_path"],
                        "line": r["entity"]["line_number"],
                        "score": round(r["similarity"], 3),
                        "preview": r.get("document", "")[:200],
                    })

            except Exception as e:
                # Fall back to keyword search
                search_type = "keyword"
                results = []

    # Keyword search fallback
    if not results:
        query_lower = query.lower()
        scored = []

        for entity in entities:
            score = 0
            name_str = entity.get("name", "").lower()
            desc = (entity.get("description") or "").lower()
            docstring = (entity.get("docstring") or "").lower()

            if query_lower in name_str:
                score += 10
            if query_lower in desc:
                score += 5
            if query_lower in docstring:
                score += 3

            for word in query_lower.split():
                if word in name_str:
                    score += 2
                if word in desc:
                    score += 1

            if score > 0:
                scored.append((entity, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        for entity, score in scored[:limit]:
            results.append({
                "type": entity.get("entity_type", "unknown"),
                "name": entity.get("name", "unknown"),
                "file": entity.get("file", ""),
                "line": entity.get("start_line", 0),
                "score": round(score / 20.0, 2),
                "preview": entity.get("docstring", "")[:200] if entity.get("docstring") else "",
            })

    return json.dumps({
        "query": query,
        "pack": name,
        "search_type": search_type,
        "results": results,
        "total": len(results),
    })


@mcp.tool
def pack_files(name: str) -> str:
    """Get the list of files in a context pack.

    Args:
        name: The pack name

    Returns:
        JSON array of file paths matching the pack's patterns
    """
    config = get_config()
    pack = config.get_pack(name)

    if not pack:
        return json.dumps({"error": f"Pack '{name}' not found"})

    # Check if pack has been built (has resolved files)
    pack_file = Path(f".autodoc/packs/{name}.json")
    if pack_file.exists():
        with open(pack_file) as f:
            pack_data = json.load(f)
            return json.dumps({
                "pack": name,
                "patterns": pack.files,
                "resolved_files": pack_data.get("files", []),
                "file_count": len(pack_data.get("files", [])),
            })

    # Return just the patterns if not built
    return json.dumps({
        "pack": name,
        "patterns": pack.files,
        "resolved_files": [],
        "hint": f"Run 'autodoc pack build {name}' to resolve file patterns",
    })


@mcp.tool
def pack_entities(
    name: str,
    entity_type: Optional[str] = None,
    limit: int = 50,
) -> str:
    """Get entities (functions, classes) from a context pack.

    Args:
        name: The pack name
        entity_type: Filter by type ('function', 'class', 'method')
        limit: Maximum entities to return (default 50)

    Returns:
        JSON array of code entities
    """
    pack_file = Path(f".autodoc/packs/{name}.json")
    if not pack_file.exists():
        return json.dumps({
            "error": f"Pack '{name}' not built",
            "hint": f"Run: autodoc pack build {name}",
        })

    with open(pack_file) as f:
        pack_data = json.load(f)

    entities = pack_data.get("entities", [])

    if entity_type:
        entities = [e for e in entities if e.get("entity_type") == entity_type]

    entities = entities[:limit]

    result = []
    for e in entities:
        result.append({
            "type": e.get("entity_type", "unknown"),
            "name": e.get("name", "unknown"),
            "file": e.get("file", ""),
            "line": e.get("start_line", 0),
            "docstring": e.get("docstring", "")[:200] if e.get("docstring") else None,
        })

    return json.dumps({
        "pack": name,
        "entity_type_filter": entity_type,
        "entities": result,
        "total": len(result),
        "limited": len(pack_data.get("entities", [])) > limit,
    })


@mcp.resource("autodoc://packs")
def list_all_packs() -> str:
    """Resource listing all available context packs."""
    config = get_config()
    packs = []
    for p in config.context_packs:
        packs.append({
            "name": p.name,
            "display_name": p.display_name,
            "description": p.description,
        })
    return json.dumps(packs)


@mcp.resource("autodoc://packs/{name}")
def get_pack_resource(name: str) -> str:
    """Resource for a specific context pack."""
    return pack_info(name, include_dependencies=True)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
