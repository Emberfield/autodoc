"""
Command-line interface for Autodoc.
"""

import asyncio
import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .autodoc import SimpleAutodoc
from .config import AutodocConfig
from .enrichment import EnrichmentCache, LLMEnricher
from .inline_enrichment import InlineEnricher, ModuleEnrichmentGenerator

# Optional graph imports - only available if dependencies are installed
try:
    from .graph import CodeGraphBuilder, CodeGraphQuery, CodeGraphVisualizer

    GRAPH_AVAILABLE = True
except ImportError as e:
    # Check if it's a specific import error or all dependencies missing
    import importlib.util

    deps_available = all(
        importlib.util.find_spec(dep) is not None
        for dep in ["matplotlib", "plotly", "neo4j", "networkx", "pyvis"]
    )
    if deps_available:
        # Dependencies are installed but there's another import issue
        print(f"Warning: Graph dependencies installed but import failed: {e}")
    GRAPH_AVAILABLE = False

# Local graph visualization (works without Neo4j)
try:
    from .local_graph import LocalCodeGraph  # noqa: F401

    LOCAL_GRAPH_AVAILABLE = True
except ImportError:
    LOCAL_GRAPH_AVAILABLE = False

console = Console()


@click.group()
def cli():
    """Autodoc - AI-powered code intelligence

    Quick start:
      1. autodoc analyze ./src          # Analyze your codebase
      2. autodoc generate              # Create AUTODOC.md documentation
      3. autodoc vector                # Generate embeddings for search
      4. autodoc graph                 # Build graph database (optional)
    """
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--save", is_flag=True, help="Save analysis to cache")
@click.option("--incremental", is_flag=True, help="Only analyze changed files")
@click.option(
    "--exclude", "-e", multiple=True, help="Patterns to exclude (can be used multiple times)"
)
@click.option("--watch", "-w", is_flag=True, help="Watch for changes and re-analyze automatically")
@click.option("--rust", is_flag=True, help="Use high-performance Rust analyzer (Python only)")
def analyze(path, save, incremental, exclude, watch, rust):
    """Analyze a codebase"""
    autodoc = SimpleAutodoc()

    if watch:
        # Watch mode
        console.print("[blue]Starting watch mode. Press Ctrl+C to stop.[/blue]")
        _run_watch_mode(autodoc, path, save, exclude)
    else:
        # Single analysis
        if rust:
            # Use Rust analyzer for Python files
            console.print("[green]Using high-performance Rust analyzer...[/green]")
            try:
                summary = _analyze_with_rust(autodoc, path, exclude)
            except ImportError:
                console.print("[red]Rust core not available. Install with: make build-rust[/red]")
                return
        else:
            # Use regular Python analyzer
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary = loop.run_until_complete(
                    autodoc.analyze_directory(
                        Path(path), incremental=incremental, exclude_patterns=list(exclude)
                    )
                )
            finally:
                loop.close()

        _display_summary(summary)

        if save:
            autodoc.save()


def _analyze_with_rust(autodoc, path, exclude_patterns):
    """Analyze using Rust core."""
    import autodoc_core

    from .analyzer import CodeEntity

    # Get all entities from Rust
    rust_entities = autodoc_core.analyze_directory_rust(
        str(path), list(exclude_patterns) if exclude_patterns else None
    )

    # Convert Rust entities to our CodeEntity format
    entities = []
    for rust_entity in rust_entities:
        # Convert parameters from list of strings to list of dicts
        params = []
        for param_name in rust_entity.parameters:
            params.append({"name": param_name, "type": None})

        entity = CodeEntity(
            type=rust_entity.entity_type,
            name=rust_entity.name,
            file_path=rust_entity.file_path,
            line_number=rust_entity.line_number,
            docstring=rust_entity.docstring,
            code=rust_entity.code,
            decorators=rust_entity.decorators,
            parameters=params,
        )

        # Add async info to decorators if needed
        if rust_entity.is_async:
            entity.decorators.append("async")

        # Store return type in response_type field
        if rust_entity.return_type:
            entity.response_type = rust_entity.return_type

        entities.append(entity)

    # Store entities in autodoc
    autodoc.entities = entities

    # Calculate summary
    summary = {
        "files_analyzed": len(set(e.file_path for e in entities)),
        "total_entities": len(entities),
        "functions": sum(1 for e in entities if e.type == "function"),
        "classes": sum(1 for e in entities if e.type == "class"),
        "methods": sum(1 for e in entities if e.type == "method"),
        "interfaces": 0,
        "types": 0,
        "has_embeddings": False,
        "languages": {
            "python": {
                "files": len(set(e.file_path for e in entities)),
                "entities": len(entities),
                "functions": sum(1 for e in entities if e.type == "function"),
                "classes": sum(1 for e in entities if e.type == "class"),
            },
            "typescript": {
                "files": 0,
                "entities": 0,
                "functions": 0,
                "classes": 0,
                "methods": 0,
                "interfaces": 0,
                "types": 0,
            },
        },
    }

    return summary


def _display_summary(summary):
    """Display analysis summary."""
    console.print("\n[bold]Analysis Summary:[/bold]")

    # Display overall stats
    console.print(f"  Files analyzed: {summary['files_analyzed']}")
    console.print(f"  Total entities: {summary['total_entities']}")
    console.print(f"  Functions: {summary['functions']}")
    console.print(f"  Classes: {summary['classes']}")

    if summary.get("methods", 0) > 0:
        console.print(f"  Methods: {summary['methods']}")
    if summary.get("interfaces", 0) > 0:
        console.print(f"  Interfaces: {summary['interfaces']}")
    if summary.get("types", 0) > 0:
        console.print(f"  Types: {summary['types']}")

    console.print(f"  Embeddings: {'enabled' if summary['has_embeddings'] else 'disabled'}")

    # Display language-specific stats
    if "languages" in summary:
        languages = summary["languages"]

        if languages["python"]["entities"] > 0:
            console.print("\n[bold]Python:[/bold]")
            console.print(f"  Files: {languages['python']['files']}")
            console.print(f"  Entities: {languages['python']['entities']}")
            console.print(f"  Functions: {languages['python']['functions']}")
            console.print(f"  Classes: {languages['python']['classes']}")

        if languages["typescript"]["entities"] > 0:
            console.print("\n[bold]TypeScript:[/bold]")
            console.print(f"  Files: {languages['typescript']['files']}")
            console.print(f"  Entities: {languages['typescript']['entities']}")
            console.print(f"  Functions: {languages['typescript']['functions']}")
            console.print(f"  Classes: {languages['typescript']['classes']}")
            console.print(f"  Methods: {languages['typescript']['methods']}")
            console.print(f"  Interfaces: {languages['typescript']['interfaces']}")
            console.print(f"  Types: {languages['typescript']['types']}")


def _run_watch_mode(autodoc, path, save, exclude):
    """Run analysis in watch mode."""
    import time

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        console.print("[red]Watch mode requires 'watchdog' package.[/red]")
        console.print("[yellow]Install with: pip install watchdog[/yellow]")
        return

    class CodeChangeHandler(FileSystemEventHandler):
        def __init__(self):
            self.last_modified = {}
            self.debounce_seconds = 1.0

        def should_process(self, file_path):
            """Check if file should be processed."""
            if not file_path.endswith((".py", ".ts", ".tsx")):
                return False

            # Check debounce
            now = time.time()
            last = self.last_modified.get(file_path, 0)
            if now - last < self.debounce_seconds:
                return False

            self.last_modified[file_path] = now
            return True

        def on_modified(self, event):
            if event.is_directory:
                return

            if self.should_process(event.src_path):
                console.print(f"\n[yellow]Detected change in {event.src_path}[/yellow]")

                # Run incremental analysis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    summary = loop.run_until_complete(
                        autodoc.analyze_directory(
                            Path(path), incremental=True, exclude_patterns=list(exclude)
                        )
                    )
                    _display_summary(summary)
                    if save:
                        autodoc.save()
                        console.print("[green]✅ Cache updated[/green]")
                except Exception as e:
                    console.print(f"[red]Error during analysis: {e}[/red]")
                finally:
                    loop.close()

                console.print("\n[dim]Watching for changes... (Ctrl+C to stop)[/dim]")

    # Initial analysis
    console.print("[yellow]Running initial analysis...[/yellow]")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        summary = loop.run_until_complete(
            autodoc.analyze_directory(Path(path), incremental=False, exclude_patterns=list(exclude))
        )
        _display_summary(summary)
        if save:
            autodoc.save()
    finally:
        loop.close()

    # Set up file watcher
    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    console.print("\n[green]Watch mode started. Monitoring for changes...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[yellow]Stopping watch mode...[/yellow]")
    observer.join()
    console.print("[green]Watch mode stopped.[/green]")


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Number of results")
@click.option("--type", "-t", help="Filter by entity type (function, class, method, etc.)")
@click.option("--file", "-f", help="Filter by file pattern (supports wildcards)")
@click.option("--regex", "-r", is_flag=True, help="Use regex pattern matching")
def search(query, limit, type, file, regex):
    """Search for code entities

    Examples:
      autodoc search "parse.*file" --regex
      autodoc search "analyze" --type function
      autodoc search "test" --file "*/tests/*"
    """
    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            autodoc.search(query, limit, type_filter=type, file_filter=file, use_regex=regex)
        )
    finally:
        loop.close()

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("File", style="green")
    table.add_column("Match", style="yellow")

    for result in results:
        entity = result["entity"]
        table.add_row(
            entity["type"],
            entity["name"],
            Path(entity["file_path"]).name,
            f"{result['similarity']:.2f}",
        )

    console.print(table)


