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
from .config import AutodocConfig, ContextPackConfig
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

            embedder = ChromaDBEmbedder(persist_directory=config.embeddings.persist_directory)
            stats = embedder.get_stats()
            console.print("✅ ChromaDB configured")
            console.print(f"   Model: {config.embeddings.chromadb_model}")
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
@click.option(
    "--security",
    "-s",
    type=click.Choice(["critical", "high", "normal"]),
    help="Filter by security level",
)
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
                    console.print(f"  {i + 1}. {p.name} ({p.display_name})")

    if pack_config.tags:
        console.print(f"\n[bold]Tags:[/bold] {', '.join(pack_config.tags)}")


@pack.command("build")
@click.argument("name")
@click.option("--all", "build_all", is_flag=True, help="Build all packs")
@click.option("--output", "-o", type=click.Path(), help="Output directory for pack data")
@click.option(
    "--embeddings", "-e", is_flag=True, help="Create ChromaDB embeddings for semantic search"
)
@click.option("--summary", "-s", is_flag=True, help="Generate LLM summary for each pack")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be processed without making API calls"
)
@click.option("--no-cache", is_flag=True, help="Force regeneration of LLM summaries (ignore cache)")
def pack_build(name, build_all, output, embeddings, summary, dry_run, no_cache):
    """Build/index a context pack for searching.

    This matches files to the pack's patterns and creates embeddings
    for semantic search within the pack.

    Use --dry-run to preview what would be processed and estimated costs.
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
            console.print(
                "[yellow]ChromaDB not available. Install with: pip install chromadb[/yellow]"
            )
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

                def matches_pattern(file_path: str, pattern: str) -> bool:
                    """Check if a file path matches a glob pattern."""
                    # Normalize paths - handle both absolute and relative
                    file_path_obj = PathLib(file_path)
                    file_str = str(file_path_obj)

                    # Try multiple matching strategies
                    try:
                        # 1. Direct fnmatch (handles ** patterns)
                        if fnmatch.fnmatch(file_str, pattern):
                            return True

                        # 2. PathLib.match (matches from the right)
                        if file_path_obj.match(pattern):
                            return True

                        # 3. Try matching just the relative part after common prefixes
                        # Handle cases where cache has relative paths but pattern has same structure
                        pattern_parts = pattern.replace("**", "").replace("*", "").strip("/")
                        if pattern_parts and pattern_parts in file_str:
                            # Pattern base directory is in file path
                            if fnmatch.fnmatch(file_str, f"*{pattern}"):
                                return True
                            if fnmatch.fnmatch(file_str, f"**/{pattern}"):
                                return True

                        # 4. Handle glob patterns by checking if file is under the pattern's directory
                        if "**" in pattern:
                            base_pattern = pattern.split("**")[0].rstrip("/")
                            if base_pattern and base_pattern in file_str:
                                # File is under the base directory
                                suffix = pattern.split("**")[-1].lstrip("/")
                                if not suffix or fnmatch.fnmatch(file_str, f"*{suffix}"):
                                    return True

                    except Exception:
                        pass

                    return False

                for entity in all_entities:
                    # Handle both 'file_path' (new format) and 'file' (old format)
                    entity_file = entity.get("file_path", entity.get("file", ""))
                    # Check if entity's file matches any pack pattern
                    for pattern in pack_config.files:
                        if matches_pattern(entity_file, pattern):
                            entities_in_pack.append(entity)
                            # Create CodeEntity for embeddings
                            if embeddings:
                                from .analyzer import CodeEntity

                                code_entity = CodeEntity(
                                    type=entity.get("entity_type", "function"),
                                    name=entity.get("name", "unknown"),
                                    file_path=entity_file,
                                    line_number=entity.get("start_line", 0),
                                    docstring=entity.get("docstring"),
                                    code=entity.get("code", ""),
                                )
                                code_entities.append(code_entity)
                            break

            console.print(f"  Found {len(entities_in_pack)} entities in pack")

        # Dry run mode - show what would be processed without making API calls
        if dry_run:
            console.print("\n  [cyan]DRY RUN - No changes will be made[/cyan]")
            console.print(f"  • Files to index: {len(matched_files)}")
            console.print(f"  • Entities to embed: {len(entities_in_pack)}")

            if embeddings:
                console.print(
                    f"  • Embeddings: Would create ChromaDB collection 'autodoc_pack_{pack_config.name}'"
                )
                console.print("    [dim](Uses local sentence-transformers - no API cost)[/dim]")

            if summary:
                # Estimate tokens for LLM summary
                # Rough estimate: pack info + entity names/docstrings
                entity_text = ""
                for e in entities_in_pack[:50]:  # Sample first 50
                    docstring = e.get("docstring") or ""  # Handle None docstrings
                    entity_text += f"{e.get('name', '')} {docstring[:100]} "
                estimated_input_tokens = len(entity_text.split()) * 2  # Rough token estimate
                estimated_input_tokens += 500  # System prompt overhead

                console.print(
                    f"  • LLM Summary: Would call {config.llm.provider}/{config.llm.model}"
                )
                console.print(f"    [dim]Estimated input tokens: ~{estimated_input_tokens}[/dim]")

                # Cost warnings for large packs
                if len(entities_in_pack) > 100:
                    console.print(
                        f"    [yellow]⚠ Large pack ({len(entities_in_pack)} entities) - consider using a smaller model[/yellow]"
                    )
                    console.print(
                        "    [dim]Tip: Configure llm.model in autodoc.yaml (e.g., claude-3-haiku-20240307, gpt-4o-mini)[/dim]"
                    )

            continue  # Skip to next pack in dry-run mode

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
            console.print(
                f"  [green]✓ Created {embedded_count} embeddings in {persist_dir}[/green]"
            )

        # Generate LLM summary if requested
        llm_summary = None
        if summary:
            try:
                from .enrichment import LLMEnricher, PackSummaryCache

                # Check cache first (unless --no-cache)
                summary_cache = PackSummaryCache()
                file_paths = [str(f) for f in matched_files]
                cached_summary = None
                if not no_cache:
                    cached_summary = summary_cache.get_summary(
                        pack_config.name, entities_in_pack, file_paths
                    )

                if cached_summary:
                    llm_summary = cached_summary
                    console.print("  [green]✓ Using cached LLM summary (content unchanged)[/green]")
                else:
                    console.print("  [dim]Generating LLM summary...[/dim]")

                    async def generate_summary():
                        async with LLMEnricher(config) as enricher:
                            result = await enricher.generate_pack_summary(
                                pack_name=pack_config.name,
                                pack_display_name=pack_config.display_name,
                                pack_description=pack_config.description,
                                entities=entities_in_pack,
                                files=file_paths,
                                tables=pack_config.tables,
                                dependencies=pack_config.dependencies,
                            )
                            # Return both the summary and token usage
                            return result, enricher.get_token_usage()

                    llm_summary, token_usage = asyncio.get_event_loop().run_until_complete(
                        generate_summary()
                    )
                    if llm_summary:
                        console.print("  [green]✓ Generated LLM summary[/green]")
                        # Display token usage
                        if token_usage.get("total_tokens", 0) > 0:
                            console.print(
                                f"    [dim]Tokens used: {token_usage['input_tokens']} input + "
                                f"{token_usage['output_tokens']} output = {token_usage['total_tokens']} total[/dim]"
                            )
                        # Cache the summary
                        summary_cache.set_summary(
                            pack_config.name, llm_summary, entities_in_pack, file_paths
                        )
                        summary_cache.save_cache()
                    else:
                        console.print(
                            "  [yellow]⚠ LLM summary generation failed (check API key)[/yellow]"
                        )
            except Exception as e:
                console.print(f"  [yellow]⚠ Error generating summary: {e}[/yellow]")

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
            "llm_summary": llm_summary,
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
@click.option(
    "--json", "output_json", is_flag=True, help="Output results as JSON for programmatic use"
)
def pack_query(name, query, limit, keyword, output_json):
    """Search within a context pack using semantic search.

    If the pack was built with --embeddings, uses ChromaDB semantic search.
    Otherwise, falls back to keyword matching.

    Use --json for programmatic output: {query, pack, search_type, results: [...]}
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
        console.print(
            f"[yellow]Pack '{name}' not built yet. Run: autodoc pack build {name}[/yellow]"
        )
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
                console.print(
                    f"[yellow]Semantic search unavailable: {e}. Falling back to keyword search.[/yellow]"
                )
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

    search_type = "semantic" if use_semantic else "keyword"

    if not results:
        if output_json:
            print(
                json.dumps(
                    {
                        "query": query,
                        "pack": name,
                        "search_type": search_type,
                        "results": [],
                        "total": 0,
                    }
                )
            )
        else:
            console.print(f"[yellow]No results found for '{query}' in pack '{name}'[/yellow]")
        return

    # JSON output mode for programmatic use
    if output_json:
        json_results = []
        for entity, score in results:
            json_results.append(
                {
                    "type": entity.get("entity_type", "unknown"),
                    "name": entity.get("name", "unknown"),
                    "file": entity.get("file", ""),
                    "line": entity.get("start_line", 0),
                    "score": round(score, 3),
                    "preview": (entity.get("description") or entity.get("docstring") or "")[:200],
                }
            )
        output = {
            "query": query,
            "pack": name,
            "search_type": search_type,
            "results": json_results,
            "total": len(json_results),
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    console.print(
        f"\n[bold]Results for '{query}' in {pack_config.display_name} ({search_type}):[/bold]\n"
    )

    for entity, score in results:
        etype = entity.get("entity_type", "unknown")
        ename = entity.get("name", "unknown")
        efile = PathLib(entity.get("file", "")).name
        line = entity.get("start_line", "?")
        similarity = f"{score:.2f}" if use_semantic else f"{score:.1f}"

        console.print(f"[cyan]{etype}[/cyan] [bold]{ename}[/bold] [dim](score: {similarity})[/dim]")
        console.print(f"  [dim]{efile}:{line}[/dim]")
        if entity.get("description"):
            desc_text = entity["description"][:100]
            console.print(f"  {desc_text}...")
        console.print()


@pack.command("auto-generate")
@click.option("--save", is_flag=True, help="Save generated packs to autodoc.yaml")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for programmatic use")
@click.option("--min-files", default=3, help="Minimum files for a pack (default: 3)")
@click.option(
    "--root",
    "root_path",
    type=click.Path(exists=True),
    help="Root directory to scan (default: current directory)",
)
def pack_auto_generate(save, output_json, min_files, root_path):
    """Automatically detect and suggest context packs based on codebase structure.

    Analyzes your codebase to detect:
    - Common directory patterns (src/, api/, tests/, models/, etc.)
    - Language markers (setup.py, package.json, go.mod, Cargo.toml)
    - Framework patterns (Django apps, FastAPI routers, React components)

    Use --save to append suggested packs to autodoc.yaml.
    Use --json for programmatic output (e.g., Temporal workflows).
    Use --root to specify a different base directory (useful in Docker/CI).
    """
    from pathlib import Path as PathLib

    config = AutodocConfig.load()
    base_path = PathLib(root_path) if root_path else PathLib.cwd()
    suggested_packs = []

    # Known pack patterns to detect
    pack_patterns = [
        # Standard code organization
        {
            "pattern": "src/**/*.py",
            "name": "source",
            "display": "Source Code",
            "desc": "Main source code",
            "tags": ["core"],
        },
        {
            "pattern": "api/**/*.py",
            "name": "api",
            "display": "API Layer",
            "desc": "API endpoints and routes",
            "tags": ["api"],
        },
        {
            "pattern": "tests/**/*.py",
            "name": "tests",
            "display": "Test Suite",
            "desc": "Test files and fixtures",
            "tags": ["tests"],
        },
        {
            "pattern": "lib/**/*.py",
            "name": "lib",
            "display": "Library Code",
            "desc": "Shared library code",
            "tags": ["core"],
        },
        {
            "pattern": "utils/**/*.py",
            "name": "utils",
            "display": "Utilities",
            "desc": "Utility functions and helpers",
            "tags": ["utilities"],
        },
        {
            "pattern": "models/**/*.py",
            "name": "models",
            "display": "Data Models",
            "desc": "Data models and schemas",
            "tags": ["data"],
        },
        {
            "pattern": "services/**/*.py",
            "name": "services",
            "display": "Services",
            "desc": "Business logic services",
            "tags": ["core"],
        },
        {
            "pattern": "controllers/**/*.py",
            "name": "controllers",
            "display": "Controllers",
            "desc": "Request handlers and controllers",
            "tags": ["api"],
        },
        {
            "pattern": "routes/**/*.py",
            "name": "routes",
            "display": "Routes",
            "desc": "API route definitions",
            "tags": ["api"],
        },
        {
            "pattern": "middleware/**/*.py",
            "name": "middleware",
            "display": "Middleware",
            "desc": "Request/response middleware",
            "tags": ["api"],
        },
        {
            "pattern": "tasks/**/*.py",
            "name": "tasks",
            "display": "Background Tasks",
            "desc": "Async tasks and jobs",
            "tags": ["async"],
        },
        {
            "pattern": "workers/**/*.py",
            "name": "workers",
            "display": "Workers",
            "desc": "Background workers and processors",
            "tags": ["async"],
        },
        {
            "pattern": "migrations/**/*.py",
            "name": "migrations",
            "display": "Database Migrations",
            "desc": "Database migration files",
            "tags": ["database"],
        },
        {
            "pattern": "config/**/*.py",
            "name": "config",
            "display": "Configuration",
            "desc": "Configuration modules",
            "tags": ["config"],
        },
        {
            "pattern": "scripts/**/*.py",
            "name": "scripts",
            "display": "Scripts",
            "desc": "Utility and automation scripts",
            "tags": ["tools"],
        },
        {
            "pattern": "cli/**/*.py",
            "name": "cli",
            "display": "CLI Commands",
            "desc": "Command-line interface",
            "tags": ["cli"],
        },
        # TypeScript/JavaScript
        {
            "pattern": "src/**/*.ts",
            "name": "source-ts",
            "display": "TypeScript Source",
            "desc": "TypeScript source code",
            "tags": ["core"],
        },
        {
            "pattern": "src/**/*.tsx",
            "name": "react-components",
            "display": "React Components",
            "desc": "React component files",
            "tags": ["frontend", "ui"],
        },
        {
            "pattern": "components/**/*.tsx",
            "name": "components",
            "display": "UI Components",
            "desc": "React/Vue/Svelte components",
            "tags": ["frontend", "ui"],
        },
        {
            "pattern": "pages/**/*.tsx",
            "name": "pages",
            "display": "Pages",
            "desc": "Page components",
            "tags": ["frontend"],
        },
        {
            "pattern": "hooks/**/*.ts",
            "name": "hooks",
            "display": "React Hooks",
            "desc": "Custom React hooks",
            "tags": ["frontend"],
        },
        {
            "pattern": "store/**/*.ts",
            "name": "store",
            "display": "State Store",
            "desc": "State management",
            "tags": ["frontend"],
        },
    ]

    # Framework-specific patterns (reserved for future use)
    _framework_patterns = [
        # Django
        {
            "marker": "**/models.py",
            "adjacent": "**/views.py",
            "name_suffix": "-app",
            "framework": "django",
            "tags": ["django"],
        },
        {
            "marker": "**/admin.py",
            "name_suffix": "-admin",
            "display_suffix": "Admin",
            "framework": "django",
            "tags": ["django", "admin"],
        },
        # FastAPI
        {
            "marker": "**/routers/**/*.py",
            "name": "fastapi-routers",
            "display": "FastAPI Routers",
            "framework": "fastapi",
            "tags": ["fastapi", "api"],
        },
        # React
        {
            "marker": "src/components/**/*.tsx",
            "name": "react-components",
            "display": "React Components",
            "framework": "react",
            "tags": ["react", "frontend"],
        },
    ]

    # Detect language from markers
    detected_language = None
    language_markers = [
        ("setup.py", "python"),
        ("pyproject.toml", "python"),
        ("requirements.txt", "python"),
        ("package.json", "javascript"),
        ("tsconfig.json", "typescript"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("pom.xml", "java"),
        ("build.gradle", "java"),
    ]

    for marker, lang in language_markers:
        if (base_path / marker).exists():
            detected_language = lang
            break

    if not output_json:
        console.print("[bold]Scanning codebase for pack suggestions...[/bold]")
        if detected_language:
            console.print(f"[dim]Detected language: {detected_language}[/dim]\n")

    # Filter patterns by detected language (reserved for future use)
    _language_extensions = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "go": [".go"],
        "rust": [".rs"],
        "java": [".java"],
    }

    # Check each pattern
    existing_pack_names = {p.name for p in config.context_packs}

    for pack_info in pack_patterns:
        pattern = pack_info["pattern"]

        # Count matching files
        matching_files = list(base_path.glob(pattern))

        if len(matching_files) >= min_files:
            # Skip if pack already exists
            if pack_info["name"] in existing_pack_names:
                continue

            suggested_packs.append(
                {
                    "name": pack_info["name"],
                    "display_name": pack_info["display"],
                    "description": pack_info["desc"],
                    "files": [pattern],
                    "file_count": len(matching_files),
                    "tags": pack_info.get("tags", []),
                    "tables": [],
                    "dependencies": [],
                }
            )

    # Detect Django apps (directories with models.py)
    for models_file in base_path.glob("**/models.py"):
        app_dir = models_file.parent
        app_name = app_dir.name.lower()

        # Skip common non-app directories
        if app_name in ["migrations", "tests", "test", "__pycache__"]:
            continue

        # Check if it looks like a Django app
        has_views = (app_dir / "views.py").exists()
        has_urls = (app_dir / "urls.py").exists()

        if (has_views or has_urls) and app_name not in existing_pack_names:
            # Count Python files in this app
            py_files = list(app_dir.glob("**/*.py"))
            if len(py_files) >= min_files:
                suggested_packs.append(
                    {
                        "name": app_name,
                        "display_name": f"{app_name.replace('_', ' ').title()} App",
                        "description": f"Django app for {app_name.replace('_', ' ')}",
                        "files": [f"{app_dir.relative_to(base_path)}/**/*.py"],
                        "file_count": len(py_files),
                        "tags": ["django", "app"],
                        "tables": [],
                        "dependencies": [],
                    }
                )

    if not suggested_packs:
        if output_json:
            print(json.dumps({"suggested_packs": [], "total": 0, "language": detected_language}))
        else:
            console.print(
                "[yellow]No pack suggestions found. Your codebase may need custom pack definitions.[/yellow]"
            )
            console.print("[dim]Define packs in autodoc.yaml under 'context_packs:'[/dim]")
        return

    # Remove duplicates by name
    seen_names = set()
    unique_packs = []
    for pack in suggested_packs:
        if pack["name"] not in seen_names:
            seen_names.add(pack["name"])
            unique_packs.append(pack)
    suggested_packs = unique_packs

    # JSON output mode
    if output_json:
        output = {
            "suggested_packs": suggested_packs,
            "total": len(suggested_packs),
            "language": detected_language,
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    console.print(f"[bold green]Found {len(suggested_packs)} suggested pack(s):[/bold green]\n")

    for pack in suggested_packs:
        tags_str = ", ".join(pack["tags"]) if pack["tags"] else "none"
        console.print(f"[cyan]{pack['name']}[/cyan]: {pack['display_name']}")
        console.print(f"  [dim]Files: {pack['files'][0]} ({pack['file_count']} files)[/dim]")
        console.print(f"  [dim]Description: {pack['description']}[/dim]")
        console.print(f"  [dim]Tags: {tags_str}[/dim]")
        console.print()

    # Save to config if requested
    if save:
        config_path = PathLib.cwd() / "autodoc.yaml"
        if not config_path.exists():
            config_path = PathLib.cwd() / ".autodoc.yaml"
            if not config_path.exists():
                config_path = PathLib.cwd() / "autodoc.yaml"

        # Create ContextPackConfig objects
        new_packs = []
        for pack in suggested_packs:
            new_pack = ContextPackConfig(
                name=pack["name"],
                display_name=pack["display_name"],
                description=pack["description"],
                files=pack["files"],
                tags=pack["tags"],
                tables=[],
                dependencies=[],
            )
            new_packs.append(new_pack)

        # Add to config
        config.context_packs.extend(new_packs)
        config.save(config_path)
        console.print(f"[green]✓ Saved {len(new_packs)} pack(s) to {config_path}[/green]")
        console.print("[dim]Run 'autodoc pack list' to see all packs[/dim]")
    else:
        console.print("[dim]Use --save to add these packs to your autodoc.yaml[/dim]")


# =============================================================================
# Impact Analysis Command
# =============================================================================


@cli.command("impact")
@click.argument("files", nargs=-1, required=True)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for programmatic use")
@click.option("--pack", "-p", multiple=True, help="Limit analysis to specific packs")
def impact_analysis(files, output_json, pack):
    """Analyze the impact of file changes on context packs.

    Given a list of changed files, shows which packs and entities might be affected.
    Useful for CI/CD pipelines to understand change scope.

    Examples:
        autodoc impact src/auth/login.py
        autodoc impact src/auth/*.py --json
        autodoc impact $(git diff --name-only HEAD~1) --pack authentication
    """
    import fnmatch
    from pathlib import Path as PathLib

    config = AutodocConfig.load()

    if not config.context_packs:
        if output_json:
            print(json.dumps({"error": "No context packs configured", "affected_packs": []}))
        else:
            console.print(
                "[yellow]No context packs configured. Run 'autodoc pack auto-generate --save' first.[/yellow]"
            )
        return

    # Normalize file paths
    changed_files = [str(PathLib(f).resolve()) for f in files]
    base_path = PathLib.cwd()

    # Filter packs if specified
    packs_to_analyze = config.context_packs
    if pack:
        packs_to_analyze = [p for p in config.context_packs if p.name in pack]
        if not packs_to_analyze:
            if output_json:
                print(json.dumps({"error": f"Packs not found: {list(pack)}", "affected_packs": []}))
            else:
                console.print(f"[red]Packs not found: {list(pack)}[/red]")
            return

    affected_packs = []

    for pack_config in packs_to_analyze:
        # Check if any changed file matches this pack's patterns
        matching_files = []
        for changed_file in changed_files:
            for pattern in pack_config.files:
                # Try multiple matching strategies
                try:
                    file_path = PathLib(changed_file)
                    # Relative path matching
                    try:
                        rel_path = file_path.relative_to(base_path)
                        if fnmatch.fnmatch(str(rel_path), pattern):
                            matching_files.append(str(rel_path))
                            break
                    except ValueError:
                        pass
                    # Absolute path matching
                    if fnmatch.fnmatch(str(file_path), f"*{pattern}"):
                        matching_files.append(changed_file)
                        break
                    # PathLib.match
                    if file_path.match(pattern):
                        matching_files.append(changed_file)
                        break
                except Exception:
                    pass

        if matching_files:
            # Load pack data to find affected entities
            pack_file = PathLib(f".autodoc/packs/{pack_config.name}.json")
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
                                        "line": entity.get("start_line", 0),
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

    # JSON output
    if output_json:
        output = {
            "changed_files": list(files),
            "affected_packs": affected_packs,
            "total_packs_affected": len(affected_packs),
            "total_entities_affected": sum(p["entity_count"] for p in affected_packs),
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    if not affected_packs:
        console.print("[green]No context packs affected by these changes.[/green]")
        return

    console.print(f"\n[bold]Impact Analysis for {len(files)} changed file(s):[/bold]\n")

    for pack_info in affected_packs:
        security_badge = ""
        if pack_info["security_level"] == "critical":
            security_badge = " [red]⚠ CRITICAL[/red]"
        elif pack_info["security_level"] == "high":
            security_badge = " [yellow]⚠ HIGH[/yellow]"

        console.print(
            f"[cyan]{pack_info['name']}[/cyan]: {pack_info['display_name']}{security_badge}"
        )
        console.print(f"  [dim]Files affected: {len(pack_info['matching_files'])}[/dim]")
        console.print(f"  [dim]Entities affected: {pack_info['entity_count']}[/dim]")

        if pack_info["affected_entities"][:5]:
            for entity in pack_info["affected_entities"][:5]:
                console.print(
                    f"    • {entity['type']} [bold]{entity['name']}[/bold] ({entity['file']}:{entity['line']})"
                )
            if len(pack_info["affected_entities"]) > 5:
                console.print(
                    f"    [dim]... and {len(pack_info['affected_entities']) - 5} more[/dim]"
                )
        console.print()

    # Summary
    total_entities = sum(p["entity_count"] for p in affected_packs)
    critical_packs = [p for p in affected_packs if p["security_level"] == "critical"]
    if critical_packs:
        console.print(f"[red]⚠ {len(critical_packs)} CRITICAL pack(s) affected![/red]")

    console.print(
        f"\n[bold]Summary:[/bold] {len(affected_packs)} pack(s), {total_entities} entity/entities affected"
    )


@pack.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for programmatic use")
def pack_status(output_json):
    """Show indexing status for all context packs.

    Displays which packs have been built, their entity counts,
    and whether they have embeddings or LLM summaries.
    """
    from pathlib import Path as PathLib

    config = AutodocConfig.load()

    if not config.context_packs:
        if output_json:
            print(json.dumps({"error": "No context packs configured", "packs": []}))
        else:
            console.print(
                "[yellow]No context packs configured. Run 'autodoc pack auto-generate --save' first.[/yellow]"
            )
        return

    pack_statuses = []
    packs_dir = PathLib(".autodoc/packs")

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

    if output_json:
        output = {
            "packs": pack_statuses,
            "total": len(pack_statuses),
            "indexed": sum(1 for p in pack_statuses if p["indexed"]),
            "with_embeddings": sum(1 for p in pack_statuses if p["has_embeddings"]),
            "with_summaries": sum(1 for p in pack_statuses if p["has_summary"]),
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    console.print("\n[bold]Pack Status:[/bold]\n")

    for status in pack_statuses:
        indexed_badge = "[green]✓[/green]" if status["indexed"] else "[red]✗[/red]"
        embed_badge = "[green]E[/green]" if status["has_embeddings"] else "[dim]-[/dim]"
        summary_badge = "[green]S[/green]" if status["has_summary"] else "[dim]-[/dim]"

        console.print(
            f"  {indexed_badge} {embed_badge} {summary_badge} "
            f"[cyan]{status['name']}[/cyan] "
            f"({status['entity_count']} entities, {status['file_count']} files)"
        )

    console.print("\n[dim]Legend: ✓=indexed, E=embeddings, S=summary[/dim]")

    indexed_count = sum(1 for p in pack_statuses if p["indexed"])
    console.print(f"\n[bold]Total:[/bold] {indexed_count}/{len(pack_statuses)} packs indexed")


@pack.command("diff")
@click.argument("name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for programmatic use")
def pack_diff(name, output_json):
    """Show what changed in a pack since it was last indexed.

    Compares current files against the indexed state to identify
    new, modified, and deleted files.
    """
    from pathlib import Path as PathLib

    config = AutodocConfig.load()
    pack_config = config.get_pack(name)

    if not pack_config:
        if output_json:
            print(json.dumps({"error": f"Pack '{name}' not found"}))
        else:
            console.print(f"[red]Pack '{name}' not found.[/red]")
        return

    pack_file = PathLib(f".autodoc/packs/{name}.json")
    if not pack_file.exists():
        if output_json:
            print(
                json.dumps(
                    {
                        "error": f"Pack '{name}' not indexed yet",
                        "hint": f"Run: autodoc pack build {name}",
                    }
                )
            )
        else:
            console.print(
                f"[yellow]Pack '{name}' not indexed yet. Run: autodoc pack build {name}[/yellow]"
            )
        return

    with open(pack_file) as f:
        pack_data = json.load(f)

    indexed_files = set(pack_data.get("files", []))
    indexed_entities = pack_data.get("entities", [])

    # Find current files matching patterns
    base_path = PathLib.cwd()
    current_files = set()
    for pattern in pack_config.files:
        for f in base_path.glob(pattern):
            if f.is_file():
                current_files.add(str(f))

    # Categorize files
    new_files = sorted(current_files - indexed_files)
    deleted_files = sorted(indexed_files - current_files)
    unchanged_files = current_files & indexed_files

    # Estimate new entities in new files
    new_entity_estimate = 0
    for f in new_files:
        try:
            content = PathLib(f).read_text()
            new_entity_estimate += content.count("\ndef ") + content.count("\nclass ")
        except Exception:
            pass

    if output_json:
        output = {
            "pack": name,
            "indexed_at": pack_data.get("indexed_at"),
            "indexed_files": len(indexed_files),
            "indexed_entities": len(indexed_entities),
            "current_files": len(current_files),
            "new_files": new_files[:50],
            "new_files_count": len(new_files),
            "deleted_files": deleted_files[:50],
            "deleted_files_count": len(deleted_files),
            "unchanged_files_count": len(unchanged_files),
            "estimated_new_entities": new_entity_estimate,
            "needs_reindex": len(new_files) > 0 or len(deleted_files) > 0,
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    console.print(f"\n[bold]Diff for {pack_config.display_name}:[/bold]\n")

    console.print(
        f"[dim]Indexed: {len(indexed_files)} files, {len(indexed_entities)} entities[/dim]"
    )
    console.print(f"[dim]Current: {len(current_files)} files[/dim]\n")

    if not new_files and not deleted_files:
        console.print("[green]✓ Pack is up to date - no changes detected[/green]")
        return

    if new_files:
        console.print(f"[green]+ {len(new_files)} new file(s):[/green]")
        for f in new_files[:10]:
            console.print(f"  [green]+[/green] {PathLib(f).name}")
        if len(new_files) > 10:
            console.print(f"  [dim]... and {len(new_files) - 10} more[/dim]")
        console.print()

    if deleted_files:
        console.print(f"[red]- {len(deleted_files)} deleted file(s):[/red]")
        for f in deleted_files[:10]:
            console.print(f"  [red]-[/red] {PathLib(f).name}")
        if len(deleted_files) > 10:
            console.print(f"  [dim]... and {len(deleted_files) - 10} more[/dim]")
        console.print()

    if new_entity_estimate > 0:
        console.print(f"[cyan]~{new_entity_estimate} new entities estimated in new files[/cyan]\n")

    console.print(
        f"[yellow]⚠ Run 'autodoc pack build {name} --embeddings' to update index[/yellow]"
    )


@pack.command("deps")
@click.argument("name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for programmatic use")
@click.option("--transitive", "-t", is_flag=True, help="Include transitive dependencies")
def pack_deps(name, output_json, transitive):
    """Show dependencies for a context pack.

    Displays which other packs this pack depends on,
    and which packs depend on this one.
    """
    config = AutodocConfig.load()
    pack_config = config.get_pack(name)

    if not pack_config:
        if output_json:
            print(json.dumps({"error": f"Pack '{name}' not found"}))
        else:
            console.print(f"[red]Pack '{name}' not found.[/red]")
        return

    # Direct dependencies
    direct_deps = pack_config.dependencies

    # Transitive dependencies
    all_deps = []
    if transitive:
        resolved = config.resolve_pack_dependencies(name)
        all_deps = [p.name for p in resolved if p.name != name]

    # Reverse dependencies (who depends on this pack)
    dependents = []
    for p in config.context_packs:
        if name in p.dependencies:
            dependents.append(p.name)

    if output_json:
        output = {
            "pack": name,
            "direct_dependencies": direct_deps,
            "transitive_dependencies": all_deps if transitive else None,
            "dependents": dependents,
        }
        print(json.dumps(output, indent=2))
        return

    # Rich console output
    console.print(f"\n[bold]Dependencies for {pack_config.display_name}:[/bold]\n")

    if direct_deps:
        console.print("[cyan]Direct dependencies:[/cyan]")
        for dep in direct_deps:
            dep_pack = config.get_pack(dep)
            display = dep_pack.display_name if dep_pack else dep
            console.print(f"  → {dep} ({display})")
    else:
        console.print("[dim]No direct dependencies[/dim]")

    if transitive and all_deps:
        console.print("\n[cyan]All dependencies (transitive):[/cyan]")
        for dep in all_deps:
            dep_pack = config.get_pack(dep)
            display = dep_pack.display_name if dep_pack else dep
            console.print(f"  → {dep} ({display})")

    if dependents:
        console.print("\n[cyan]Dependents (packs that depend on this):[/cyan]")
        for dep in dependents:
            dep_pack = config.get_pack(dep)
            display = dep_pack.display_name if dep_pack else dep
            console.print(f"  ← {dep} ({display})")
    else:
        console.print("\n[dim]No packs depend on this one[/dim]")


@pack.command("export-skill")
@click.argument("name", required=False)
@click.option("--all", "export_all", is_flag=True, help="Export all packs as skills")
@click.option("--output", "-o", type=click.Path(), help="Custom output directory")
@click.option(
    "--format",
    "skill_format",
    type=click.Choice(["claude", "codex"]),
    default="claude",
    help="Output format: claude (.claude/skills/) or codex (~/.codex/skills/)",
)
@click.option(
    "--include-reference",
    "-r",
    is_flag=True,
    help="Generate ENTITIES.md and ARCHITECTURE.md reference files",
)
@click.option(
    "--generate-summary",
    "-s",
    is_flag=True,
    help="Generate LLM summary if missing (requires OpenAI API key)",
)
@click.option("--json", "output_json", is_flag=True, help="Output result as JSON")
def pack_export_skill(name, export_all, output, skill_format, include_reference, generate_summary, output_json):
    """Export context pack(s) as SKILL.md for AI assistants.

    Generates SKILL.md files that are discoverable by Claude Code,
    OpenAI Codex, and other AI assistants.

    Examples:

        autodoc pack export-skill authentication

        autodoc pack export-skill --all --format codex

        autodoc pack export-skill api --include-reference
    """
    from autodoc.skill_generator import SkillConfig, SkillFormat, SkillGenerator

    if not name and not export_all:
        if output_json:
            print(json.dumps({"error": "Either provide a pack name or use --all"}))
        else:
            console.print("[red]Error: Either provide a pack name or use --all[/red]")
        return

    config = AutodocConfig.load()

    if not config.context_packs:
        if output_json:
            print(json.dumps({"error": "No context packs defined"}))
        else:
            console.print("[yellow]No context packs defined in autodoc.yaml[/yellow]")
        return

    # Determine packs to export
    packs_to_export = []
    if export_all:
        packs_to_export = [p.name for p in config.context_packs]
    else:
        pack_config = config.get_pack(name)
        if not pack_config:
            if output_json:
                print(json.dumps({"error": f"Pack '{name}' not found"}))
            else:
                console.print(f"[red]Pack '{name}' not found.[/red]")
            return
        packs_to_export = [name]

    # Configure skill generator
    skill_config = SkillConfig(
        format=SkillFormat.CLAUDE if skill_format == "claude" else SkillFormat.CODEX,
        include_reference=include_reference,
        output_dir=Path(output) if output else None,
    )
    generator = SkillGenerator(skill_config)

    project_root = Path.cwd()
    results = []
    errors = []

    for pack_name in packs_to_export:
        # Load pack data from build output
        pack_data_path = project_root / ".autodoc" / "packs" / f"{pack_name}.json"

        if not pack_data_path.exists():
            error_msg = f"Pack '{pack_name}' not built. Run 'autodoc pack build {pack_name}' first."
            errors.append({"pack": pack_name, "error": error_msg})
            if not output_json:
                console.print(f"[yellow]⚠ {error_msg}[/yellow]")
            continue

        try:
            pack_data = json.loads(pack_data_path.read_text())
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse pack data: {e}"
            errors.append({"pack": pack_name, "error": error_msg})
            if not output_json:
                console.print(f"[red]Error reading {pack_name}: {error_msg}[/red]")
            continue

        # Check for LLM summary
        if not pack_data.get("llm_summary") and not generate_summary:
            if not output_json:
                console.print(
                    f"[yellow]⚠ Pack '{pack_name}' has no LLM summary. "
                    f"Skills will have limited content. Use --generate-summary or "
                    f"run 'autodoc pack build {pack_name} --summarize' first.[/yellow]"
                )

        # Generate LLM summary if requested and missing
        if generate_summary and not pack_data.get("llm_summary"):
            if not output_json:
                console.print(f"[cyan]Generating LLM summary for {pack_name}...[/cyan]")
            try:
                # Import enrichment module for summary generation
                from autodoc.enrichment import LLMEnricher

                enricher = LLMEnricher()
                entities = pack_data.get("entities", [])

                # Build context for summary
                entity_summaries = []
                for e in entities[:20]:  # Limit for token count
                    entity_summaries.append(
                        f"- {e.get('type', 'unknown')} `{e.get('name', '')}`: {e.get('docstring', '')[:100]}"
                    )

                summary_prompt = f"""Analyze this code pack and provide a structured summary:

Pack: {pack_data.get('display_name', pack_name)}
Description: {pack_data.get('description', '')}
Files: {', '.join(pack_data.get('files', [])[:10])}

Key entities:
{chr(10).join(entity_summaries)}

Provide:
1. architecture: Brief overview of how this code works
2. key_components: List of 3-5 most important functions/classes with their roles
3. usage_patterns: How to use this code (2-3 common patterns)
4. security_notes: Any security considerations (if applicable)"""

                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    summary_text = loop.run_until_complete(enricher.generate_llm_response(summary_prompt))

                    # Parse structured response
                    pack_data["llm_summary"] = {
                        "architecture": summary_text,
                        "key_components": [],
                        "usage_patterns": [],
                        "security_notes": [],
                    }
                finally:
                    loop.close()

            except Exception as e:
                if not output_json:
                    console.print(f"[yellow]⚠ Failed to generate summary: {e}[/yellow]")

        # Generate skill
        try:
            skill = generator.generate(pack_data, project_root)
            created_files = generator.write_skill(skill)

            result = {
                "pack": pack_name,
                "skill_name": skill.skill_name,
                "files_created": [str(f) for f in created_files],
            }
            results.append(result)

            if not output_json:
                console.print(f"[green]✓[/green] Exported [bold]{pack_name}[/bold] → {skill.skill_path}")
                if skill.reference_files:
                    for ref_name in skill.reference_files:
                        console.print(f"  [dim]+ {ref_name}[/dim]")

        except Exception as e:
            error_msg = f"Failed to generate skill: {e}"
            errors.append({"pack": pack_name, "error": error_msg})
            if not output_json:
                console.print(f"[red]Error exporting {pack_name}: {error_msg}[/red]")

    if output_json:
        output_data = {
            "success": results,
            "errors": errors,
            "format": skill_format,
            "output_dir": str(skill_config.get_output_dir(project_root)),
        }
        print(json.dumps(output_data, indent=2))
    else:
        if results:
            console.print(f"\n[bold green]✓ Exported {len(results)} skill(s)[/bold green]")
            console.print(f"[dim]Output directory: {skill_config.get_output_dir(project_root)}[/dim]")

            if skill_format == "claude":
                console.print(
                    "\n[cyan]Skills are now discoverable by Claude Code and compatible AI assistants.[/cyan]"
                )
            else:
                console.print("\n[cyan]Skills exported for OpenAI Codex.[/cyan]")


# =============================================================================
# Feature Discovery Commands
# =============================================================================


@cli.group()
def features():
    """Auto-detect code features using graph analysis.

    Uses Neo4j Graph Data Science (GDS) to detect code clusters
    using Louvain community detection, then names them semantically with LLM.

    Requires:
      1. Neo4j with GDS library installed
      2. A built code graph (run 'autodoc graph' first)

    Examples:
      autodoc features detect              # Detect features using GDS
      autodoc features name                # Name detected features with LLM
      autodoc features list                # List all detected features
      autodoc features show 0              # Show files in feature 0
      autodoc features export              # Export as context packs
    """
    pass


@features.command("detect")
@click.option("--force", is_flag=True, help="Force re-detection even if cache exists")
@click.option(
    "--max-degree",
    default=50,
    type=int,
    help="Max connections for a file to be included (filters 'God Objects')",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def features_detect(force, max_degree, as_json):
    """Run GDS Louvain community detection to find code features.

    This requires:
    1. Neo4j with GDS library installed
    2. A built code graph (run 'autodoc graph' first)

    Files with more than --max-degree connections are excluded
    (e.g., logger.py, config.py that are imported everywhere).

    Results are cached in .autodoc/features_cache.json
    """
    from .features import FeatureDetector, FeaturesCache

    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available. Install dependencies:[/red]")
        console.print("  pip install neo4j matplotlib plotly networkx pyvis")
        return

    from .graph import GraphConfig
    from neo4j import GraphDatabase

    cache = FeaturesCache()

    try:
        config = GraphConfig.from_env()
        driver = GraphDatabase.driver(config.uri, auth=(config.username, config.password))

        # Test connection
        with driver.session() as session:
            session.run("RETURN 1")
    except Exception as e:
        console.print(f"[red]Failed to connect to Neo4j: {e}[/red]")
        console.print("[yellow]Ensure Neo4j is running and credentials are correct.[/yellow]")
        return

    detector = FeatureDetector(driver)

    # Check GDS availability
    if not detector.check_gds_available():
        console.print("[red]Neo4j GDS library not installed.[/red]")
        console.print("\n[yellow]To install GDS:[/yellow]")
        console.print("  1. Download from: https://neo4j.com/deployment-center/")
        console.print("  2. Copy to neo4j/plugins/ directory")
        console.print("  3. Restart Neo4j")
        driver.close()
        return

    # Check graph exists
    if not detector.check_graph_exists():
        console.print("[red]No code graph found.[/red]")
        console.print("[yellow]Run 'autodoc graph' first to build the graph.[/yellow]")
        driver.close()
        return

    # Check cache validity
    current_hash = detector.compute_graph_hash()
    if not force:
        cached = cache.load()
        if cached:
            if cache.is_stale(current_hash):
                console.print("[yellow]Cache is stale (graph has changed).[/yellow]")
                console.print("[dim]Use --force to re-run detection[/dim]\n")
            else:
                if as_json:
                    console.print(json.dumps({"cached": True, **cached.to_dict()}))
                else:
                    console.print(f"[yellow]Using cached results from {cached.detected_at}[/yellow]")
                    console.print(f"[dim]Use --force to re-run detection[/dim]\n")
                    _display_detection_summary(cached)
                driver.close()
                return

    console.print(f"[yellow]Running Louvain community detection (max_degree={max_degree})...[/yellow]")

    try:
        result = detector.detect_features(max_degree=max_degree)
        cache.save(result)

        if as_json:
            console.print(json.dumps({"cached": False, **result.to_dict()}))
        else:
            console.print("[green]Feature detection complete![/green]\n")
            _display_detection_summary(result)
    except RuntimeError as e:
        console.print(f"[red]Error during feature detection: {e}[/red]")
    finally:
        driver.close()


def _display_detection_summary(result):
    """Display detection results in a table."""
    from pathlib import Path as PathLib

    console.print("[bold]Detection Summary:[/bold]")
    console.print(f"  Communities found: {result.community_count}")
    console.print(f"  Modularity score: {result.modularity:.3f}")
    console.print(f"  Max degree threshold: {result.max_degree_threshold}")
    console.print()

    table = Table(title="Detected Features")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Files", style="white", justify="right")
    table.add_column("Sample Files", style="dim")

    for fid in sorted(result.features.keys()):
        feature = result.features[fid]
        name_display = feature.display_name or "[dim]<unnamed>[/dim]"
        samples = ", ".join(PathLib(f.path).name for f in feature.sample_files[:3])
        if not samples and feature.files:
            samples = ", ".join(PathLib(p).name for p in feature.files[:3])
        if len(feature.sample_files) > 3 or len(feature.files) > 3:
            samples += "..."

        table.add_row(
            str(fid),
            name_display,
            str(feature.file_count),
            samples,
        )

    console.print(table)
    console.print(f"\n[dim]Run 'autodoc features name' to generate semantic names[/dim]")


@features.command("name")
@click.option("--feature-id", "-f", type=int, help="Name specific feature only")
@click.option("--force", is_flag=True, help="Re-name already named features")
@click.option("--dry-run", is_flag=True, help="Show what would be named without calling LLM")
def features_name(feature_id, force, dry_run):
    """Use LLM to generate semantic names for detected features.

    Names are generated based on file paths and summaries in each cluster.
    Uses the configured LLM provider (anthropic, openai, ollama).
    """
    import asyncio
    from .features import FeaturesCache, FeatureNamer

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        console.print("[red]No detected features found.[/red]")
        console.print("[yellow]Run 'autodoc features detect' first.[/yellow]")
        return

    if not result.features:
        console.print("[yellow]No features to name.[/yellow]")
        return

    config = AutodocConfig.load()

    # Check API key
    api_key = config.llm.get_api_key()
    if not api_key and config.llm.provider != "ollama":
        console.print(f"[red]No API key found for {config.llm.provider}[/red]")
        console.print("[yellow]Set via environment variable or .autodoc.yaml[/yellow]")
        return

    # Filter features to name
    features_to_name = {}
    for fid, feature in result.features.items():
        if feature_id is not None and fid != feature_id:
            continue
        if not force and feature.name:
            console.print(f"[dim]Skipping feature {fid} (already named: {feature.name})[/dim]")
            continue
        if feature.file_count == 0:
            continue
        features_to_name[fid] = feature

    if not features_to_name:
        console.print("[green]All features already named![/green]")
        return

    if dry_run:
        console.print(f"[cyan]DRY RUN: Would name {len(features_to_name)} features[/cyan]")
        for fid, feature in features_to_name.items():
            console.print(f"  Feature {fid}: {feature.file_count} files")
            for sf in feature.sample_files[:3]:
                console.print(f"    - {sf.path}")
        return

    console.print(f"[yellow]Naming {len(features_to_name)} features with {config.llm.provider}...[/yellow]")

    namer = FeatureNamer(config)

    async def name_features():
        for fid, feature in features_to_name.items():
            console.print(f"[dim]Naming feature {fid}...[/dim]")
            try:
                naming = await namer.name_feature(feature)
                if naming:
                    cache.update_feature_name(
                        fid,
                        naming["name"],
                        naming["display_name"],
                        naming.get("reasoning"),
                    )
                    console.print(f"  [green]{fid}[/green] -> {naming['display_name']}")
                    if naming.get("reasoning"):
                        console.print(f"       [dim]{naming['reasoning']}[/dim]")
                else:
                    console.print(f"  [yellow]Feature {fid}: naming failed[/yellow]")
            except Exception as e:
                console.print(f"  [red]Feature {fid}: {e}[/red]")

    asyncio.run(name_features())
    console.print("\n[green]Feature naming complete![/green]")


@features.command("list")
@click.option("--named-only", is_flag=True, help="Show only named features")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def features_list(named_only, as_json):
    """List all detected features."""
    from .features import FeaturesCache

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        if as_json:
            console.print(json.dumps({"error": "No features detected", "features": []}))
        else:
            console.print("[yellow]No detected features found.[/yellow]")
            console.print("[dim]Run 'autodoc features detect' first.[/dim]")
        return

    features_data = []
    for fid in sorted(result.features.keys()):
        feature = result.features[fid]
        if named_only and not feature.name:
            continue
        features_data.append({
            "id": fid,
            "name": feature.name,
            "display_name": feature.display_name,
            "file_count": feature.file_count,
            "named": feature.name is not None,
        })

    if as_json:
        console.print(json.dumps({
            "community_count": result.community_count,
            "modularity": result.modularity,
            "detected_at": result.detected_at,
            "features": features_data,
        }))
        return

    _display_detection_summary(result)


@features.command("show")
@click.argument("feature_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def features_show(feature_id, as_json):
    """Show all files belonging to a specific feature."""
    from .features import FeaturesCache

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        console.print("[red]No detected features found.[/red]")
        return

    if feature_id not in result.features:
        console.print(f"[red]Feature {feature_id} not found.[/red]")
        console.print(f"[dim]Available: {list(result.features.keys())}[/dim]")
        return

    feature = result.features[feature_id]

    if as_json:
        console.print(json.dumps(feature.to_dict()))
        return

    name_display = feature.display_name or f"Feature {feature_id}"
    console.print(f"\n[bold]{name_display}[/bold]")
    if feature.name:
        console.print(f"[dim]({feature.name})[/dim]")
    if feature.reasoning:
        console.print(f"\n{feature.reasoning}\n")

    console.print(f"[bold]Files ({feature.file_count}):[/bold]")
    for path in sorted(feature.files):
        console.print(f"  - {path}")


@features.command("export")
@click.option("--min-files", default=2, help="Minimum files for export (default: 2)")
@click.option("--save", is_flag=True, help="Append to .autodoc.yaml")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def features_export(min_files, save, as_json):
    """Export detected features as context packs.

    Converts named features to ContextPackConfig format that can be
    added to .autodoc.yaml for use with 'autodoc pack' commands.
    """
    from pathlib import Path as PathLib
    from .features import FeaturesCache
    from .config import ContextPackConfig

    cache = FeaturesCache()
    result = cache.load()

    if not result:
        console.print("[red]No detected features found.[/red]")
        return

    # Build context pack configs for named features
    packs = []
    for fid, feature in result.features.items():
        if not feature.name:
            continue
        if feature.file_count < min_files:
            continue

        # Convert file list to glob patterns
        # Group by directory and create patterns
        dirs = {}
        for path in feature.files:
            p = PathLib(path)
            dir_key = str(p.parent)
            if dir_key not in dirs:
                dirs[dir_key] = []
            dirs[dir_key].append(p.suffix or ".py")

        # Create patterns like "src/auth/**/*.py"
        patterns = []
        for dir_path, extensions in dirs.items():
            ext = extensions[0] if len(set(extensions)) == 1 else "*"
            pattern = f"{dir_path}/**/*{ext}"
            patterns.append(pattern)

        pack_config = ContextPackConfig(
            name=feature.name,
            display_name=feature.display_name or feature.name.replace("-", " ").title(),
            description=feature.reasoning or f"Auto-detected feature containing {feature.file_count} files",
            files=patterns,
            tags=["auto-detected"],
        )
        packs.append(pack_config)

    if not packs:
        console.print("[yellow]No named features to export.[/yellow]")
        console.print("[dim]Run 'autodoc features name' first.[/dim]")
        return

    if as_json:
        console.print(json.dumps([p.model_dump() for p in packs], indent=2))
        return

    # Display packs
    console.print(f"\n[bold]Exportable Context Packs ({len(packs)}):[/bold]\n")
    for pack in packs:
        console.print(f"[cyan]{pack.name}[/cyan]: {pack.display_name}")
        console.print(f"  {pack.description}")
        console.print(f"  Files: {pack.files}")
        console.print()

    if save:
        config = AutodocConfig.load()
        existing_names = {p.name for p in config.context_packs}

        added = 0
        for pack in packs:
            if pack.name not in existing_names:
                config.context_packs.append(pack)
                added += 1
                console.print(f"[green]Added: {pack.name}[/green]")
            else:
                console.print(f"[yellow]Skipped (exists): {pack.name}[/yellow]")

        if added > 0:
            config.save()
            console.print(f"\n[green]Saved {added} pack(s) to .autodoc.yaml[/green]")
    else:
        console.print("[dim]Use --save to append to .autodoc.yaml[/dim]")


# =============================================================================
# MCP Server Command
# =============================================================================


@cli.command("mcp-server")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="Transport protocol (stdio for local, sse/streamable-http for remote)",
)
@click.option(
    "--host",
    default="localhost",
    help="Host for remote transports (default: localhost)",
)
@click.option(
    "--port",
    default=8089,
    type=int,
    help="Port for remote transports (default: 8089)",
)
def mcp_server(transport: str, host: str, port: int):
    """Start the MCP (Model Context Protocol) server.

    This exposes autodoc context pack tools for AI assistants like Claude Code.

    Transport options:
      --transport stdio   Local stdio (default, for Claude Code)
      --transport sse     Remote SSE server (for remote agents)

    Tools available:
      - pack_list: List all context packs
      - pack_info: Get details about a pack
      - pack_query: Search within a pack
      - pack_files: Get files in a pack
      - pack_entities: Get entities from a pack
      - impact_analysis: Analyze impact of file changes
      - pack_status: Get indexing status for all packs
      - pack_deps: Show pack dependencies
      - pack_diff: Show changes since last index

    Resources available:
      - autodoc://packs - List all packs
      - autodoc://packs/{name} - Get specific pack info

    Examples:
      # Local MCP (for Claude Code settings)
      autodoc mcp-server

      # Remote MCP server (for remote agents)
      autodoc mcp-server --transport sse --port 8089
    """
    try:
        from .mcp_server import mcp

        console.print("[bold]Starting autodoc MCP server...[/bold]")
        console.print(f"[dim]Transport: {transport}[/dim]")
        if transport != "stdio":
            console.print(f"[dim]Listening on: http://{host}:{port}[/dim]")
        console.print(
            "[dim]Tools: pack_list, pack_info, pack_query, pack_files, pack_entities,[/dim]"
        )
        console.print("[dim]        impact_analysis, pack_status, pack_deps, pack_diff[/dim]")
        console.print("[dim]Resources: autodoc://packs, autodoc://packs/{name}[/dim]\n")

        if transport == "stdio":
            mcp.run(transport="stdio")
        else:
            mcp.run(transport=transport, host=host, port=port)
    except ImportError as e:
        console.print(f"[red]Error: MCP dependencies not installed: {e}[/red]")
        console.print("[yellow]Install with: pip install fastmcp[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting MCP server: {e}[/red]")


@cli.command("init-hooks")
@click.option(
    "--warn-only",
    is_flag=True,
    help="Only warn about critical pack changes, don't block commits",
)
@click.option(
    "--critical-only",
    is_flag=True,
    help="Only check changes to packs with security_level=critical",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".git/hooks/pre-commit",
    help="Output path for the pre-commit hook",
)
def init_hooks(warn_only, critical_only, output):
    """Generate a pre-commit hook for impact analysis.

    This creates a git pre-commit hook that runs impact analysis on
    staged files and warns (or blocks) commits that affect critical
    context packs.

    Example:
        autodoc init-hooks              # Install hook (blocking mode)
        autodoc init-hooks --warn-only  # Install hook (warning mode)
    """
    from pathlib import Path as PathLib

    hook_path = PathLib(output)

    # Check if we're in a git repo
    git_dir = PathLib(".git")
    if not git_dir.exists():
        console.print("[red]Error: Not in a git repository[/red]")
        return

    # Ensure hooks directory exists
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if hook already exists
    if hook_path.exists():
        if not click.confirm(f"Pre-commit hook already exists at {hook_path}. Overwrite?"):
            console.print("[yellow]Aborted.[/yellow]")
            return

    # Generate hook content
    block_mode = "warn" if warn_only else "block"
    security_filter = "--security critical" if critical_only else ""

    hook_content = f"""#!/bin/bash
# Autodoc Impact Analysis Pre-commit Hook
# Generated by: autodoc init-hooks
# Mode: {block_mode}

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Run impact analysis
echo "Running autodoc impact analysis..."
IMPACT_OUTPUT=$(autodoc impact $STAGED_FILES --json {security_filter} 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Warning: autodoc impact analysis failed (autodoc may not be installed)"
    exit 0
fi

# Check for critical pack changes
CRITICAL_PACKS=$(echo "$IMPACT_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    critical = data.get('critical_packs', [])
    if critical:
        print(','.join(critical))
except:
    pass
" 2>/dev/null)

if [ -n "$CRITICAL_PACKS" ]; then
    echo ""
    echo "⚠️  CRITICAL PACK CHANGES DETECTED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "The following critical security packs are affected:"
    echo "$CRITICAL_PACKS" | tr ',' '\\n' | while read pack; do
        echo "  • $pack"
    done
    echo ""
"""

    if warn_only:
        hook_content += """    echo "⚠️  Please ensure these changes have been reviewed for security implications."
    echo ""
fi

exit 0
"""
    else:
        hook_content += """    echo "🛑 Commit blocked. Critical packs require explicit confirmation."
    echo ""
    echo "To proceed, use one of these options:"
    echo "  1. git commit --no-verify  (bypass hook)"
    echo "  2. autodoc init-hooks --warn-only  (switch to warning mode)"
    echo ""
    exit 1
fi

exit 0
"""

    # Write hook file
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)  # Make executable

    console.print(f"[green]✓ Pre-commit hook installed at {hook_path}[/green]")
    console.print(f"[dim]Mode: {'Warning only' if warn_only else 'Blocking'}[/dim]")
    if critical_only:
        console.print("[dim]Filter: Critical packs only[/dim]")

    console.print("\n[bold]Hook behavior:[/bold]")
    if warn_only:
        console.print("  • Warns when commits affect critical packs")
        console.print("  • Does not block commits")
    else:
        console.print("  • Blocks commits that affect critical packs")
        console.print("  • Use 'git commit --no-verify' to bypass")

    console.print("\n[dim]To uninstall: rm .git/hooks/pre-commit[/dim]")


def main():
    cli()


if __name__ == "__main__":
    main()
