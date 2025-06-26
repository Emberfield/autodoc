"""
Command-line interface for Autodoc.
"""

import asyncio
import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from .autodoc import SimpleAutodoc

# Optional graph imports - only available if dependencies are installed
try:
    from .graph import CodeGraphBuilder, CodeGraphQuery, CodeGraphVisualizer

    GRAPH_AVAILABLE = True
except ImportError:
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
def analyze(path, save):
    """Analyze a codebase"""
    autodoc = SimpleAutodoc()

    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        summary = loop.run_until_complete(autodoc.analyze_directory(Path(path)))
    finally:
        loop.close()

    console.print("\n[bold]Analysis Summary:[/bold]")
    
    # Display overall stats
    console.print(f"  Files analyzed: {summary['files_analyzed']}")
    console.print(f"  Total entities: {summary['total_entities']}")
    console.print(f"  Functions: {summary['functions']}")
    console.print(f"  Classes: {summary['classes']}")
    
    if summary.get('methods', 0) > 0:
        console.print(f"  Methods: {summary['methods']}")
    if summary.get('interfaces', 0) > 0:
        console.print(f"  Interfaces: {summary['interfaces']}")
    if summary.get('types', 0) > 0:
        console.print(f"  Types: {summary['types']}")
    
    console.print(f"  Embeddings: {'enabled' if summary['has_embeddings'] else 'disabled'}")
    
    # Display language-specific stats
    if 'languages' in summary:
        languages = summary['languages']
        
        if languages['python']['entities'] > 0:
            console.print("\n[bold]Python:[/bold]")
            console.print(f"  Files: {languages['python']['files']}")
            console.print(f"  Entities: {languages['python']['entities']}")
            console.print(f"  Functions: {languages['python']['functions']}")
            console.print(f"  Classes: {languages['python']['classes']}")
        
        if languages['typescript']['entities'] > 0:
            console.print("\n[bold]TypeScript:[/bold]")
            console.print(f"  Files: {languages['typescript']['files']}")
            console.print(f"  Entities: {languages['typescript']['entities']}")
            console.print(f"  Functions: {languages['typescript']['functions']}")
            console.print(f"  Classes: {languages['typescript']['classes']}")
            console.print(f"  Methods: {languages['typescript']['methods']}")
            console.print(f"  Interfaces: {languages['typescript']['interfaces']}")
            console.print(f"  Types: {languages['typescript']['types']}")

    if save:
        autodoc.save()


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Number of results")
def search(query, limit):
    """Search for code"""
    autodoc = SimpleAutodoc()
    autodoc.load()

    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return

    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(autodoc.search(query, limit))
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
def check():
    """Check dependencies and configuration"""
    console.print("[bold]Autodoc Status:[/bold]\n")

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


@cli.command(name="graph")
@click.option("--clear", is_flag=True, help="Clear existing graph data")
@click.option("--visualize", is_flag=True, help="Create visualizations after building graph")
def graph(clear, visualize):
    """Build code relationship graph database"""
    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available. Install graph dependencies:[/red]")
        console.print("pip install matplotlib plotly neo4j")
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
                console.print(f"[yellow]Warning: Could not create visualizations: {viz_error}[/yellow]")
            finally:
                query.close()
        else:
            console.print("[blue]💡 Use 'autodoc graph --visualize' to create visualizations[/blue]")
        
        builder.close()

    except Exception as e:
        console.print(f"[red]Error building graph: {e}[/red]")
        console.print("[yellow]Make sure Neo4j is running at bolt://localhost:7687[/yellow]")


@cli.command(name="vector")
@click.option("--regenerate", is_flag=True, help="Regenerate all embeddings (overwrite existing)")
def vector(regenerate):
    """Generate embeddings for semantic search"""
    autodoc = SimpleAutodoc()
    
    # Load existing entities
    autodoc.load()
    
    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return
    
    if not autodoc.embedder:
        console.print("[red]No OpenAI API key found. Set OPENAI_API_KEY environment variable.[/red]")
        console.print("[blue]💡 Create a .env file with: OPENAI_API_KEY=sk-your-key-here[/blue]")
        return
    
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


@cli.command(name="visualize-graph")
@click.option("--output", "-o", default="code_graph.html", help="Output file for interactive graph")
@click.option("--deps", is_flag=True, help="Create module dependency graph")
@click.option("--complexity", is_flag=True, help="Create complexity heatmap")
@click.option("--all", "create_all", is_flag=True, help="Create all visualizations")
def visualize_graph(output, deps, complexity, create_all):
    """Create interactive visualizations of the code graph"""
    if not GRAPH_AVAILABLE:
        console.print("[red]Graph functionality not available. Install graph dependencies:[/red]")
        console.print("pip install matplotlib plotly neo4j")
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
        console.print("pip install matplotlib plotly neo4j")
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
@click.option("--detailed", is_flag=True, help="Generate detailed documentation with code examples")
def generate(output, output_format, detailed):
    """Generate comprehensive codebase documentation"""
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


# Backwards compatibility alias
@cli.command(name="generate-summary", hidden=True)
@click.option("--output", "-o", help="Output file path")
@click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]))
def generate_summary_alias(output, output_format):
    """[DEPRECATED] Use 'autodoc generate' instead"""
    console.print("[yellow]⚠️  'generate-summary' is deprecated. Use 'autodoc generate' instead.[/yellow]")
    from click import Context
    ctx = Context(generate)
    return ctx.invoke(generate, output=output or "AUTODOC.md", output_format=output_format, detailed=False)


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
        console.print(f"[blue]API docs: Available endpoints at /api/*[/blue]")
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


def main():
    cli()


if __name__ == "__main__":
    main()