@cli.command()
@click.argument("cache1", type=click.Path(exists=True), default="autodoc_cache.json")
@click.argument("cache2", type=click.Path(exists=True), required=False)
@click.option("--detailed", "-d", is_flag=True, help="Show detailed differences")
def diff(cache1, cache2, detailed):
    """Compare two analysis caches to see what changed

    Examples:
      autodoc diff                               # Compare current with previous backup
      autodoc diff cache1.json cache2.json      # Compare two specific caches
      autodoc diff --detailed                   # Show detailed changes
    """
    import json
    from pathlib import Path

    # If no second cache specified, look for backup
    if not cache2:
        backup_path = Path(f"{cache1}.backup")
        if backup_path.exists():
            cache2 = str(backup_path)
            console.print(f"[blue]Comparing {cache1} with backup {cache2}[/blue]")
        else:
            console.print("[red]No second cache file specified and no backup found.[/red]")
            console.print("[yellow]Usage: autodoc diff [cache1] [cache2][/yellow]")
            return

    # Load caches
    try:
        with open(cache1, "r") as f:
            data1 = json.load(f)
        with open(cache2, "r") as f:
            data2 = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading cache files: {e}[/red]")
        return

    entities1 = {f"{e['file_path']}:{e['name']}": e for e in data1.get("entities", [])}
    entities2 = {f"{e['file_path']}:{e['name']}": e for e in data2.get("entities", [])}

    # Find differences
    added = set(entities1.keys()) - set(entities2.keys())
    removed = set(entities2.keys()) - set(entities1.keys())
    common = set(entities1.keys()) & set(entities2.keys())

    modified = []
    for key in common:
        e1 = entities1[key]
        e2 = entities2[key]
        # Check if entity has changed (line number, docstring, code)
        if (
            e1.get("line_number") != e2.get("line_number")
            or e1.get("docstring") != e2.get("docstring")
            or e1.get("code") != e2.get("code")
        ):
            modified.append(key)

    # Display summary
    console.print("\n[bold]Analysis Diff Summary:[/bold]")
    console.print(f"  Added: [green]{len(added)}[/green] entities")
    console.print(f"  Removed: [red]{len(removed)}[/red] entities")
    console.print(f"  Modified: [yellow]{len(modified)}[/yellow] entities")
    console.print(f"  Unchanged: {len(common) - len(modified)} entities")

    if detailed or (added or removed or modified):
        # Show details
        if added:
            console.print("\n[green]Added entities:[/green]")
            for key in sorted(added):
                entity = entities1[key]
                console.print(
                    f"  + {entity['type']} {entity['name']} in {Path(entity['file_path']).name}"
                )

        if removed:
            console.print("\n[red]Removed entities:[/red]")
            for key in sorted(removed):
                entity = entities2[key]
                console.print(
                    f"  - {entity['type']} {entity['name']} in {Path(entity['file_path']).name}"
                )

        if modified and detailed:
            console.print("\n[yellow]Modified entities:[/yellow]")
            for key in sorted(modified):
                entity1 = entities1[key]
                entity2 = entities2[key]
                console.print(
                    f"  ~ {entity1['type']} {entity1['name']} in {Path(entity1['file_path']).name}"
                )

                # Show what changed
                if entity1.get("line_number") != entity2.get("line_number"):
                    console.print(
                        f"    Line: {entity2.get('line_number')} → {entity1.get('line_number')}"
                    )
                if entity1.get("docstring") != entity2.get("docstring"):
                    console.print(
                        f"    Docstring: {'added' if entity1.get('docstring') and not entity2.get('docstring') else 'modified' if entity1.get('docstring') else 'removed'}"
                    )


@cli.command()
@click.argument("output", type=click.Path(), default="autodoc_export.zip")
@click.option("--include-enrichments", is_flag=True, help="Include enrichment cache")
@click.option("--include-config", is_flag=True, help="Include configuration")
def export(output, include_enrichments, include_config):
    """Export analysis data for sharing with team

    Creates a zip file containing:
    - autodoc_cache.json (analysis results)
    - autodoc_enrichment_cache.json (if --include-enrichments)
    - autodoc_config.json (if --include-config)
    """
    import zipfile
    from pathlib import Path

    files_to_export = []

    # Always include main cache
    if Path("autodoc_cache.json").exists():
        files_to_export.append("autodoc_cache.json")
    else:
        console.print("[red]No analysis cache found. Run 'autodoc analyze' first.[/red]")
        return

    # Include enrichments if requested
    if include_enrichments and Path("autodoc_enrichment_cache.json").exists():
        files_to_export.append("autodoc_enrichment_cache.json")

    # Include config if requested
    if include_config and Path("autodoc_config.json").exists():
        files_to_export.append("autodoc_config.json")

    # Create zip file
    try:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files_to_export:
                zf.write(file)
                console.print(f"[green]Added {file}[/green]")

        # Get file size
        size = Path(output).stat().st_size / 1024  # KB
        console.print(f"\n[green]✅ Exported to {output} ({size:.1f} KB)[/green]")
        console.print(f"[blue]Files included: {', '.join(files_to_export)}[/blue]")

    except Exception as e:
        console.print(f"[red]Error creating export: {e}[/red]")


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
def import_(input_file, overwrite):
    """Import analysis data from export file

    Extracts and imports:
    - autodoc_cache.json
    - autodoc_enrichment_cache.json (if present)
    - autodoc_config.json (if present)
    """
    import zipfile
    from pathlib import Path

    try:
        with zipfile.ZipFile(input_file, "r") as zf:
            # List files in archive
            files = zf.namelist()
            console.print(f"[blue]Found {len(files)} files in archive:[/blue]")
            for file in files:
                console.print(f"  • {file}")

            # Check for existing files
            existing = [f for f in files if Path(f).exists()]
            if existing and not overwrite:
                console.print("\n[yellow]The following files already exist:[/yellow]")
                for file in existing:
                    console.print(f"  • {file}")
                console.print("[red]Use --overwrite to replace existing files.[/red]")
                return

            # Extract files
            console.print("\n[yellow]Importing files...[/yellow]")
            for file in files:
                zf.extract(file)
                console.print(f"[green]✅ Imported {file}[/green]")

            # Load and show summary
            autodoc = SimpleAutodoc()
            autodoc.load()
            console.print(
                f"\n[green]Successfully imported {len(autodoc.entities)} entities[/green]"
            )

            # Check for enrichments
            if "autodoc_enrichment_cache.json" in files:
                console.print("[blue]Enrichment cache also imported[/blue]")

    except Exception as e:
        console.print(f"[red]Error importing: {e}[/red]")


