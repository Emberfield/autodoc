#!/bin/bash
# Create complete Autodoc project in one script

echo "🚀 Creating Autodoc - Simple Code Intelligence"

# Create directory structure
mkdir -p src/autodoc tests

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "autodoc"
dynamic = ["version"]
description = "AI-powered code intelligence for our projects"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
dependencies = [
    "aiohttp>=3.9.1",
    "aiohttp-cors>=0.7.0",
    "asyncpg>=0.29.0",
    "numpy<2.0",
    "astroid>=3.0.2",
    "click>=8.1.7",
    "rich>=13.7.0",
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
    "openai>=1.6.1",
    "tiktoken>=0.5.2",
    "PyGithub>=2.1.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.12.1",
    "ruff>=0.1.8",
]

[project.scripts]
autodoc = "autodoc.cli:main"

[tool.hatch.version]
path = "src/autodoc/__about__.py"

[tool.hatch.envs.default]
dependencies = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.12.1",
    "ruff>=0.1.8",
    "ipython>=8.18.0",
]

[tool.hatch.envs.default.scripts]
serve = "python -m autodoc serve"
analyze = "python -m autodoc analyze {args}"
search = "python -m autodoc search {args}"
test = "pytest {args:tests}"
fmt = ["black .", "ruff check . --fix"]
check = "python -m autodoc check"

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]
ignore = ["E501"]
EOF

# Create src/autodoc/__about__.py
cat > src/autodoc/__about__.py << 'EOF'
__version__ = "0.1.0"
EOF

# Create src/autodoc/__init__.py
cat > src/autodoc/__init__.py << 'EOF'
from autodoc.__about__ import __version__
from autodoc.cli import Autodoc

__all__ = ["__version__", "Autodoc"]
EOF

# Create src/autodoc/__main__.py
cat > src/autodoc/__main__.py << 'EOF'
from autodoc.cli import main

if __name__ == "__main__":
    main()
EOF

# Create the main implementation - src/autodoc/cli.py
cat > src/autodoc/cli.py << 'EOF'
#!/usr/bin/env python3
"""
Minimal Autodoc implementation that just works.
"""

import os
import ast
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import click
from rich.console import Console
from rich.table import Table
import aiohttp
from dotenv import load_dotenv

load_dotenv()
console = Console()


@dataclass
class CodeEntity:
    type: str
    name: str
    file_path: str
    line_number: int
    docstring: Optional[str]
    code: str
    embedding: Optional[List[float]] = None


class SimpleASTAnalyzer:
    def analyze_file(self, file_path: Path) -> List[CodeEntity]:
        entities = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    entities.append(CodeEntity(
                        type='function',
                        name=node.name,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        code=f"def {node.name}(...)",
                    ))
                elif isinstance(node, ast.ClassDef):
                    entities.append(CodeEntity(
                        type='class',
                        name=node.name,
                        file_path=str(file_path),
                        line_number=node.lineno,
                        docstring=ast.get_docstring(node),
                        code=f"class {node.name}",
                    ))
        except Exception as e:
            console.print(f"[red]Error analyzing {file_path}: {e}[/red]")
        return entities


class OpenAIEmbedder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    async def embed(self, text: str) -> List[float]:
        async with aiohttp.ClientSession() as session:
            data = {
                "input": text[:8000],
                "model": "text-embedding-3-small"
            }
            async with session.post(
                "https://api.openai.com/v1/embeddings",
                headers=self.headers,
                json=data
            ) as response:
                result = await response.json()
                return result["data"][0]["embedding"]
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings


class SimpleAutodoc:
    def __init__(self):
        self.analyzer = SimpleASTAnalyzer()
        self.embedder = None
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "sk-...":
            self.embedder = OpenAIEmbedder(api_key)
        else:
            console.print("[yellow]No OpenAI API key found - embeddings disabled[/yellow]")
            
        self.entities: List[CodeEntity] = []
        
    async def analyze_directory(self, path: Path) -> Dict[str, Any]:
        console.print(f"[blue]Analyzing {path}...[/blue]")
        
        python_files = list(path.rglob("*.py"))
        python_files = [
            f for f in python_files 
            if not any(skip in f.parts for skip in ['__pycache__', 'venv', '.venv', 'build', 'dist'])
        ]
        
        console.print(f"Found {len(python_files)} Python files")
        
        all_entities = []
        for file_path in python_files:
            entities = self.analyzer.analyze_file(file_path)
            all_entities.extend(entities)
            
        console.print(f"Found {len(all_entities)} code entities")
        
        if self.embedder and all_entities:
            console.print("[blue]Generating embeddings...[/blue]")
            texts = []
            for entity in all_entities:
                text = f"{entity.type} {entity.name}"
                if entity.docstring:
                    text += f": {entity.docstring}"
                texts.append(text)
                
            embeddings = await self.embedder.embed_batch(texts)
            for entity, embedding in zip(all_entities, embeddings):
                entity.embedding = embedding
                
            console.print(f"[green]Generated {len(embeddings)} embeddings[/green]")
            
        self.entities = all_entities
        
        return {
            "files_analyzed": len(python_files),
            "total_entities": len(all_entities),
            "functions": len([e for e in all_entities if e.type == 'function']),
            "classes": len([e for e in all_entities if e.type == 'class']),
            "has_embeddings": self.embedder is not None
        }
        
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.entities:
            return []
            
        if self.embedder and all(e.embedding for e in self.entities):
            console.print(f"[blue]Searching for: {query}[/blue]")
            query_embedding = await self.embedder.embed(query)
            
            results = []
            for entity in self.entities:
                similarity = sum(a * b for a, b in zip(query_embedding, entity.embedding))
                results.append((similarity, entity))
                
            results.sort(key=lambda x: x[0], reverse=True)
            
            return [
                {"entity": asdict(entity), "similarity": similarity}
                for similarity, entity in results[:limit]
            ]
        else:
            query_lower = query.lower()
            results = []
            
            for entity in self.entities:
                if query_lower in entity.name.lower():
                    results.append({"entity": asdict(entity), "similarity": 1.0})
                elif entity.docstring and query_lower in entity.docstring.lower():
                    results.append({"entity": asdict(entity), "similarity": 0.5})
                    
            return results[:limit]
    
    def save(self, path: str = "autodoc_cache.json"):
        data = {"entities": [asdict(e) for e in self.entities]}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Saved {len(self.entities)} entities to {path}[/green]")
        
    def load(self, path: str = "autodoc_cache.json"):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.entities = [CodeEntity(**entity) for entity in data["entities"]]
            console.print(f"[green]Loaded {len(self.entities)} entities from {path}[/green]")
        except FileNotFoundError:
            console.print(f"[yellow]No cache file found at {path}[/yellow]")


