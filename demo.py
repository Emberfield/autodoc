#!/usr/bin/env python3
"""
Demo script showcasing Autodoc capabilities
"""

import asyncio
import os
from pathlib import Path

from rich.console import Console
from rich.table import Table

from autodoc import SimpleAutodoc

console = Console()


async def demo():
    """Run a demo of Autodoc features"""
    console.print("[bold cyan]Autodoc Demo[/bold cyan]")
    console.print("=" * 50)

    # Initialize Autodoc
    autodoc = SimpleAutodoc()

    # Check if we have OpenAI API key
    if os.getenv("OPENAI_API_KEY"):
        console.print("✅ OpenAI API key found - embeddings enabled")
    else:
        console.print("ℹ️  No OpenAI API key - using text-based search")

    console.print("\n[yellow]Analyzing the autodoc codebase itself...[/yellow]")

    # Analyze the src directory
    src_path = Path(__file__).parent / "src"
    summary = await autodoc.analyze_directory(src_path)

    # Display summary
    console.print("\n[bold]Analysis Summary:[/bold]")
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Files Analyzed", str(summary["files_analyzed"]))
    table.add_row("Total Entities", str(summary["total_entities"]))
    table.add_row("Functions", str(summary["functions"]))
    table.add_row("Classes", str(summary["classes"]))
    table.add_row("Has Embeddings", "Yes" if summary["has_embeddings"] else "No")

    console.print(table)

    # Demo search
    console.print("\n[yellow]Searching for 'analyze' functions...[/yellow]")
    results = await autodoc.search("analyze", limit=3)

    if results:
        console.print("\n[bold]Search Results:[/bold]")
        for i, result in enumerate(results, 1):
            entity = result["entity"]
            console.print(f"\n{i}. [cyan]{entity['name']}[/cyan] ({entity['type']})")
            console.print(f"   File: {Path(entity['file_path']).name}:{entity['line_number']}")
            if entity.get("docstring"):
                console.print(f"   Doc: {entity['docstring'][:80]}...")
            if result.get("similarity") is not None:
                console.print(f"   Similarity: {result['similarity']:.2f}")

    # Save cache
    console.print("\n[yellow]Saving analysis cache...[/yellow]")
    autodoc.save("demo_cache.json")
    console.print("✅ Cache saved to demo_cache.json")

    console.print("\n[bold green]Demo complete![/bold green]")
    console.print("\nTry running these commands:")
    console.print("  autodoc analyze .")
    console.print("  autodoc search 'your query'")
    console.print("  autodoc generate-summary")


if __name__ == "__main__":
    asyncio.run(demo())