@cli.command()
@click.option("--output", "-o", help="Output file for test mapping (default: stdout)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format",
)
def test_map(output, format):
    """Map test functions to the code they test

    Analyzes test files to find which functions are being tested,
    helping identify test coverage gaps.
    """
    import json
    from pathlib import Path

    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Find test functions and the functions they test
    test_mapping = {}
    tested_functions = set()

    # Get all test functions
    test_functions = [
        e for e in autodoc.entities if e.file_path.find("test") != -1 and e.type == "function"
    ]

    for test_func in test_functions:
        if not test_func.code:
            continue

        # Simple heuristic: look for function calls in test code
        # This is a basic implementation - could be enhanced with AST analysis
        tested = []

        # Look for direct function calls
        import re

        # Match function calls like func_name( or self.func_name(
        call_pattern = r"(?:self\.)?\b(\w+)\s*\("
        calls = re.findall(call_pattern, test_func.code)

        # Match against known functions
        for call in calls:
            for entity in autodoc.entities:
                if (
                    entity.type == "function"
                    and entity.name == call
                    and entity.file_path.find("test") == -1
                ):
                    tested.append(
                        {"name": entity.name, "file": entity.file_path, "line": entity.line_number}
                    )
                    tested_functions.add(f"{entity.file_path}:{entity.name}")

        if tested:
            test_mapping[f"{test_func.file_path}::{test_func.name}"] = tested

    # Find untested functions
    all_functions = [
        e for e in autodoc.entities if e.type == "function" and e.file_path.find("test") == -1
    ]
    untested = []
    for func in all_functions:
        func_id = f"{func.file_path}:{func.name}"
        if func_id not in tested_functions and not func.name.startswith("_"):
            untested.append({"name": func.name, "file": func.file_path, "line": func.line_number})

    # Format output
    if format == "json":
        result = {
            "test_mapping": test_mapping,
            "untested_functions": untested,
            "summary": {
                "total_functions": len(all_functions),
                "tested_functions": len(tested_functions),
                "untested_functions": len(untested),
                "coverage_percentage": (
                    (len(tested_functions) / len(all_functions) * 100) if all_functions else 0
                ),
            },
        }
        output_text = json.dumps(result, indent=2)

    elif format == "markdown":
        lines = ["# Test Coverage Mapping\n"]
        lines.append(f"**Total Functions:** {len(all_functions)}")
        lines.append(f"**Tested:** {len(tested_functions)}")
        lines.append(f"**Untested:** {len(untested)}")
        lines.append(
            f"**Coverage:** {len(tested_functions) / len(all_functions) * 100:.1f}%\n"
            if all_functions
            else "**Coverage:** 0%\n"
        )

        lines.append("## Test Mapping\n")
        for test, functions in test_mapping.items():
            lines.append(f"### {test}")
            for func in functions:
                lines.append(f"- `{func['name']}` in {Path(func['file']).name}:{func['line']}")
            lines.append("")

        if untested:
            lines.append("## Untested Functions\n")
            for func in untested[:20]:  # Show first 20
                lines.append(f"- `{func['name']}` in {Path(func['file']).name}:{func['line']}")
            if len(untested) > 20:
                lines.append(f"\n... and {len(untested) - 20} more")

        output_text = "\n".join(lines)

    else:  # table format
        # Summary
        console.print("\n[bold]Test Coverage Summary:[/bold]")
        console.print(f"  Total functions: {len(all_functions)}")
        console.print(f"  Tested: [green]{len(tested_functions)}[/green]")
        console.print(f"  Untested: [red]{len(untested)}[/red]")
        if all_functions:
            console.print(f"  Coverage: {len(tested_functions) / len(all_functions) * 100:.1f}%")

        # Show some test mappings
        if test_mapping:
            console.print("\n[bold]Sample Test Mappings:[/bold]")
            shown = 0
            for test, functions in list(test_mapping.items())[:5]:
                test_name = test.split("::")[1]
                console.print(f"\n[cyan]{test_name}[/cyan] tests:")
                for func in functions[:3]:
                    console.print(f"  → {func['name']} ({Path(func['file']).name})")
                if len(functions) > 3:
                    console.print(f"  ... and {len(functions) - 3} more")
                shown += 1

        # Show untested functions
        if untested:
            console.print(f"\n[bold]Untested Functions ({len(untested)} total):[/bold]")
            table = Table()
            table.add_column("Function", style="red")
            table.add_column("File", style="dim")
            table.add_column("Line", style="dim")

            for func in untested[:10]:
                table.add_row(func["name"], Path(func["file"]).name, str(func["line"]))
            console.print(table)
            if len(untested) > 10:
                console.print(f"[dim]... and {len(untested) - 10} more[/dim]")

        output_text = None

    # Write to file if specified
    if output and output_text:
        with open(output, "w") as f:
            f.write(output_text)
        console.print(f"\n[green]Output written to {output}[/green]")


@cli.command()
def check():
    """Check dependencies and configuration"""
    console.print("[bold]Autodoc Status:[/bold]\n")

    # Load config to check embedding provider
    config = AutodocConfig.load()
    embedding_provider = config.embeddings.provider

    console.print(f"[blue]Embedding Provider: {embedding_provider}[/blue]")

    if embedding_provider == "chromadb":
        # Check ChromaDB
        try:
            from .chromadb_embedder import ChromaDBEmbedder

            embedder = ChromaDBEmbedder(
                persist_directory=config.embeddings.persist_directory
            )
            stats = embedder.get_stats()
            console.print("✅ ChromaDB configured")
            console.print(
                f"   Model: {config.embeddings.chromadb_model}"
            )
            console.print(f"   Embeddings: {stats['total_embeddings']}")
            console.print(f"   Directory: {stats['persist_directory']}")
        except Exception as e:
            console.print(f"❌ ChromaDB error: {e}")
    else:
        # Check OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "sk-...":
            console.print("✅ OpenAI API key configured")
        else:
            console.print("❌ OpenAI API key not found")
            console.print("   Set OPENAI_API_KEY in .env file")

    if Path("autodoc_cache.json").exists():
        console.print("✅ Analyzed code cache found")
    else:
        console.print("ℹ️  No analyzed code found - run 'autodoc analyze' first")

    # Check for enrichment cache
    if Path("autodoc_enrichment_cache.json").exists():
        console.print("✅ Enrichment cache found")

    # Check for config file
    if Path(".autodoc.yml").exists() or Path("autodoc.yml").exists():
        console.print("✅ Configuration file found")
    else:
        console.print("ℹ️  No config file - using defaults (run 'autodoc init' to create)")


@cli.command(name="init")
def init_config():
    """Initialize autodoc configuration file"""
    config_path = Path.cwd() / ".autodoc.yml"

    if config_path.exists():
        console.print("[yellow]Configuration file already exists at .autodoc.yml[/yellow]")
        if not click.confirm("Overwrite existing configuration?"):
            return

    # Create default config
    config = AutodocConfig()
    config.save(config_path)

    console.print("[green]✅ Created .autodoc.yml configuration file[/green]")
    console.print("\n[blue]Configuration sections:[/blue]")
    console.print("  • llm: LLM provider settings (OpenAI, Anthropic, Ollama)")
    console.print("  • enrichment: Code enrichment settings")
    console.print("  • embeddings: Embedding generation settings")
    console.print("  • graph: Graph database settings")
    console.print("  • analysis: Code analysis settings")
    console.print("  • output: Documentation output settings")
    console.print("\n[yellow]Remember to set your API keys via environment variables:[/yellow]")
    console.print("  • OpenAI: export OPENAI_API_KEY='your-key'")
    console.print("  • Anthropic: export ANTHROPIC_API_KEY='your-key'")


