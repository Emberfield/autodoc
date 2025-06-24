"""
AST analysis functionality for extracting code entities from Python files.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rich.console import Console

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
    """Analyzes Python files using AST to extract code entities."""

    def analyze_file(self, file_path: Path) -> List[CodeEntity]:
        """Analyze a single Python file and extract code entities."""
        entities = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                    entities.append(
                        CodeEntity(
                            type="function",
                            name=node.name,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            docstring=ast.get_docstring(node),
                            code=f"{prefix} {node.name}(...)",
                        )
                    )
                elif isinstance(node, ast.ClassDef):
                    entities.append(
                        CodeEntity(
                            type="class",
                            name=node.name,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            docstring=ast.get_docstring(node),
                            code=f"class {node.name}",
                        )
                    )
        except Exception as e:
            console.print(f"[red]Error analyzing {file_path}: {e}[/red]")
        return entities

    def analyze_directory(self, path: Path) -> List[CodeEntity]:
        """Analyze all Python files in a directory."""
        console.print(f"[blue]Analyzing {path}...[/blue]")

        python_files = list(path.rglob("*.py"))
        python_files = [
            f
            for f in python_files
            if not any(
                skip in f.parts for skip in ["__pycache__", "venv", ".venv", "build", "dist"]
            )
        ]

        console.print(f"Found {len(python_files)} Python files")

        all_entities = []
        for file_path in python_files:
            entities = self.analyze_file(file_path)
            all_entities.extend(entities)

        console.print(f"Found {len(all_entities)} code entities")
        return all_entities
