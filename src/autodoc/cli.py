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

console = Console()


@click.group()
def cli():
    """Autodoc - AI-powered code intelligence"""
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
    for key, value in summary.items():
        console.print(f"  {key}: {value}")

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


@cli.command(name="build-graph")
@click.option("--clear", is_flag=True, help="Clear existing graph data")
def build_graph(clear):
    """Build code relationship graph in Neo4j"""
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
        console.print("[yellow]Building code graph...[/yellow]")
        builder = CodeGraphBuilder()

        if clear:
            builder.clear_graph()
            console.print("✅ Cleared existing graph data")

        builder.build_from_autodoc(autodoc)
        builder.close()

        console.print("[green]✅ Code graph built successfully![/green]")
        console.print("Use 'autodoc visualize-graph' to create visualizations")

    except Exception as e:
        console.print(f"[red]Error building graph: {e}[/red]")
        console.print("[yellow]Make sure Neo4j is running at bolt://localhost:7687[/yellow]")


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
        console.print("[yellow]Make sure you've run 'autodoc build-graph' first[/yellow]")


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
        console.print("[yellow]Make sure you've run 'autodoc build-graph' first[/yellow]")


@cli.command(name="generate-summary")
@click.option("--output", "-o", help="Save summary to file (e.g., summary.md)")
@click.option(
    "--format",
    "output_format",
    default="markdown",
    type=click.Choice(["markdown", "json"]),
    help="Output format",
)
def generate_summary(output, output_format):
    """Generate a comprehensive codebase summary optimized for LLM context"""
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

    # Handle output format
    if output_format == "json":
        output_content = json.dumps(summary, indent=2, default=str)
        if output:
            if not output.endswith(".json"):
                output = f"{output}.json"
    else:  # markdown
        output_content = autodoc.format_summary_markdown(summary)
        if output:
            if not output.endswith(".md"):
                output = f"{output}.md"

    # Save to file if output path specified
    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(output_content)
            console.print(f"[green]✅ Comprehensive documentation saved to {output}[/green]")
            console.print(f"[blue]File size: {len(output_content):,} characters[/blue]")

            # Show preview of what was generated
            overview = summary["overview"]
            console.print("\n[bold]Generated Documentation Summary:[/bold]")
            console.print(
                f"- {overview['total_functions']} functions across {overview['total_files']} files"
            )
            console.print(f"- {overview['total_classes']} classes analyzed")
            console.print(f"- {len(summary.get('feature_map', {}))} feature categories identified")
            console.print(f"- {len(summary.get('modules', {}))} modules documented")

            # Show build and CI info
            if summary.get("build_system") and summary["build_system"].get("build_tools"):
                console.print(f"- Build tools: {', '.join(summary['build_system']['build_tools'])}")

            if summary.get("test_system"):
                test_count = summary["test_system"].get("test_functions_count", 0)
                console.print(f"- {test_count} test functions found")

            if summary.get("ci_configuration") and summary["ci_configuration"].get("has_ci"):
                platforms = summary["ci_configuration"].get("platforms", [])
                console.print(f"- CI/CD platforms: {', '.join(platforms)}")

        except Exception as e:
            console.print(f"[red]Error saving file: {e}[/red]")
            # Fall back to displaying in console
            if output_format == "markdown":
                console.print(Markdown(output_content))
            else:
                console.print(output_content)
    else:
        # Display in console
        if output_format == "markdown":
            console.print(Markdown(output_content))
        else:
            console.print(output_content)


def main():
    cli()


if __name__ == "__main__":
    main()