@cli.command(name="enrich")
@click.option("--limit", "-l", default=None, type=int, help="Limit number of entities to enrich")
@click.option("--filter", "-f", help="Filter entities by name pattern")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["function", "class", "all"]),
    default="all",
    help="Entity type to enrich",
)
@click.option("--force", is_flag=True, help="Force re-enrichment of cached entities")
@click.option("--provider", help="Override LLM provider (openai, anthropic, ollama)")
@click.option("--model", help="Override LLM model")
@click.option(
    "--regenerate-embeddings", is_flag=True, help="Regenerate embeddings after enrichment"
)
@click.option("--inline", is_flag=True, help="Add enriched docstrings directly to code files")
@click.option(
    "--incremental", is_flag=True, default=True, help="Only process changed files (default: true)"
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup files before modifying (default: true)",
)
@click.option("--module-files", is_flag=True, help="Generate module-level enrichment files")
@click.option(
    "--module-format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Format for module enrichment files",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without modifying files")
def enrich(
    limit,
    filter,
    type,
    force,
    provider,
    model,
    regenerate_embeddings,
    inline,
    incremental,
    backup,
    module_files,
    module_format,
    dry_run,
):
    """Enrich code entities with LLM-generated descriptions"""
    # Run async function
    asyncio.run(
        _enrich_async(
            limit,
            filter,
            type,
            force,
            provider,
            model,
            regenerate_embeddings,
            inline,
            incremental,
            backup,
            module_files,
            module_format,
            dry_run,
        )
    )


async def _enrich_async(
    limit,
    filter,
    type,
    force,
    provider,
    model,
    regenerate_embeddings,
    inline,
    incremental,
    backup,
    module_files,
    module_format,
    dry_run,
):
    """Async implementation of enrich command"""
    # Load config
    config = AutodocConfig.load()

    # Override provider/model if specified
    if provider:
        config.llm.provider = provider
    if model:
        config.llm.model = model

    # Check API key (but allow inline/module operations with cached data)
    api_key = config.llm.get_api_key()
    if not api_key and config.llm.provider != "ollama":
        if not (inline or module_files):
            console.print(f"[red]No API key found for {config.llm.provider}[/red]")
            console.print("[yellow]Set via environment variable or .autodoc.yml[/yellow]")
            console.print(
                f"[yellow]Example: export {config.llm.provider.upper()}_API_KEY=your-api-key[/yellow]"
            )
            return
        else:
            console.print(
                f"[yellow]No API key found for {config.llm.provider} - will use cached enrichments only[/yellow]"
            )
            console.print("[dim]To generate new enrichments, set your API key[/dim]")

    # Load entities
    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Filter entities
    entities = autodoc.entities
    if type != "all":
        entities = [e for e in entities if e.type == type]
    if filter:
        import re

        pattern = re.compile(filter, re.IGNORECASE)
        entities = [e for e in entities if pattern.search(e.name)]
    if limit:
        entities = entities[:limit]

    console.print(
        f"[yellow]Enriching {len(entities)} entities with {config.llm.provider}/{config.llm.model}...[/yellow]"
    )

    # Load cache
    cache = EnrichmentCache()

    # Filter out already cached entities unless force is set
    if not force:
        uncached = []
        for entity in entities:
            cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
            if not cache.get_enrichment(cache_key):
                uncached.append(entity)

        if len(uncached) < len(entities):
            console.print(
                f"[blue]Skipping {len(entities) - len(uncached)} cached entities (use --force to re-enrich)[/blue]"
            )
        entities = uncached

    # Initialize counters
    enriched_count = 0
    failed_count = 0

    if not entities:
        console.print("[green]All entities are already enriched![/green]")
    elif not api_key and config.llm.provider != "ollama":
        console.print("[yellow]Skipping enrichment - no API key available[/yellow]")
    else:
        # Enrich entities
        async with LLMEnricher(config) as enricher:
            with console.status("[yellow]Enriching entities...[/yellow]") as status:
                # Process in smaller batches for better progress feedback
                batch_size = min(config.enrichment.batch_size, 5)

                for i in range(0, len(entities), batch_size):
                    batch = entities[i : i + batch_size]
                    batch_names = [e.name for e in batch]
                    status.update(f"[yellow]Enriching: {', '.join(batch_names)}...[/yellow]")

                    try:
                        enriched_batch = await enricher.enrich_entities(batch)

                        # Cache results
                        for enriched in enriched_batch:
                            cache_key = f"{enriched.entity.file_path}:{enriched.entity.name}:{enriched.entity.line_number}"
                            cache.set_enrichment(
                                cache_key,
                                {
                                    "description": enriched.description,
                                    "purpose": enriched.purpose,
                                    "key_features": enriched.key_features,
                                    "complexity_notes": enriched.complexity_notes,
                                    "usage_examples": enriched.usage_examples,
                                    "design_patterns": enriched.design_patterns,
                                    "dependencies": enriched.dependencies,
                                },
                            )
                            enriched_count += 1

                    except Exception as e:
                        console.print(f"[red]Error enriching batch: {e}[/red]")
                        failed_count += len(batch)

    # Save cache
    if not dry_run:
        cache.save_cache()
    else:
        console.print("\n[blue]DRY RUN: Enrichment cache was not saved[/blue]")

    # Summary
    console.print(f"\n[green]✅ Enriched {enriched_count} entities[/green]")
    if failed_count > 0:
        console.print(f"[red]❌ Failed to enrich {failed_count} entities[/red]")

    console.print("\n[blue]Enrichment cached in autodoc_enrichment_cache.json[/blue]")

    # Handle inline enrichment
    if inline:
        if dry_run:
            console.print(
                "\n[yellow]DRY RUN: Would add enriched docstrings inline to code files...[/yellow]"
            )
        else:
            console.print("\n[yellow]Adding enriched docstrings inline to code files...[/yellow]")

        inline_enricher = InlineEnricher(config, backup=backup, dry_run=dry_run)
        inline_results = await inline_enricher.enrich_files_inline(
            autodoc.entities, incremental=incremental, force=force
        )

        total_updated = sum(r.updated_docstrings for r in inline_results)
        total_errors = sum(len(r.errors) for r in inline_results)

        if dry_run:
            console.print(
                f"[green]✅ Would update {total_updated} docstrings across {len(inline_results)} files[/green]"
            )
            if total_errors > 0:
                console.print(
                    f"[red]❌ {total_errors} errors would occur during inline enrichment[/red]"
                )
            console.print("[blue]💡 No files were modified (dry run)[/blue]")
        else:
            console.print(
                f"[green]✅ Updated {total_updated} docstrings across {len(inline_results)} files[/green]"
            )
            if total_errors > 0:
                console.print(
                    f"[red]❌ {total_errors} errors occurred during inline enrichment[/red]"
                )
            console.print(
                "[blue]💡 Enriched docstrings are now available in your code files[/blue]"
            )

    # Handle module enrichment files
    if module_files:
        if dry_run:
            console.print(
                f"\n[yellow]DRY RUN: Would generate module-level enrichment files ({module_format})...[/yellow]"
            )
        else:
            console.print(
                f"\n[yellow]Generating module-level enrichment files ({module_format})...[/yellow]"
            )

        module_generator = ModuleEnrichmentGenerator(config, dry_run=dry_run)
        generated_files = await module_generator.generate_module_enrichment_files(
            autodoc.entities, output_format=module_format
        )

        if dry_run:
            console.print(
                f"[green]✅ Would generate {len(generated_files)} module enrichment files[/green]"
            )
        else:
            console.print(
                f"[green]✅ Generated {len(generated_files)} module enrichment files[/green]"
            )

        for file_path in generated_files[:5]:  # Show first 5
            console.print(f"  📄 {Path(file_path).name}")
        if len(generated_files) > 5:
            console.print(f"  ... and {len(generated_files) - 5} more")

    if not inline and not module_files:
        console.print(
            "[yellow]Run 'autodoc generate' to create documentation with enriched descriptions[/yellow]"
        )
        console.print("[blue]💡 Use --inline to add docstrings directly to code files[/blue]")
        console.print(
            "[blue]💡 Use --module-files to generate module-level enrichment files[/blue]"
        )

    # Regenerate embeddings if requested
    if regenerate_embeddings:
        console.print("\n[yellow]Regenerating embeddings with enriched content...[/yellow]")

        # Create new autodoc instance with config
        autodoc_regen = SimpleAutodoc(config)
        autodoc_regen.entities = autodoc.entities  # Copy entities

        # Check which embedder is configured
        if autodoc_regen.chromadb_embedder:
            # Clear existing ChromaDB embeddings
            console.print("[blue]Clearing existing ChromaDB embeddings...[/blue]")
            autodoc_regen.chromadb_embedder.clear_collection()

            # Re-embed all entities with enrichment
            embedded_count = await autodoc_regen.chromadb_embedder.embed_entities(
                autodoc_regen.entities,
                use_enrichment=True,
                batch_size=config.embeddings.batch_size,
            )
            console.print(
                f"[green]✅ Re-embedded {embedded_count} entities in ChromaDB with enriched content[/green]"
            )

        elif autodoc_regen.embedder:
            # Use OpenAI embeddings
            console.print("[blue]Regenerating OpenAI embeddings...[/blue]")

            texts = []
            for entity in autodoc_regen.entities:
                text = f"{entity.type} {entity.name}"

                # Use enriched description
                cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                enrichment = cache.get_enrichment(cache_key)
                if enrichment and enrichment.get("description"):
                    text += f": {enrichment['description']}"
                    if enrichment.get("key_features"):
                        text += " Features: " + ", ".join(enrichment["key_features"])
                elif entity.docstring:
                    text += f": {entity.docstring}"

                texts.append(text)

            # Generate embeddings
            embeddings = await autodoc_regen.embedder.embed_batch(texts)
            for entity, embedding in zip(autodoc_regen.entities, embeddings):
                entity.embedding = embedding

            # Save updated entities
            autodoc_regen.save()

            console.print(
                f"[green]✅ Regenerated {len(embeddings)} embeddings with enriched content[/green]"
            )
        else:
            console.print(
                "[yellow]No embedder configured - skipping embedding regeneration[/yellow]"
            )

        console.print("[blue]💡 Use 'autodoc search' to see improved search results[/blue]")


@cli.command(name="graph")
@click.option("--clear", is_flag=True, help="Clear existing graph data")
@click.option("--visualize", is_flag=True, help="Create visualizations after building graph")
def graph(clear, visualize):
    """Build code relationship graph database"""
    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available.[/red]")

        # Check if dependencies are installed
        import importlib.util

        deps = {
            "matplotlib": "visualization",
            "plotly": "interactive graphs",
            "neo4j": "graph database",
            "networkx": "graph analysis",
            "pyvis": "network visualization",
        }

        missing = []
        for dep, desc in deps.items():
            if importlib.util.find_spec(dep) is None:
                missing.append(f"{dep} ({desc})")

        if missing:
            console.print("[yellow]Missing dependencies:[/yellow]")
            for dep in missing:
                console.print(f"  • {dep}")
            console.print("\n[blue]Install with:[/blue]")
            console.print("  pip install matplotlib plotly neo4j networkx pyvis")
            console.print("  # or")
            console.print("  uv pip install matplotlib plotly neo4j networkx pyvis")
        else:
            console.print(
                "[yellow]All dependencies are installed, but graph import failed.[/yellow]"
            )
            console.print("\nPossible causes:")
            console.print("  • Neo4j database is not running")
            console.print("  • Import conflicts or version incompatibilities")
            console.print("\n[blue]To start Neo4j:[/blue]")
            console.print("  • Docker: docker run -p 7687:7687 -p 7474:7474 neo4j")
            console.print("  • Desktop: Start Neo4j Desktop application")
            console.print("\n[blue]For local visualization without Neo4j, try:[/blue]")
            console.print("  autodoc local-graph")
        return

    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    try:
        console.print("[yellow]Building code graph database...[/yellow]")
        builder = CodeGraphBuilder()

        if clear:
            builder.clear_graph()
            console.print("✅ Cleared existing graph data")

        builder.build_from_autodoc(autodoc)

        console.print("[green]✅ Code graph database built successfully![/green]")

        # Create visualizations if requested
        if visualize:
            console.print("[yellow]Creating graph visualizations...[/yellow]")
            query = CodeGraphQuery()
            visualizer = CodeGraphVisualizer(query)

            try:
                # Create interactive graph
                visualizer.create_interactive_graph("code_graph.html")
                console.print("  • Interactive graph: code_graph.html")

                # Create dependency graph
                visualizer.create_module_dependency_graph("module_dependencies.png")
                console.print("  • Module dependencies: module_dependencies.png")

                console.print("[green]✅ Visualizations created![/green]")
            except Exception as viz_error:
                console.print(
                    f"[yellow]Warning: Could not create visualizations: {viz_error}[/yellow]"
                )
            finally:
                query.close()
        else:
            console.print(
                "[blue]💡 Use 'autodoc graph --visualize' to create visualizations[/blue]"
            )

        builder.close()

    except Exception as e:
        console.print(f"[red]Error building graph: {e}[/red]")
        console.print("[yellow]Make sure Neo4j is running at bolt://localhost:7687[/yellow]")


@cli.command(name="vector")
@click.option("--regenerate", is_flag=True, help="Regenerate all embeddings (overwrite existing)")
def vector(regenerate):
    """Generate embeddings for semantic search"""
    # Load config to determine embedding provider
    config = AutodocConfig.load()
    autodoc = SimpleAutodoc(config)

    # Load existing entities
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Check which embedder is available
    if autodoc.chromadb_embedder:
        # Handle ChromaDB embeddings
        console.print("[blue]Using ChromaDB for embeddings[/blue]")

        # Get current stats
        stats = autodoc.chromadb_embedder.get_stats()
        existing_embeddings = stats["total_embeddings"]

        if existing_embeddings > 0 and not regenerate:
            console.print(
                f"[yellow]Found {existing_embeddings} existing embeddings in ChromaDB.[/yellow]"
            )
            console.print(f"[blue]Enriched ratio: {stats['sample_enriched_ratio']:.1%}[/blue]")
            console.print("[blue]💡 Use --regenerate to overwrite existing embeddings[/blue]")
            return

        if regenerate and existing_embeddings > 0:
            console.print("[yellow]Clearing existing ChromaDB embeddings...[/yellow]")
            autodoc.chromadb_embedder.clear_collection()

        # Run embedding generation asynchronously
        import asyncio

        embedded_count = asyncio.run(
            autodoc.chromadb_embedder.embed_entities(
                autodoc.entities,
                use_enrichment=True,
                batch_size=config.embeddings.batch_size,
            )
        )

        console.print(f"[green]✅ Embedded {embedded_count} entities in ChromaDB![/green]")
        console.print("[blue]💡 You can now use 'autodoc search' for semantic search[/blue]")

    elif autodoc.embedder:
        # Handle OpenAI embeddings (existing code)
        console.print("[blue]Using OpenAI for embeddings[/blue]")

    # Check if embeddings already exist
    existing_embeddings = sum(1 for entity in autodoc.entities if entity.embedding is not None)

    if existing_embeddings > 0 and not regenerate:
        console.print(f"[yellow]Found {existing_embeddings} existing embeddings.[/yellow]")
        console.print("[blue]💡 Use --regenerate to overwrite existing embeddings[/blue]")
        return

    try:
        console.print("[yellow]Generating embeddings for semantic search...[/yellow]")

        # Prepare texts for embedding
        texts = []
        entities_to_embed = []

        for entity in autodoc.entities:
            if regenerate or entity.embedding is None:
                text = f"{entity.type} {entity.name}"
                if entity.docstring:
                    text += f": {entity.docstring}"
                texts.append(text)
                entities_to_embed.append(entity)

        if not texts:
            console.print("[green]✅ All entities already have embeddings![/green]")
            return

        console.print(f"Generating embeddings for {len(texts)} entities...")

        # Generate embeddings in batches
        import asyncio

        embeddings = asyncio.run(autodoc.embedder.embed_batch(texts))

        # Assign embeddings to entities
        for entity, embedding in zip(entities_to_embed, embeddings):
            entity.embedding = embedding

        # Save updated entities
        autodoc.save()

        console.print(f"[green]✅ Generated {len(embeddings)} embeddings![/green]")
        console.print("[blue]💡 You can now use 'autodoc search' for semantic search[/blue]")

    except Exception as e:
        console.print(f"[red]Error generating embeddings: {e}[/red]")

    else:
        console.print("[red]No embedding provider configured.[/red]")
        console.print(
            "[yellow]Configure OpenAI API key or set embeddings.provider: chromadb in .autodoc.yml[/yellow]"
        )


@cli.command(name="visualize-graph")
@click.option("--output", "-o", default="code_graph.html", help="Output file for interactive graph")
@click.option("--deps", is_flag=True, help="Create module dependency graph")
@click.option("--complexity", is_flag=True, help="Create complexity heatmap")
@click.option("--all", "create_all", is_flag=True, help="Create all visualizations")
def visualize_graph(output, deps, complexity, create_all):
    """Create interactive visualizations of the code graph"""
    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available. Install graph dependencies:[/red]")
        console.print("pip install matplotlib plotly neo4j networkx pyvis")
        return

    try:
        console.print("[yellow]Creating graph visualizations...[/yellow]")
        query = CodeGraphQuery()
        visualizer = CodeGraphVisualizer(query)

        created_files = []

        if create_all or not (deps or complexity):
            # Default: create interactive graph
            visualizer.create_interactive_graph(output)
            created_files.append(output)

        if create_all or deps:
            deps_file = "module_dependencies.png"
            visualizer.create_module_dependency_graph(deps_file)
            created_files.append(deps_file)

        if create_all or complexity:
            complexity_file = "complexity_heatmap.html"
            visualizer.create_complexity_heatmap(complexity_file)
            created_files.append(complexity_file)

        query.close()

        console.print("[green]✅ Graph visualizations created:[/green]")
        for file in created_files:
            console.print(f"  - {file}")

    except Exception as e:
        console.print(f"[red]Error creating visualizations: {e}[/red]")
        console.print("[yellow]Make sure you've run 'autodoc graph' first[/yellow]")


@cli.command(name="query-graph")
@click.option("--entry-points", is_flag=True, help="Find entry points")
@click.option("--test-coverage", is_flag=True, help="Analyze test coverage")
@click.option("--patterns", is_flag=True, help="Find code patterns")
@click.option("--complexity", is_flag=True, help="Show module complexity")
@click.option("--deps", help="Find dependencies for entity")
@click.option("--all", "show_all", is_flag=True, help="Show all analysis")
def query_graph(entry_points, test_coverage, patterns, complexity, deps, show_all):
    """Query the code graph for insights"""
    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available. Install graph dependencies:[/red]")
        console.print("pip install matplotlib plotly neo4j networkx pyvis")
        return

    try:
        query = CodeGraphQuery()

        if show_all or entry_points:
            console.print("\n[bold]Entry Points:[/bold]")
            entry_points_data = query.find_entry_points()
            if entry_points_data:
                for ep in entry_points_data:
                    console.print(f"  • {ep['name']} in {Path(ep['file']).name}")
                    if ep.get("description"):
                        console.print(f"    {ep['description']}")
            else:
                console.print("  None found")

        if show_all or test_coverage:
            console.print("\n[bold]Test Coverage:[/bold]")
            coverage = query.find_test_coverage()
            if coverage:
                total_functions = coverage.get("total_functions", 0)
                total_tests = coverage.get("total_tests", 0)
                tested_modules = coverage.get("tested_modules", [])

                console.print(f"  • Total functions: {total_functions}")
                console.print(f"  • Total tests: {total_tests}")
                if total_functions > 0:
                    ratio = (total_tests / total_functions) * 100
                    console.print(f"  • Test ratio: {ratio:.1f}%")
                console.print(f"  • Tested modules: {len(tested_modules)}")
                for module in tested_modules[:5]:
                    console.print(f"    - {module}")
            else:
                console.print("  No coverage data available")

        if show_all or patterns:
            console.print("\n[bold]Code Patterns:[/bold]")
            patterns_data = query.find_code_patterns()
            if patterns_data:
                for pattern_type, instances in patterns_data.items():
                    if instances:
                        console.print(
                            f"  • {pattern_type.replace('_', ' ').title()}: {len(instances)}"
                        )
                        for instance in instances[:3]:
                            console.print(f"    - {instance['name']}")
            else:
                console.print("  No patterns found")

        if show_all or complexity:
            console.print("\n[bold]Module Complexity:[/bold]")
            complexity_data = query.get_module_complexity()
            if complexity_data:
                console.print("  Top 5 most complex modules:")
                for module in complexity_data[:5]:
                    console.print(f"    • {module['module']}: {module['complexity_score']:.1f}")
                    console.print(
                        f"      Functions: {module['function_count']}, Classes: {module['class_count']}"
                    )
            else:
                console.print("  No complexity data available")

        if deps:
            console.print(f"\n[bold]Dependencies for '{deps}':[/bold]")
            deps_data = query.find_dependencies(deps)

            depends_on = deps_data.get("depends_on", [])
            depended_by = deps_data.get("depended_by", [])

            if depends_on:
                console.print("  Depends on:")
                for dep in depends_on:
                    console.print(f"    • {dep['name']} ({dep['type']})")

            if depended_by:
                console.print("  Depended on by:")
                for dep in depended_by:
                    console.print(f"    • {dep['name']} ({dep['type']})")

            if not depends_on and not depended_by:
                console.print("  No dependencies found")

        query.close()

    except Exception as e:
        console.print(f"[red]Error querying graph: {e}[/red]")
        console.print("[yellow]Make sure you've run 'autodoc graph' first[/yellow]")


@cli.command(name="generate")
@click.option("--output", "-o", default="AUTODOC.md", help="Output file path (default: AUTODOC.md)")
@click.option(
    "--format",
    "output_format",
    default="markdown",
    type=click.Choice(["markdown", "json"]),
    help="Output format (default: markdown)",
)
@click.option(
    "--detailed/--summary",
    default=True,
    help="Generate detailed documentation (default) or summary only",
)
@click.option(
    "--enrich", is_flag=True, help="Automatically enrich entities before generating documentation"
)
@click.option(
    "--inline",
    is_flag=True,
    help="Add enriched docstrings directly to code files (requires --enrich)",
)
def generate(output, output_format, detailed, enrich, inline):
    """Generate comprehensive codebase documentation"""
    # Run async function for enrichment if needed
    if enrich:
        asyncio.run(_generate_with_enrichment_async(output, output_format, detailed, inline))
    else:
        _generate_documentation_only(output, output_format, detailed)


def _generate_documentation_only(output, output_format, detailed):
    """Generate documentation without enrichment."""
    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    console.print("[yellow]Generating comprehensive codebase documentation...[/yellow]")
    summary = autodoc.generate_summary()

    if "error" in summary:
        console.print(f"[red]{summary['error']}[/red]")
        return

    # Handle output format and ensure proper file extension
    if output_format == "json":
        output_content = json.dumps(summary, indent=2, default=str)
        if not output.endswith(".json"):
            output = output.replace(".md", ".json") if output.endswith(".md") else output + ".json"
    else:  # markdown
        output_content = autodoc.format_summary_markdown(summary)
        if not output.endswith(".md"):
            output = output.replace(".json", ".md") if output.endswith(".json") else output + ".md"

    # Always save to file
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write(output_content)
        console.print(f"[green]✅ Documentation generated: {output}[/green]")
        console.print(f"[blue]File size: {len(output_content):,} characters[/blue]")

        # Show preview of what was generated
        overview = summary["overview"]
        console.print("\n[bold]📊 Documentation Summary:[/bold]")
        console.print(
            f"  • {overview['total_functions']} functions across {overview['total_files']} files"
        )
        console.print(f"  • {overview['total_classes']} classes analyzed")
        console.print(f"  • {len(summary.get('feature_map', {}))} feature categories identified")
        console.print(f"  • {len(summary.get('modules', {}))} modules documented")

        # Show build and CI info
        if summary.get("build_system") and summary["build_system"].get("build_tools"):
            console.print(f"  • Build tools: {', '.join(summary['build_system']['build_tools'])}")

        if summary.get("test_system"):
            test_count = summary["test_system"].get("test_functions_count", 0)
            console.print(f"  • {test_count} test functions found")

        if summary.get("ci_configuration") and summary["ci_configuration"].get("has_ci"):
            platforms = summary["ci_configuration"].get("platforms", [])
            console.print(f"  • CI/CD platforms: {', '.join(platforms)}")

    except Exception as e:
        console.print(f"[red]Error saving file: {e}[/red]")


async def _generate_with_enrichment_async(output, output_format, detailed, inline):
    """Generate documentation with automatic enrichment."""
    config = AutodocConfig.load()
    autodoc = SimpleAutodoc(config)
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Check API key
    api_key = config.llm.get_api_key()
    if not api_key and config.llm.provider != "ollama":
        console.print(f"[red]No API key found for {config.llm.provider}[/red]")
        console.print("[yellow]Set via environment variable or .autodoc.yml[/yellow]")
        return

    console.print("[yellow]Enriching entities before generating documentation...[/yellow]")

    # Load cache
    cache = EnrichmentCache()

    # Find entities that need enrichment
    entities_to_enrich = []
    for entity in autodoc.entities:
        cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
        if not cache.get_enrichment(cache_key):
            entities_to_enrich.append(entity)

    if entities_to_enrich:
        console.print(f"[blue]Enriching {len(entities_to_enrich)} entities...[/blue]")

        # Enrich entities
        async with LLMEnricher(config) as enricher:
            try:
                enriched = await enricher.enrich_entities(entities_to_enrich)

                # Cache results
                for enriched_entity in enriched:
                    cache_key = f"{enriched_entity.entity.file_path}:{enriched_entity.entity.name}:{enriched_entity.entity.line_number}"
                    cache.set_enrichment(
                        cache_key,
                        {
                            "description": enriched_entity.description,
                            "purpose": enriched_entity.purpose,
                            "key_features": enriched_entity.key_features,
                            "complexity_notes": enriched_entity.complexity_notes,
                            "usage_examples": enriched_entity.usage_examples,
                            "design_patterns": enriched_entity.design_patterns,
                            "dependencies": enriched_entity.dependencies,
                        },
                    )

                cache.save_cache()
                console.print(f"[green]✅ Enriched {len(enriched)} entities[/green]")

            except Exception as e:
                console.print(f"[red]Error during enrichment: {e}[/red]")
                console.print("[yellow]Continuing with existing enrichments...[/yellow]")
    else:
        console.print("[green]All entities already enriched[/green]")

    # Handle inline enrichment if requested
    if inline:
        console.print("[yellow]Adding enriched docstrings inline to code files...[/yellow]")

        inline_enricher = InlineEnricher(config)
        inline_results = await inline_enricher.enrich_files_inline(
            autodoc.entities, incremental=True, force=False
        )

        total_updated = sum(r.updated_docstrings for r in inline_results)
        console.print(f"[green]✅ Updated {total_updated} docstrings inline[/green]")

    # Generate documentation
    _generate_documentation_only(output, output_format, detailed)


# Backwards compatibility alias
@cli.command(name="generate-summary", hidden=True)
@click.option("--output", "-o", help="Output file path")
@click.option(
    "--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"])
)
def generate_summary_alias(output, output_format):
    """[DEPRECATED] Use 'autodoc generate' instead"""
    console.print(
        "[yellow]⚠️  'generate-summary' is deprecated. Use 'autodoc generate' instead.[/yellow]"
    )
    from click import Context

    ctx = Context(generate)
    return ctx.invoke(
        generate, output=output or "AUTODOC.md", output_format=output_format, detailed=False
    )


