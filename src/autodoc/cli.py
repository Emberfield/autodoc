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
from rich.markdown import Markdown
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

    def generate_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive codebase summary"""
        if not self.entities:
            return {"error": "No analyzed code found. Run 'analyze' first."}
        
        # Group entities by file
        files = {}
        for entity in self.entities:
            file_path = entity.file_path
            if file_path not in files:
                files[file_path] = {
                    "functions": [],
                    "classes": [],
                    "module_doc": None
                }
            
            if entity.type == 'function':
                files[file_path]["functions"].append({
                    "name": entity.name,
                    "line": entity.line_number,
                    "docstring": entity.docstring or "No description",
                    "purpose": self._extract_purpose(entity)
                })
            elif entity.type == 'class':
                files[file_path]["classes"].append({
                    "name": entity.name,
                    "line": entity.line_number,
                    "docstring": entity.docstring or "No description",
                    "methods": self._get_class_methods(entity, file_path)
                })
        
        # Build feature map
        feature_map = self._build_feature_map()
        
        # Create summary
        summary = {
            "overview": {
                "total_files": len(files),
                "total_functions": len([e for e in self.entities if e.type == 'function']),
                "total_classes": len([e for e in self.entities if e.type == 'class']),
                "has_tests": any('test' in Path(f).name for f in files.keys()),
                "main_language": "Python"
            },
            "modules": {},
            "feature_map": feature_map,
            "key_functions": self._identify_key_functions(),
            "class_hierarchy": self._build_class_hierarchy()
        }
        
        # Process each file
        for file_path, content in files.items():
            module_name = self._path_to_module(file_path)
            summary["modules"][module_name] = {
                "file": file_path,
                "purpose": self._infer_module_purpose(file_path, content),
                "functions": content["functions"],
                "classes": content["classes"],
                "imports": self._extract_imports(file_path)
            }
        
        return summary

    def _extract_purpose(self, entity: CodeEntity) -> str:
        """Extract purpose from function name and docstring"""
        name_lower = entity.name.lower()
        if 'test_' in name_lower:
            return "Test function"
        elif 'get_' in name_lower or 'fetch_' in name_lower:
            return "Retrieves data"
        elif 'set_' in name_lower or 'update_' in name_lower:
            return "Updates data"
        elif 'create_' in name_lower or 'make_' in name_lower:
            return "Creates new objects"
        elif 'delete_' in name_lower or 'remove_' in name_lower:
            return "Removes data"
        elif 'is_' in name_lower or 'has_' in name_lower:
            return "Checks condition"
        elif entity.docstring:
            return entity.docstring.split('\n')[0]
        else:
            return "General purpose function"

    def _get_class_methods(self, class_entity: CodeEntity, file_path: str) -> List[str]:
        """Get methods belonging to a class"""
        methods = []
        class_line = class_entity.line_number
        
        for entity in self.entities:
            if (entity.type == 'function' and 
                entity.file_path == file_path and
                entity.line_number > class_line):
                methods.append(entity.name)
                if len(methods) > 10:
                    break
        
        return methods

    def _build_feature_map(self) -> Dict[str, List[str]]:
        """Build a map of features to locations"""
        feature_map = {
            "authentication": [],
            "database": [],
            "api_endpoints": [],
            "data_processing": [],
            "file_operations": [],
            "testing": [],
            "configuration": [],
            "utilities": []
        }
        
        for entity in self.entities:
            name_lower = entity.name.lower()
            file_lower = entity.file_path.lower()
            
            if any(auth in name_lower for auth in ['auth', 'login', 'token', 'permission']):
                feature_map["authentication"].append(f"{entity.name} in {Path(entity.file_path).name}")
            
            if any(db in name_lower for db in ['db', 'database', 'query', 'model', 'orm']):
                feature_map["database"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if any(api in name_lower for api in ['api', 'endpoint', 'route', 'view']):
                feature_map["api_endpoints"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if any(proc in name_lower for proc in ['process', 'transform', 'parse', 'analyze']):
                feature_map["data_processing"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if any(file_op in name_lower for file_op in ['read', 'write', 'save', 'load', 'file']):
                feature_map["file_operations"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if 'test' in file_lower or 'test_' in name_lower:
                feature_map["testing"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if any(conf in file_lower for conf in ['config', 'settings', 'env']):
                feature_map["configuration"].append(f"{entity.name} in {Path(entity.file_path).name}")
                
            if any(util in file_lower for util in ['util', 'helper', 'common']):
                feature_map["utilities"].append(f"{entity.name} in {Path(entity.file_path).name}")
        
        return {k: v for k, v in feature_map.items() if v}

    def _identify_key_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify the most important functions"""
        key_functions = []
        
        for entity in self.entities:
            if (entity.type == 'function' and 
                entity.docstring and 
                not entity.name.startswith('test_') and
                not entity.name.startswith('_')):
                
                key_functions.append({
                    "name": entity.name,
                    "module": self._path_to_module(entity.file_path),
                    "purpose": entity.docstring.split('\n')[0],
                    "location": f"{Path(entity.file_path).name}:{entity.line_number}"
                })
        
        return key_functions[:limit]

    def _build_class_hierarchy(self) -> Dict[str, Any]:
        """Build class hierarchy information"""
        classes = {}
        
        for entity in self.entities:
            if entity.type == 'class':
                classes[entity.name] = {
                    "module": self._path_to_module(entity.file_path),
                    "docstring": entity.docstring or "No description",
                    "location": f"{Path(entity.file_path).name}:{entity.line_number}"
                }
        
        return classes

    def _path_to_module(self, file_path: str) -> str:
        """Convert file path to module name"""
        path = Path(file_path)
        parts = path.with_suffix('').parts
        
        skip = {'src', '.', '..'}
        module_parts = [p for p in parts if p not in skip]
        
        return '.'.join(module_parts) if module_parts else path.stem

    def _infer_module_purpose(self, file_path: str, content: Dict) -> str:
        """Infer the purpose of a module from its contents"""
        filename = Path(file_path).stem.lower()
        
        if filename == '__init__':
            return "Package initialization"
        elif filename == '__main__':
            return "Entry point"
        elif 'test' in filename:
            return "Test module"
        elif 'config' in filename or 'settings' in filename:
            return "Configuration"
        elif 'model' in filename:
            return "Data models"
        elif 'util' in filename or 'helper' in filename:
            return "Utility functions"
        elif 'cli' in filename:
            return "Command-line interface"
        elif 'api' in filename:
            return "API endpoints"
        elif content['classes']:
            return f"Defines {len(content['classes'])} classes"
        elif content['functions']:
            return f"Contains {len(content['functions'])} functions"
        else:
            return "Module"

    def _extract_imports(self, file_path: str) -> List[str]:
        """Extract imports from a file (simplified)"""
        return []

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format summary as Markdown"""
        md = []
        md.append("# Codebase Summary\n")
        
        overview = summary["overview"]
        md.append("## Overview\n")
        md.append(f"- **Total Files**: {overview['total_files']}")
        md.append(f"- **Total Functions**: {overview['total_functions']}")
        md.append(f"- **Total Classes**: {overview['total_classes']}")
        md.append(f"- **Has Tests**: {'Yes' if overview['has_tests'] else 'No'}")
        md.append(f"- **Language**: {overview['main_language']}\n")
        
        if summary["feature_map"]:
            md.append("## Where to Find Features\n")
            for feature, locations in summary["feature_map"].items():
                if locations:
                    md.append(f"### {feature.replace('_', ' ').title()}")
                    for loc in locations[:5]:
                        md.append(f"- {loc}")
                    if len(locations) > 5:
                        md.append(f"- ...and {len(locations) - 5} more")
                    md.append("")
        
        if summary["key_functions"]:
            md.append("## Key Functions\n")
            for func in summary["key_functions"]:
                md.append(f"### `{func['name']}`")
                md.append(f"- **Module**: {func['module']}")
                md.append(f"- **Purpose**: {func['purpose']}")
                md.append(f"- **Location**: {func['location']}\n")
        
        md.append("## Modules\n")
        for module_name, module_info in sorted(summary["modules"].items()):
            md.append(f"### {module_name}")
            md.append(f"- **File**: `{module_info['file']}`")
            md.append(f"- **Purpose**: {module_info['purpose']}")
            
            if module_info['functions']:
                md.append(f"- **Functions** ({len(module_info['functions'])}):")
                for func in module_info['functions'][:5]:
                    md.append(f"  - `{func['name']}` - {func['purpose']}")
                if len(module_info['functions']) > 5:
                    md.append(f"  - ...and {len(module_info['functions']) - 5} more")
                    
            if module_info['classes']:
                md.append(f"- **Classes** ({len(module_info['classes'])}):")
                for cls in module_info['classes']:
                    md.append(f"  - `{cls['name']}` - {cls['docstring']}")
            
            md.append("")
        
        return '\n'.join(md)


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

@cli.command(name="generate-summary")
def generate_summary():
    """Generate a comprehensive codebase summary"""
    autodoc = SimpleAutodoc()
    autodoc.load()
    
    if not autodoc.entities:
        console.print("[red]No analyzed code found. Run 'autodoc analyze' first.[/red]")
        return
    
    summary = autodoc.generate_summary()
    
    if "error" in summary:
        console.print(f"[red]{summary['error']}[/red]")
        return
    
    # Format and display summary
    markdown_summary = autodoc.format_summary_markdown(summary)
    console.print(Markdown(markdown_summary))


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