@click.group()
def cli():
    """Autodoc - AI-powered code intelligence"""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--save", is_flag=True, help="Save analysis to cache")
async def analyze(path, save):
    """Analyze a codebase"""
    autodoc = SimpleAutodoc()
    summary = await autodoc.analyze_directory(Path(path))
    
    console.print("\n[bold]Analysis Summary:[/bold]")
    for key, value in summary.items():
        console.print(f"  {key}: {value}")
        
    if save:
        autodoc.save()


@cli.command()
@click.argument("query")
@click.option("--limit", default=5, help="Number of results")
async def search(query, limit):
    """Search for code"""
    autodoc = SimpleAutodoc()
    autodoc.load()
    
    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return
        
    results = await autodoc.search(query, limit)
    
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
            f"{result['similarity']:.2f}"
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


class Autodoc(SimpleAutodoc):
    """Public API"""
    async def analyze(self, path: str) -> Dict[str, Any]:
        return await self.analyze_directory(Path(path))


def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ['analyze', 'search']:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        original_invoke = cli.invoke
        def invoke(ctx):
            rv = original_invoke(ctx)
            if asyncio.iscoroutine(rv):
                return loop.run_until_complete(rv)
            return rv
        cli.invoke = invoke
    cli()


if __name__ == "__main__":
    main()
EOF

# Create tests/test_autodoc.py
cat > tests/test_autodoc.py << 'EOF'
import pytest
from pathlib import Path
import tempfile
from autodoc.cli import SimpleAutodoc, SimpleASTAnalyzer


def test_ast_analyzer():
    analyzer = SimpleASTAnalyzer()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def test():\n    """Test"""\n    pass')
        temp_path = Path(f.name)
    
    try:
        entities = analyzer.analyze_file(temp_path)
        assert len(entities) == 1
        assert entities[0].name == 'test'
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_autodoc():
    autodoc = SimpleAutodoc()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text('def hello():\n    """Hi"""\n    pass')
        
        summary = await autodoc.analyze_directory(Path(tmpdir))
        assert summary['functions'] == 1
EOF

# Create .env.example
cat > .env.example << 'EOF'
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://localhost/autodoc
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.coverage
.pytest_cache/
.ruff_cache/
venv/
.venv/
autodoc_cache.json
EOF

# Create README.md
cat > README.md << 'EOF'
# Autodoc - Simple Code Intelligence

Analyze and search codebases using AI. No overengineering, just works.

## Quick Start

```bash
# Setup
./create_autodoc.sh
hatch env create
echo "OPENAI_API_KEY=sk-your-key" > .env

# Use
hatch run analyze ./my-project --save
hatch run search "authentication"
```

## Install in Other Projects

```bash
pip install /path/to/autodoc
# or after publishing
pip install autodoc
```

Then use:
```python
from autodoc import Autodoc

autodoc = Autodoc()
await autodoc.analyze("./src")
results = await autodoc.search("validation")
```

That's it!
EOF

# Create Makefile
cat > Makefile << 'EOF'
.PHONY: help setup analyze search test build

help:
	@echo "  make setup    - Initial setup"
	@echo "  make analyze  - Analyze current directory"
	@echo "  make search   - Search code (QUERY='...')"
	@echo "  make test     - Run tests"
	@echo "  make build    - Build package"

setup:
	hatch env create

analyze:
	hatch run analyze . --save

search:
	hatch run search "$(QUERY)"

test:
	hatch run test

build:
	hatch build
EOF

# Final setup
chmod +x create_autodoc.sh

echo "
✅ Autodoc created successfully!

Next steps:
1. Install Hatch: pip install hatch
2. Create environment: hatch env create  
3. Add OpenAI key: echo 'OPENAI_API_KEY=sk-...' > .env
4. Test it: hatch run analyze . --save

Or use Make:
  make setup
  make analyze
  make search QUERY='function'
"