@cli.command(name="local-graph")
@click.option("--files", is_flag=True, help="Create file dependency graph")
@click.option("--entities", is_flag=True, help="Create entity network graph")
@click.option("--stats", is_flag=True, help="Show module statistics")
@click.option("--all", "create_all", is_flag=True, help="Create all visualizations")
def local_graph(files, entities, stats, create_all):
    """Create code visualizations without Neo4j (uses local analysis)"""
    if not LOCAL_GRAPH_AVAILABLE:
        console.print("[red]Local graph functionality not available.[/red]")
        console.print("This should not happen - please check the installation.")
        return

    # Default behavior
    if not (files or entities or stats or create_all):
        create_all = True

    try:
        console.print("[yellow]Creating local code graphs...[/yellow]")

        from .local_graph import LocalCodeGraph

        graph = LocalCodeGraph()

        if not graph.entities:
            console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
            return

        created_files = []

        if create_all or files:
            try:
                file1 = graph.create_file_dependency_graph()
                if file1:
                    created_files.append(file1)
            except Exception as e:
                console.print(f"[yellow]Could not create file graph: {e}[/yellow]")

        if create_all or entities:
            try:
                file2 = graph.create_entity_network()
                if file2:
                    created_files.append(file2)
            except Exception as e:
                console.print(f"[yellow]Could not create entity graph: {e}[/yellow]")

        if create_all or stats:
            console.print("")
            graph.create_module_stats()  # Creates module_stats.html

        if created_files:
            console.print(f"\n[green]✅ Created {len(created_files)} visualization files:[/green]")
            for file in created_files:
                console.print(f"  📄 {file}")
            console.print(
                "\n[blue]💡 Open these HTML files in your browser to view interactive graphs![/blue]"
            )

        if not GRAPH_AVAILABLE:
            console.print(
                "\n[yellow]💡 For advanced graph features with Neo4j, install graph dependencies:[/yellow]"
            )
            console.print("   make setup-graph")

    except Exception as e:
        console.print(f"[red]Error creating local graphs: {e}[/red]")


