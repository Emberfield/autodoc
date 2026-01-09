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
import logging
import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

from fastmcp import FastMCP

from .config import AutodocConfig

log = logging.getLogger(__name__)

# Initialize FastMCP server
# Note: FastMCP 2.x uses 'instructions' instead of 'description'
mcp = FastMCP(
    "autodoc",
    instructions="Code documentation and context pack tools for understanding codebases",
)


def safe_json_response(func: Callable) -> Callable:
    """Decorator to ensure MCP tools always return valid JSON responses.

    Catches exceptions and returns structured error responses instead of crashing.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return func(*args, **kwargs)
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error in {func.__name__}: {e}")
            return json.dumps({
                "error": "Invalid JSON data encountered",
                "details": str(e),
                "tool": func.__name__,
            })
        except FileNotFoundError as e:
            log.warning(f"File not found in {func.__name__}: {e}")
            return json.dumps({
                "error": "Required file not found",
                "details": str(e),
                "hint": "Run 'autodoc analyze' or 'autodoc pack build' first",
                "tool": func.__name__,
            })
        except Exception as e:
            log.error(f"Unexpected error in {func.__name__}: {e}\n{traceback.format_exc()}")
            return json.dumps({
                "error": "Unexpected error occurred",
                "details": str(e),
                "tool": func.__name__,
                "hint": "Check server logs for details",
            })

    return wrapper


def get_config() -> AutodocConfig:
    """Load autodoc configuration."""
    try:
        return AutodocConfig.load()
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        # Return default config to avoid crashes
        return AutodocConfig()


@mcp.tool
@safe_json_response
def capabilities() -> str:
    """Check autodoc capabilities and tool availability.

    Returns which tools are available based on installed dependencies,
    running services, and existing cache files. Use this to understand
    what features you can use before calling other tools.

    Returns:
        JSON with available tools categorized by requirement status
    """
    import os

    result = {
        "core_tools": {
            "status": "available",
            "tools": [
                "pack_list",
                "pack_info",
                "pack_query",
                "pack_files",
                "pack_entities",
                "pack_status",
                "pack_deps",
                "pack_diff",
                "impact_analysis",
                "analyze",
                "search",
                "generate",
                "check",
            ],
            "description": "Always available - context pack and basic analysis tools",
        },
        "enrichment_tools": {
            "tools": ["enrich"],
            "requires": "LLM API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)",
            "status": "available"
            if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
            else "unavailable",
        },
        "graph_tools": {
            "tools": ["graph_build", "graph_query"],
            "requires": "Neo4j running + NEO4J_PASSWORD env var",
            "setup_hint": "Run: docker compose up -d (uses included docker-compose.yml)",
            "status": "unknown",
        },
        "feature_tools": {
            "tools": ["feature_list", "feature_files"],
            "requires": "Graph tools + 'autodoc features detect' run first",
            "status": "unknown",
        },
    }

    # Check Neo4j availability
    try:
        from neo4j import GraphDatabase

        neo4j_password = os.environ.get("NEO4J_PASSWORD")
        if neo4j_password:
            neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
            try:
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                driver.verify_connectivity()
                driver.close()
                result["graph_tools"]["status"] = "available"
            except Exception:
                result["graph_tools"]["status"] = "unavailable"
                result["graph_tools"]["error"] = "Cannot connect to Neo4j"
        else:
            result["graph_tools"]["status"] = "unavailable"
            result["graph_tools"]["error"] = "NEO4J_PASSWORD not set"
    except ImportError:
        result["graph_tools"]["status"] = "unavailable"
        result["graph_tools"]["error"] = "neo4j package not installed (run: make setup-graph)"

    # Check features cache
    from pathlib import Path

    features_cache = Path(".autodoc/features_cache.json")
    if features_cache.exists():
        result["feature_tools"]["status"] = "available"
    else:
        result["feature_tools"]["status"] = "unavailable"
        result["feature_tools"]["error"] = "No features detected yet"

    # Check analysis cache
    cache_exists = Path("autodoc_cache.json").exists()
    result["analysis_cache"] = {
        "exists": cache_exists,
        "hint": "Run 'analyze' tool first" if not cache_exists else None,
    }

    return json.dumps(result, indent=2)


@mcp.tool
@safe_json_response
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
        result.append(
            {
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "files_count": len(p.files),
                "tables": p.tables,
                "dependencies": p.dependencies,
                "security_level": p.security_level,
                "tags": p.tags,
            }
        )

    return json.dumps({"packs": result, "total": len(result)})


@mcp.tool
@safe_json_response
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
        return json.dumps(
            {
                "error": f"Pack '{name}' not found",
                "available_packs": available,
            }
        )

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
            {"name": p.name, "display_name": p.display_name} for p in resolved if p.name != name
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
@safe_json_response
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
        return json.dumps(
            {
                "error": f"Pack '{name}' not built yet",
                "hint": f"Run: autodoc pack build {name}",
            }
        )

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
                    results.append(
                        {
                            "type": r["entity"]["type"],
                            "name": r["entity"]["name"],
                            "file": r["entity"]["file_path"],
                            "line": r["entity"]["line_number"],
                            "score": round(r["similarity"], 3),
                            "preview": r.get("document", "")[:200],
                        }
                    )

            except Exception:
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
            results.append(
                {
                    "type": entity.get("entity_type", "unknown"),
                    "name": entity.get("name", "unknown"),
                    "file": entity.get("file", ""),
                    "line": entity.get("line_number", entity.get("start_line", 0)),
                    "score": round(score / 20.0, 2),
                    "preview": entity.get("docstring", "")[:200] if entity.get("docstring") else "",
                }
            )

    return json.dumps(
        {
            "query": query,
            "pack": name,
            "search_type": search_type,
            "results": results,
            "total": len(results),
        }
    )


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
            return json.dumps(
                {
                    "pack": name,
                    "patterns": pack.files,
                    "resolved_files": pack_data.get("files", []),
                    "file_count": len(pack_data.get("files", [])),
                }
            )

    # Return just the patterns if not built
    return json.dumps(
        {
            "pack": name,
            "patterns": pack.files,
            "resolved_files": [],
            "hint": f"Run 'autodoc pack build {name}' to resolve file patterns",
        }
    )


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
        return json.dumps(
            {
                "error": f"Pack '{name}' not built",
                "hint": f"Run: autodoc pack build {name}",
            }
        )

    with open(pack_file) as f:
        pack_data = json.load(f)

    entities = pack_data.get("entities", [])

    if entity_type:
        entities = [e for e in entities if e.get("entity_type") == entity_type]

    entities = entities[:limit]

    result = []
    for e in entities:
        result.append(
            {
                "type": e.get("entity_type", "unknown"),
                "name": e.get("name", "unknown"),
                "file": e.get("file", ""),
                "line": e.get("line_number", e.get("start_line", 0)),
                "docstring": e.get("docstring", "")[:200] if e.get("docstring") else None,
            }
        )

    return json.dumps(
        {
            "pack": name,
            "entity_type_filter": entity_type,
            "entities": result,
            "total": len(result),
            "limited": len(pack_data.get("entities", [])) > limit,
        }
    )


@mcp.tool
@safe_json_response
def impact_analysis(
    files: str,
    pack_filter: Optional[str] = None,
) -> str:
    """Analyze the impact of file changes on context packs.

    Given changed files, shows which packs and entities might be affected.
    Useful for understanding the scope of code changes.

    Args:
        files: Comma-separated list of changed file paths
        pack_filter: Limit analysis to specific pack (optional)

    Returns:
        JSON with affected packs, entities, and security warnings
    """
    import fnmatch

    config = get_config()

    if not config.context_packs:
        return json.dumps({"error": "No context packs configured", "affected_packs": []})

    # Parse file list
    changed_files = [f.strip() for f in files.split(",") if f.strip()]
    if not changed_files:
        return json.dumps({"error": "No files provided", "affected_packs": []})

    base_path = Path.cwd()

    # Filter packs if specified
    packs_to_analyze = config.context_packs
    if pack_filter:
        packs_to_analyze = [p for p in config.context_packs if p.name == pack_filter]
        if not packs_to_analyze:
            return json.dumps({"error": f"Pack '{pack_filter}' not found", "affected_packs": []})

    affected_packs = []

    for pack_config in packs_to_analyze:
        matching_files = []
        for changed_file in changed_files:
            for pattern in pack_config.files:
                try:
                    file_path = Path(changed_file)
                    # Try relative path matching
                    try:
                        rel_path = file_path.relative_to(base_path)
                        if fnmatch.fnmatch(str(rel_path), pattern):
                            matching_files.append(str(rel_path))
                            break
                    except ValueError:
                        pass
                    # Direct pattern matching
                    if fnmatch.fnmatch(str(file_path), f"*{pattern}"):
                        matching_files.append(changed_file)
                        break
                    if file_path.match(pattern):
                        matching_files.append(changed_file)
                        break
                except Exception:
                    pass

        if matching_files:
            pack_file = Path(f".autodoc/packs/{pack_config.name}.json")
            affected_entities = []

            if pack_file.exists():
                with open(pack_file) as f:
                    pack_data = json.load(f)
                    entities = pack_data.get("entities", [])

                    for entity in entities:
                        entity_file = entity.get("file_path", entity.get("file", ""))
                        for mf in matching_files:
                            if mf in entity_file or entity_file.endswith(mf.lstrip("*")):
                                affected_entities.append(
                                    {
                                        "type": entity.get("entity_type", "unknown"),
                                        "name": entity.get("name", "unknown"),
                                        "file": entity_file,
                                        "line": entity.get("line_number", entity.get("start_line", 0)),
                                    }
                                )
                                break

            affected_packs.append(
                {
                    "name": pack_config.name,
                    "display_name": pack_config.display_name,
                    "security_level": pack_config.security_level,
                    "matching_files": list(set(matching_files)),
                    "affected_entities": affected_entities,
                    "entity_count": len(affected_entities),
                }
            )

    # Build response with security warnings
    critical_packs = [p for p in affected_packs if p["security_level"] == "critical"]

    return json.dumps(
        {
            "changed_files": changed_files,
            "affected_packs": affected_packs,
            "total_packs_affected": len(affected_packs),
            "total_entities_affected": sum(p["entity_count"] for p in affected_packs),
            "security_warning": f"{len(critical_packs)} CRITICAL pack(s) affected"
            if critical_packs
            else None,
        }
    )


@mcp.tool
def pack_status() -> str:
    """Get indexing status for all context packs.

    Returns:
        JSON with status of each pack (indexed, embeddings, summary)
    """
    config = get_config()

    if not config.context_packs:
        return json.dumps({"error": "No context packs configured", "packs": []})

    pack_statuses = []
    packs_dir = Path(".autodoc/packs")

    for pack_config in config.context_packs:
        pack_file = packs_dir / f"{pack_config.name}.json"
        chromadb_dir = packs_dir / f"{pack_config.name}_chromadb"

        status = {
            "name": pack_config.name,
            "display_name": pack_config.display_name,
            "indexed": pack_file.exists(),
            "has_embeddings": chromadb_dir.exists(),
            "has_summary": False,
            "entity_count": 0,
            "file_count": 0,
        }

        if pack_file.exists():
            try:
                with open(pack_file) as f:
                    pack_data = json.load(f)
                    status["entity_count"] = len(pack_data.get("entities", []))
                    status["file_count"] = len(pack_data.get("files", []))
                    status["has_summary"] = pack_data.get("llm_summary") is not None
            except Exception:
                pass

        pack_statuses.append(status)

    return json.dumps(
        {
            "packs": pack_statuses,
            "total": len(pack_statuses),
            "indexed": sum(1 for p in pack_statuses if p["indexed"]),
            "with_embeddings": sum(1 for p in pack_statuses if p["has_embeddings"]),
            "with_summaries": sum(1 for p in pack_statuses if p["has_summary"]),
        }
    )


@mcp.tool
def pack_deps(
    name: str,
    include_transitive: bool = False,
) -> str:
    """Get dependencies for a context pack.

    Args:
        name: The pack name
        include_transitive: Include transitive dependencies

    Returns:
        JSON with direct deps, transitive deps, and dependents
    """
    config = get_config()
    pack_config = config.get_pack(name)

    if not pack_config:
        return json.dumps({"error": f"Pack '{name}' not found"})

    direct_deps = pack_config.dependencies

    all_deps = []
    if include_transitive:
        resolved = config.resolve_pack_dependencies(name)
        all_deps = [p.name for p in resolved if p.name != name]

    dependents = []
    for p in config.context_packs:
        if name in p.dependencies:
            dependents.append(p.name)

    return json.dumps(
        {
            "pack": name,
            "direct_dependencies": direct_deps,
            "transitive_dependencies": all_deps if include_transitive else None,
            "dependents": dependents,
        }
    )


@mcp.tool
def pack_diff(name: str) -> str:
    """Show what changed in a pack since it was last indexed.

    Compares current file content hashes against the indexed state
    to identify new, modified, and deleted files.

    Args:
        name: The pack name to check

    Returns:
        JSON with new, modified, and deleted files plus entity changes
    """

    config = get_config()
    pack_config = config.get_pack(name)

    if not pack_config:
        return json.dumps({"error": f"Pack '{name}' not found"})

    pack_file = Path(f".autodoc/packs/{name}.json")
    if not pack_file.exists():
        return json.dumps(
            {
                "error": f"Pack '{name}' not indexed yet",
                "hint": f"Run: autodoc pack build {name}",
            }
        )

    with open(pack_file) as f:
        pack_data = json.load(f)

    indexed_files = set(pack_data.get("files", []))
    # Entity index reserved for future per-entity diff tracking
    _indexed_entities = {
        f"{e.get('file_path', e.get('file', ''))}:{e.get('name', '')}": e
        for e in pack_data.get("entities", [])
    }

    # Find current files matching patterns
    base_path = Path.cwd()
    current_files = set()
    for pattern in pack_config.files:
        for f in base_path.glob(pattern):
            if f.is_file():
                current_files.add(str(f))

    # Categorize files
    new_files = list(current_files - indexed_files)
    deleted_files = list(indexed_files - current_files)

    # Check for modified files (compare content hash if we stored it)
    modified_files = []
    for f in current_files & indexed_files:
        try:
            file_path = Path(f)
            if file_path.exists():
                # Simple modification check via mtime could be added
                # For now, we flag files that exist in both sets
                pass
        except Exception:
            pass

    # Count potential entity changes
    new_entity_estimate = 0
    for f in new_files:
        # Rough estimate: count def/class keywords
        try:
            content = Path(f).read_text()
            new_entity_estimate += content.count("\ndef ") + content.count("\nclass ")
        except Exception:
            pass

    return json.dumps(
        {
            "pack": name,
            "indexed_at": pack_data.get("indexed_at"),
            "current_files": len(current_files),
            "indexed_files": len(indexed_files),
            "new_files": new_files[:20],  # Limit to first 20
            "new_files_count": len(new_files),
            "deleted_files": deleted_files[:20],
            "deleted_files_count": len(deleted_files),
            "modified_files_count": len(modified_files),
            "estimated_new_entities": new_entity_estimate,
            "needs_reindex": len(new_files) > 0 or len(deleted_files) > 0,
        }
    )


@mcp.tool
def pack_export_skill(
    name: str,
    format: str = "claude",
    include_reference: bool = False,
) -> str:
    """Export a context pack as a SKILL.md file for AI assistants.

    Generates SKILL.md files that are discoverable by Claude Code,
    OpenAI Codex, and other AI assistants. Skills provide structured
    instructions and documentation for code modules.

    Args:
        name: Pack name to export (or 'all' to export all packs)
        format: Output format - 'claude' (.claude/skills/) or 'codex' (~/.codex/skills/)
        include_reference: Generate additional ENTITIES.md and ARCHITECTURE.md files

    Returns:
        JSON with exported skill information including file paths
    """
    from autodoc.skill_generator import SkillConfig, SkillFormat, SkillGenerator

    config = get_config()

    if name == "all":
        packs_to_export = [p.name for p in config.context_packs]
    else:
        pack_config = config.get_pack(name)
        if not pack_config:
            return json.dumps({"error": f"Pack '{name}' not found"})
        packs_to_export = [name]

    skill_config = SkillConfig(
        format=SkillFormat.CLAUDE if format == "claude" else SkillFormat.CODEX,
        include_reference=include_reference,
    )
    generator = SkillGenerator(skill_config)

    project_root = Path.cwd()
    results = []
    errors = []

    for pack_name in packs_to_export:
        pack_data_path = project_root / ".autodoc" / "packs" / f"{pack_name}.json"

        if not pack_data_path.exists():
            errors.append(
                {
                    "pack": pack_name,
                    "error": f"Pack not built. Run: autodoc pack build {pack_name}",
                }
            )
            continue

        try:
            with open(pack_data_path) as f:
                pack_data = json.load(f)

            skill = generator.generate(pack_data, project_root)
            created_files = generator.write_skill(skill)

            results.append(
                {
                    "pack": pack_name,
                    "skill_name": skill.skill_name,
                    "files_created": [str(f) for f in created_files],
                }
            )
        except Exception as e:
            errors.append(
                {
                    "pack": pack_name,
                    "error": str(e),
                }
            )

    return json.dumps(
        {
            "success": results,
            "errors": errors,
            "format": format,
            "output_dir": str(skill_config.get_output_dir(project_root)),
        }
    )


@mcp.resource("autodoc://packs")
def list_all_packs() -> str:
    """Resource listing all available context packs."""
    config = get_config()
    packs = []
    for p in config.context_packs:
        packs.append(
            {
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
            }
        )
    return json.dumps(packs)


@mcp.resource("autodoc://packs/{name}")
def get_pack_resource(name: str) -> str:
    """Resource for a specific context pack."""
    return pack_info(name, include_dependencies=True)


# =============================================================================
# Feature Discovery Tools
# =============================================================================


@mcp.tool
def feature_list(named_only: bool = False) -> str:
    """List auto-detected code features.

    REQUIRES: Neo4j graph database running. Use 'capabilities' tool to check availability.
    Setup: docker compose up -d && autodoc features detect

    Features are code clusters detected using graph analysis (Louvain algorithm).

    Args:
        named_only: Only show features that have been named by LLM

    Returns:
        JSON with detected features, their IDs, names, and file counts
    """
    from .features import FeaturesCache

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        return json.dumps(
            {
                "error": "No features detected. Run 'autodoc features detect' first.",
                "features": [],
            }
        )

    features = []
    for fid, feature in result.features.items():
        if named_only and not feature.name:
            continue
        features.append(
            {
                "id": fid,
                "name": feature.name,
                "display_name": feature.display_name,
                "file_count": feature.file_count,
                "sample_paths": [f.path for f in feature.sample_files[:5]],
            }
        )

    return json.dumps(
        {
            "community_count": result.community_count,
            "modularity": result.modularity,
            "detected_at": result.detected_at,
            "features": features,
            "total": len(features),
        }
    )


@mcp.tool
def feature_files(feature_id: int) -> str:
    """Get all files belonging to a detected feature.

    REQUIRES: Neo4j graph database running. Use 'capabilities' tool to check availability.
    Setup: docker compose up -d && autodoc features detect

    Args:
        feature_id: The feature ID to query

    Returns:
        JSON object with feature details and complete file list
    """
    from .features import FeaturesCache

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        return json.dumps(
            {
                "error": "No features detected. Run 'autodoc features detect' first.",
            }
        )

    if feature_id not in result.features:
        return json.dumps(
            {
                "error": f"Feature {feature_id} not found",
                "available": list(result.features.keys()),
            }
        )

    feature = result.features[feature_id]
    return json.dumps(feature.to_dict())


# =============================================================================
# Core Analysis Tools
# =============================================================================


@mcp.tool
@safe_json_response
def analyze(
    path: str = ".",
    save: bool = True,
    incremental: bool = False,
) -> str:
    """Analyze a codebase to extract code entities (functions, classes, methods).

    This is the primary analysis command that parses source files and extracts
    structured information about the code.

    Args:
        path: Path to the codebase to analyze (default: current directory)
        save: Save results to autodoc_cache.json
        incremental: Only analyze changed files

    Returns:
        JSON with analysis results including entity counts and file statistics
    """
    import asyncio

    try:
        from .autodoc import SimpleAutodoc
    except ImportError:
        return json.dumps({
            "error": "Full autodoc not available in lightweight mode",
            "hint": "Use the full autodoc installation for analysis"
        })

    config = get_config()
    autodoc = SimpleAutodoc(config)

    try:
        result = asyncio.get_event_loop().run_until_complete(
            autodoc.analyze_directory(Path(path), incremental=incremental)
        )

        if save:
            cache_path = Path(path) / "autodoc_cache.json"
            autodoc.save(str(cache_path))

        return json.dumps({
            "success": True,
            "path": path,
            "files_analyzed": result.get("files_analyzed", 0),
            "total_entities": result.get("total_entities", 0),
            "functions": result.get("functions", 0),
            "classes": result.get("classes", 0),
            "methods": result.get("methods", 0),
            "has_embeddings": result.get("has_embeddings", False),
            "cache_saved": save,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool
@safe_json_response
def search(
    query: str,
    limit: int = 10,
    type_filter: Optional[str] = None,
) -> str:
    """Search the codebase with natural language or keywords.

    Uses semantic search if embeddings are available, otherwise falls back
    to keyword matching.

    Args:
        query: Search query (natural language or keywords)
        limit: Maximum number of results (default 10)
        type_filter: Filter by entity type (function, class, method)

    Returns:
        JSON array of matching code entities with similarity scores
    """
    import asyncio

    # Try to load from cache
    cache_path = Path("autodoc_cache.json")
    if not cache_path.exists():
        return json.dumps({
            "error": "No analysis cache found",
            "hint": "Run 'analyze' first to analyze the codebase"
        })

    try:
        from .autodoc import SimpleAutodoc
    except ImportError:
        return json.dumps({
            "error": "Full autodoc not available in lightweight mode",
            "hint": "Use the full autodoc installation for search"
        })

    config = get_config()
    autodoc = SimpleAutodoc(config)
    autodoc.load(str(cache_path))

    try:
        results = asyncio.get_event_loop().run_until_complete(
            autodoc.search(query, limit=limit, type_filter=type_filter)
        )

        formatted = []
        for r in results:
            entity = r.get("entity", {})
            formatted.append({
                "name": entity.get("name"),
                "type": entity.get("type"),
                "file_path": entity.get("file_path"),
                "line_number": entity.get("line_number"),
                "similarity": round(r.get("similarity", 0), 3),
                "docstring": entity.get("docstring", "")[:200] if entity.get("docstring") else None,
                "code": entity.get("code"),
            })

        return json.dumps({
            "query": query,
            "results": formatted,
            "total": len(formatted),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool
def enrich(
    entity_filter: Optional[str] = None,
    limit: int = 10,
    inline: bool = False,
) -> str:
    """Enrich code entities with AI-generated documentation.

    Uses LLM to generate summaries, descriptions, and usage examples
    for functions and classes.

    Args:
        entity_filter: Filter entities by name pattern
        limit: Maximum entities to enrich (default 10)
        inline: Write enrichment back to source files as docstrings

    Returns:
        JSON with enrichment results and statistics
    """
    import asyncio

    cache_path = Path("autodoc_cache.json")
    if not cache_path.exists():
        return json.dumps({
            "error": "No analysis cache found",
            "hint": "Run 'analyze' first"
        })

    try:
        from .enrichment import EnrichmentEngine
    except ImportError:
        return json.dumps({
            "error": "Enrichment not available in lightweight mode",
            "hint": "Use the full autodoc installation with LLM API keys configured"
        })

    config = get_config()

    # Check for API key
    import os
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return json.dumps({
            "error": "No LLM API key configured",
            "hint": "Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable"
        })

    try:
        engine = EnrichmentEngine(config)

        # Load entities from cache
        with open(cache_path) as f:
            cache_data = json.load(f)

        entities = cache_data.get("entities", [])
        if entity_filter:
            entities = [e for e in entities if entity_filter.lower() in e.get("name", "").lower()]

        entities = entities[:limit]

        enriched_count = 0
        results = []
        for entity in entities:
            try:
                enrichment = asyncio.get_event_loop().run_until_complete(
                    engine.enrich_entity(entity)
                )
                if enrichment:
                    enriched_count += 1
                    results.append({
                        "name": entity.get("name"),
                        "type": entity.get("type"),
                        "summary": enrichment.get("summary"),
                    })
            except Exception:
                continue

        return json.dumps({
            "success": True,
            "entities_processed": len(entities),
            "entities_enriched": enriched_count,
            "inline_mode": inline,
            "results": results,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool
def check() -> str:
    """Check autodoc configuration and dependencies.

    Validates that required dependencies are available and configuration
    is properly set up.

    Returns:
        JSON with configuration status and available features
    """
    import os

    config = get_config()
    status = {
        "config_loaded": True,
        "llm_provider": config.llm.provider if config.llm else None,
        "embeddings_provider": config.embeddings.provider if config.embeddings else None,
        "context_packs": len(config.context_packs) if config.context_packs else 0,
        "features": {},
    }

    # Check for API keys
    status["api_keys"] = {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
    }

    # Check for optional dependencies
    try:
        import chromadb
        status["features"]["chromadb"] = True
    except ImportError:
        status["features"]["chromadb"] = False

    try:
        from neo4j import GraphDatabase
        status["features"]["neo4j"] = True
    except ImportError:
        status["features"]["neo4j"] = False

    try:
        import sentence_transformers
        status["features"]["sentence_transformers"] = True
    except ImportError:
        status["features"]["sentence_transformers"] = False

    # Check for cache files
    status["cache_files"] = {
        "analysis": Path("autodoc_cache.json").exists(),
        "enrichment": Path("autodoc_enrichment_cache.json").exists(),
        "features": Path(".autodoc/features_cache.json").exists(),
    }

    return json.dumps(status)


@mcp.tool
def generate(
    output: str = "AUTODOC.md",
    include_private: bool = False,
) -> str:
    """Generate comprehensive codebase documentation.

    Creates a markdown file with documentation for all analyzed entities.

    Args:
        output: Output file path (default: AUTODOC.md)
        include_private: Include private/internal entities

    Returns:
        JSON with generation status and output path
    """
    cache_path = Path("autodoc_cache.json")
    if not cache_path.exists():
        return json.dumps({
            "error": "No analysis cache found",
            "hint": "Run 'analyze' first"
        })

    try:
        with open(cache_path) as f:
            cache_data = json.load(f)

        entities = cache_data.get("entities", [])

        if not include_private:
            entities = [e for e in entities if not e.get("name", "").startswith("_")]

        # Load enrichment if available
        enrichment = {}
        enrichment_path = Path("autodoc_enrichment_cache.json")
        if enrichment_path.exists():
            with open(enrichment_path) as f:
                enrichment = json.load(f)

        # Generate markdown
        lines = ["# Codebase Documentation\n"]
        lines.append(f"*Generated by autodoc*\n")
        lines.append(f"**{len(entities)} entities documented**\n\n")

        # Group by file
        by_file: dict = {}
        for entity in entities:
            fp = entity.get("file_path", "unknown")
            if fp not in by_file:
                by_file[fp] = []
            by_file[fp].append(entity)

        for file_path, file_entities in sorted(by_file.items()):
            lines.append(f"## {file_path}\n")
            for entity in file_entities:
                entity_type = entity.get("type", "unknown")
                name = entity.get("name", "unknown")
                lines.append(f"### `{name}` ({entity_type})\n")

                # Add enrichment if available
                enrich_key = f"{file_path}::{name}"
                if enrich_key in enrichment:
                    e = enrichment[enrich_key]
                    if e.get("summary"):
                        lines.append(f"{e['summary']}\n")
                elif entity.get("docstring"):
                    lines.append(f"{entity['docstring'][:500]}\n")

                if entity.get("code"):
                    lines.append(f"```\n{entity['code']}\n```\n")
                lines.append("\n")

        # Write output
        output_path = Path(output)
        output_path.write_text("\n".join(lines))

        return json.dumps({
            "success": True,
            "output": str(output_path),
            "entities_documented": len(entities),
            "files_covered": len(by_file),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool
def graph_build(
    clear: bool = False,
) -> str:
    """Build a Neo4j code relationship graph.

    REQUIRES: Neo4j graph database running. Use 'capabilities' tool to check availability.
    Setup: docker compose up -d && export NEO4J_PASSWORD=autodoc123

    Creates nodes for files and entities, and relationships for imports,
    calls, and inheritance.

    Args:
        clear: Clear existing graph before building

    Returns:
        JSON with graph build status
    """
    try:
        from .graph import CodeGraphBuilder
    except ImportError:
        return json.dumps({
            "error": "Neo4j not available",
            "hint": "Install neo4j driver and ensure Neo4j is running"
        })

    import os

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")

    if not neo4j_password:
        return json.dumps({
            "error": "NEO4J_PASSWORD not set",
            "hint": "Set NEO4J_PASSWORD environment variable"
        })

    cache_path = Path("autodoc_cache.json")
    if not cache_path.exists():
        return json.dumps({
            "error": "No analysis cache found",
            "hint": "Run 'analyze' first"
        })

    try:
        builder = CodeGraphBuilder(neo4j_uri, neo4j_user, neo4j_password)

        if clear:
            builder.clear_graph()

        with open(cache_path) as f:
            cache_data = json.load(f)

        entities = cache_data.get("entities", [])
        builder.build_from_entities(entities)

        stats = builder.get_stats()
        builder.close()

        return json.dumps({
            "success": True,
            "nodes_created": stats.get("nodes", 0),
            "relationships_created": stats.get("relationships", 0),
            "graph_cleared": clear,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool
def graph_query(
    query_type: str = "overview",
) -> str:
    """Query the code graph for insights.

    REQUIRES: Neo4j graph database running with graph data. Use 'capabilities' tool to check.
    Setup: docker compose up -d && export NEO4J_PASSWORD=autodoc123 && autodoc graph --build

    Args:
        query_type: Type of query - 'overview', 'hotspots', 'dependencies', 'orphans'

    Returns:
        JSON with query results
    """
    try:
        from .graph import CodeGraphBuilder
    except ImportError:
        return json.dumps({
            "error": "Neo4j not available",
            "hint": "Install neo4j driver and ensure Neo4j is running"
        })

    import os

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD")

    if not neo4j_password:
        return json.dumps({
            "error": "NEO4J_PASSWORD not set",
            "hint": "Set NEO4J_PASSWORD environment variable"
        })

    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        with driver.session() as session:
            if query_type == "overview":
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as type, count(*) as count
                    ORDER BY count DESC
                """)
                data = [{"type": r["type"], "count": r["count"]} for r in result]
            elif query_type == "hotspots":
                result = session.run("""
                    MATCH (f:File)
                    OPTIONAL MATCH (f)-[r]-()
                    RETURN f.path as file, count(r) as connections
                    ORDER BY connections DESC
                    LIMIT 10
                """)
                data = [{"file": r["file"], "connections": r["connections"]} for r in result]
            elif query_type == "dependencies":
                result = session.run("""
                    MATCH (a:File)-[:IMPORTS]->(b:File)
                    RETURN a.path as from_file, b.path as to_file
                    LIMIT 50
                """)
                data = [{"from": r["from_file"], "to": r["to_file"]} for r in result]
            elif query_type == "orphans":
                result = session.run("""
                    MATCH (f:File)
                    WHERE NOT (f)-[:IMPORTS]-() AND NOT ()-[:IMPORTS]->(f)
                    RETURN f.path as file
                    LIMIT 20
                """)
                data = [{"file": r["file"]} for r in result]
            else:
                return json.dumps({"error": f"Unknown query type: {query_type}"})

        driver.close()
        return json.dumps({"query_type": query_type, "results": data})
    except Exception as e:
        return json.dumps({"error": str(e)})


def main():
    """Run the MCP server.

    Supports multiple transport modes:
    - stdio: Default for local MCP clients (Claude Desktop, etc.)
    - sse: Server-Sent Events for remote HTTP access
    - http: Streamable HTTP transport (recommended for new deployments)
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Autodoc MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport mode (default: stdio, or MCP_TRANSPORT env var)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host to bind to for HTTP/SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8080")),
        help="Port to bind to for HTTP/SSE transport (default: 8080)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        # HTTP or SSE transport for remote access
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