@cli.command()
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("--port", default=8080, type=int, help="Port to bind to")
@click.option("--load-cache", is_flag=True, help="Load existing cache on startup")
def serve(host, port, load_cache):
    """Start the API server for node connections and graph queries"""
    try:
        from .api_server import APIServer

        console.print(f"[blue]Starting Autodoc API server on {host}:{port}[/blue]")

        # Create server instance
        server = APIServer(host=host, port=port)

        # Load existing cache if requested
        if load_cache:
            console.print("[yellow]Loading existing cache...[/yellow]")
            if server.autodoc:
                server.autodoc.load()
                console.print(f"[green]Loaded {len(server.autodoc.entities)} entities[/green]")

        console.print("\n[bold green]🚀 Server starting...[/bold green]")
        console.print(f"[blue]Health check: http://{host}:{port}/health[/blue]")
        console.print("[blue]API docs: Available endpoints at /api/*[/blue]")
        console.print("\n[yellow]Available endpoints:[/yellow]")
        console.print("  • GET /health - Health check")
        console.print("  • POST /api/nodes/analyze - Analyze codebase")
        console.print("  • GET /api/nodes - List nodes/entities")
        console.print("  • POST /api/relationships - Create relationships")
        console.print("  • GET /api/relationships - List relationships")
        console.print("  • POST /api/search - Search entities")
        console.print("  • GET /api/entities/internal - Internal entities")
        console.print("  • GET /api/entities/external - External entities")
        console.print("  • GET /api/entities/endpoints - API endpoints")
        console.print("  • GET /api/graph/stats - Graph statistics")
        console.print("\n[dim]Press Ctrl+C to stop the server[/dim]")

        # Run the server
        server.run()

    except ImportError as e:
        console.print(f"[red]Error: Missing dependencies for API server: {e}[/red]")
        console.print(
            "[yellow]Install with: pip install 'aiohttp>=3.9.1' 'aiohttp-cors>=0.7.0'[/yellow]"
        )
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")


# =============================================================================
# Context Pack Commands
# =============================================================================


@cli.group()
def pack():
    """Manage context packs for feature-based code grouping.

    Context packs group related code entities (functions, classes, modules)
    for easier navigation and understanding.

    Examples:
      autodoc pack list                    # List all configured packs
      autodoc pack info authentication     # Show details for a pack
      autodoc pack build authentication    # Build/index a specific pack
      autodoc pack query auth "login flow" # Search within a pack
    """
    pass


@pack.command("list")
@click.option("--tag", "-t", help="Filter packs by tag")
@click.option("--security", "-s", type=click.Choice(["critical", "high", "normal"]),
              help="Filter by security level")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def pack_list(tag, security, as_json):
    """List all configured context packs."""
    config = AutodocConfig.load()

    packs = config.context_packs
    if not packs:
        if as_json:
            console.print("[]")
        else:
            console.print("[yellow]No context packs configured.[/yellow]")
            console.print("\nAdd packs to your autodoc.yaml:")
            example = """[dim]context_packs:
  - name: authentication
    display_name: Authentication System
    description: User auth and session management
    files:
      - src/auth/**/*.py
    security_level: critical[/dim]"""
            console.print(example)
        return

    # Apply filters
    if tag:
        packs = [p for p in packs if tag in p.tags]
    if security:
        packs = [p for p in packs if p.security_level == security]

    if as_json:
        output = [p.model_dump() for p in packs]
        console.print(json.dumps(output, indent=2))
        return

    # Rich table output
    table = Table(title="Context Packs")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name", style="white")
    table.add_column("Files", style="dim")
    table.add_column("Tables", style="dim")
    table.add_column("Dependencies", style="yellow")
    table.add_column("Security", style="red")
    table.add_column("Tags", style="green")

    for p in packs:
        security_badge = {
            "critical": "🔴 critical",
            "high": "🟠 high",
            "normal": "🟢 normal",
        }.get(p.security_level or "", "")

        table.add_row(
            p.name,
            p.display_name,
            str(len(p.files)),
            str(len(p.tables)),
            ", ".join(p.dependencies) or "-",
            security_badge,
            ", ".join(p.tags) or "-",
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(packs)} packs[/dim]")


@pack.command("info")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--deps", is_flag=True, help="Show resolved dependencies")
def pack_info(name, as_json, deps):
    """Show detailed information about a context pack."""
    config = AutodocConfig.load()
    pack_config = config.get_pack(name)

    if not pack_config:
        console.print(f"[red]Pack '{name}' not found.[/red]")
        if config.context_packs:
            console.print(f"Available packs: {', '.join(p.name for p in config.context_packs)}")
        return

    if as_json:
        output = pack_config.model_dump()
        if deps:
            resolved = config.resolve_pack_dependencies(name)
            output["resolved_dependencies"] = [p.name for p in resolved if p.name != name]
        console.print(json.dumps(output, indent=2))
        return

    # Rich output
    console.print(f"\n[bold cyan]{pack_config.display_name}[/bold cyan]")
    console.print(f"[dim]({pack_config.name})[/dim]\n")
    console.print(f"{pack_config.description}\n")

    if pack_config.security_level:
        badge = {
            "critical": "[red bold]🔴 CRITICAL SECURITY[/red bold]",
            "high": "[yellow bold]🟠 HIGH SECURITY[/yellow bold]",
            "normal": "[green]🟢 Normal[/green]",
        }.get(pack_config.security_level, "")
        console.print(f"Security Level: {badge}\n")

    console.print("[bold]File Patterns:[/bold]")
    for pattern in pack_config.files:
        console.print(f"  • {pattern}")

    if pack_config.tables:
        console.print("\n[bold]Database Tables:[/bold]")
        for table in pack_config.tables:
            console.print(f"  • {table}")

    if pack_config.dependencies:
        console.print("\n[bold]Direct Dependencies:[/bold]")
        for dep in pack_config.dependencies:
            console.print(f"  → {dep}")

    if deps:
        resolved = config.resolve_pack_dependencies(name)
        if len(resolved) > 1:
            console.print("\n[bold]Full Dependency Chain:[/bold]")
            for i, p in enumerate(resolved):
                if p.name != name:
                    console.print(f"  {i+1}. {p.name} ({p.display_name})")

    if pack_config.tags:
        console.print(f"\n[bold]Tags:[/bold] {', '.join(pack_config.tags)}")


@pack.command("build")
@click.argument("name")
@click.option("--all", "build_all", is_flag=True, help="Build all packs")
@click.option("--output", "-o", type=click.Path(), help="Output directory for pack data")
@click.option("--embeddings", "-e", is_flag=True, help="Create ChromaDB embeddings for semantic search")
def pack_build(name, build_all, output, embeddings):
    """Build/index a context pack for searching.

    This matches files to the pack's patterns and creates embeddings
    for semantic search within the pack.
    """
    import asyncio
    import fnmatch
    from pathlib import Path as PathLib

    config = AutodocConfig.load()

    if build_all:
        packs_to_build = config.context_packs
    else:
        pack_config = config.get_pack(name)
        if not pack_config:
            console.print(f"[red]Pack '{name}' not found.[/red]")
            return
        packs_to_build = [pack_config]

    if not packs_to_build:
        console.print("[yellow]No packs to build.[/yellow]")
        return

    output_dir = PathLib(output) if output else PathLib(".autodoc/packs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize ChromaDB embedder if requested
    chromadb_embedder = None
    if embeddings:
        try:
            from .chromadb_embedder import ChromaDBEmbedder
            console.print("[dim]Initializing ChromaDB for pack embeddings...[/dim]")
        except ImportError:
            console.print("[yellow]ChromaDB not available. Install with: pip install chromadb[/yellow]")
            embeddings = False

    for pack_config in packs_to_build:
        console.print(f"\n[bold]Building pack: {pack_config.display_name}[/bold]")

        # Find matching files
        matched_files = []
        base_path = PathLib.cwd()

        for pattern in pack_config.files:
            # Handle glob patterns
            if "**" in pattern:
                matched = list(base_path.glob(pattern))
            else:
                matched = list(base_path.glob(pattern))
            matched_files.extend(matched)

        # Deduplicate
        matched_files = list(set(matched_files))
        console.print(f"  Found {len(matched_files)} matching files")

        # Load cache to get entities
        cache_file = PathLib("autodoc_cache.json")
        entities_in_pack = []
        code_entities = []

        if cache_file.exists():
            with open(cache_file) as f:
                cache_data = json.load(f)
                all_entities = cache_data.get("entities", [])

                for entity in all_entities:
                    entity_file = PathLib(entity.get("file", ""))
                    # Check if entity's file matches any pack pattern
                    for pattern in pack_config.files:
                        try:
                            if entity_file.match(pattern) or fnmatch.fnmatch(
                                str(entity_file), pattern
                            ):
                                entities_in_pack.append(entity)
                                # Create CodeEntity for embeddings
                                if embeddings:
                                    from .analyzer import CodeEntity
                                    code_entity = CodeEntity(
                                        type=entity.get("entity_type", "function"),
                                        name=entity.get("name", "unknown"),
                                        file_path=entity.get("file", ""),
                                        line_number=entity.get("start_line", 0),
                                        docstring=entity.get("docstring"),
                                        code=entity.get("code", ""),
                                    )
                                    code_entities.append(code_entity)
                                break
                        except Exception:
                            pass

            console.print(f"  Found {len(entities_in_pack)} entities in pack")

        # Create ChromaDB embeddings for this pack
        if embeddings and code_entities:
            from .chromadb_embedder import ChromaDBEmbedder
            collection_name = f"autodoc_pack_{pack_config.name}"
            persist_dir = str(output_dir / f"{pack_config.name}_chromadb")

            chromadb_embedder = ChromaDBEmbedder(
                collection_name=collection_name,
                persist_directory=persist_dir,
                embedding_model=config.embeddings.chromadb_model,
            )
            # Clear existing and re-embed
            chromadb_embedder.clear_collection()

            console.print(f"  [dim]Creating embeddings for {len(code_entities)} entities...[/dim]")
            embedded_count = asyncio.get_event_loop().run_until_complete(
                chromadb_embedder.embed_entities(code_entities, use_enrichment=True)
            )
            console.print(f"  [green]✓ Created {embedded_count} embeddings in {persist_dir}[/green]")

        # Save pack data
        pack_data = {
            "name": pack_config.name,
            "display_name": pack_config.display_name,
            "description": pack_config.description,
            "files": [str(f) for f in matched_files],
            "entities": entities_in_pack,
            "tables": pack_config.tables,
            "dependencies": pack_config.dependencies,
            "security_level": pack_config.security_level,
            "tags": pack_config.tags,
            "has_embeddings": embeddings and len(code_entities) > 0,
        }

        pack_file = output_dir / f"{pack_config.name}.json"
        with open(pack_file, "w") as f:
            json.dump(pack_data, f, indent=2)

        console.print(f"  [green]✓ Saved to {pack_file}[/green]")

    console.print(f"\n[green]Built {len(packs_to_build)} pack(s)[/green]")


@pack.command("query")
@click.argument("name")
@click.argument("query")
@click.option("--limit", "-n", default=5, help="Number of results")
@click.option("--keyword", "-k", is_flag=True, help="Force keyword search instead of semantic")
def pack_query(name, query, limit, keyword):
    """Search within a context pack using semantic search.

    If the pack was built with --embeddings, uses ChromaDB semantic search.
    Otherwise, falls back to keyword matching.
    """
    import asyncio
    from pathlib import Path as PathLib

    config = AutodocConfig.load()
    pack_config = config.get_pack(name)

    if not pack_config:
        console.print(f"[red]Pack '{name}' not found.[/red]")
        return

    pack_file = PathLib(f".autodoc/packs/{name}.json")
    if not pack_file.exists():
        console.print(f"[yellow]Pack '{name}' not built yet. Run: autodoc pack build {name}[/yellow]")
        return

    with open(pack_file) as f:
        pack_data = json.load(f)

    entities = pack_data.get("entities", [])
    if not entities:
        console.print("[yellow]No entities in this pack.[/yellow]")
        return

    # Try semantic search with ChromaDB if available
    use_semantic = pack_data.get("has_embeddings", False) and not keyword
    results = []

    if use_semantic:
        chromadb_dir = PathLib(f".autodoc/packs/{name}_chromadb")
        if chromadb_dir.exists():
            try:
                from .chromadb_embedder import ChromaDBEmbedder
                collection_name = f"autodoc_pack_{name}"

                embedder = ChromaDBEmbedder(
                    collection_name=collection_name,
                    persist_directory=str(chromadb_dir),
                    embedding_model=config.embeddings.chromadb_model,
                )

                console.print("[dim]Using semantic search...[/dim]")
                search_results = asyncio.get_event_loop().run_until_complete(
                    embedder.search(query, limit=limit)
                )

                for r in search_results:
                    entity_data = {
                        "entity_type": r["entity"]["type"],
                        "name": r["entity"]["name"],
                        "file": r["entity"]["file_path"],
                        "start_line": r["entity"]["line_number"],
                        "description": r.get("document", "")[:200],
                    }
                    results.append((entity_data, r["similarity"]))

            except Exception as e:
                console.print(f"[yellow]Semantic search unavailable: {e}. Falling back to keyword search.[/yellow]")
                use_semantic = False

    # Fall back to keyword search
    if not use_semantic:
        console.print("[dim]Using keyword search...[/dim]")
        query_lower = query.lower()

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

            # Check for partial matches
            for word in query_lower.split():
                if word in name_str:
                    score += 2
                if word in desc:
                    score += 1

            if score > 0:
                results.append((entity, score / 20.0))  # Normalize to ~0-1 range

        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:limit]

    if not results:
        console.print(f"[yellow]No results found for '{query}' in pack '{name}'[/yellow]")
        return

    search_type = "semantic" if use_semantic else "keyword"
    console.print(f"\n[bold]Results for '{query}' in {pack_config.display_name} ({search_type}):[/bold]\n")

    for entity, score in results:
        etype = entity.get("entity_type", "unknown")
        ename = entity.get("name", "unknown")
        efile = PathLib(entity.get("file", "")).name
        line = entity.get("start_line", "?")
        similarity = f"{score:.2f}" if use_semantic else f"{score:.1f}"

        console.print(f"[cyan]{etype}[/cyan] [bold]{ename}[/bold] [dim](score: {similarity})[/dim]")
        console.print(f"  [dim]{efile}:{line}[/dim]")
        if entity.get("description"):
            desc_text = entity['description'][:100]
            console.print(f"  {desc_text}...")
        console.print()


def main():
    cli()


if __name__ == "__main__":
    main()
