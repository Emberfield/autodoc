#!/usr/bin/env python3
"""
Minimal Autodoc implementation that just works.
"""

import ast
import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

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


class OpenAIEmbedder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def embed(self, text: str) -> List[float]:
        async with aiohttp.ClientSession() as session:
            data = {"input": text[:8000], "model": "text-embedding-3-small"}
            async with session.post(
                "https://api.openai.com/v1/embeddings", headers=self.headers, json=data
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
            f
            for f in python_files
            if not any(
                skip in f.parts for skip in ["__pycache__", "venv", ".venv", "build", "dist"]
            )
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
            "functions": len([e for e in all_entities if e.type == "function"]),
            "classes": len([e for e in all_entities if e.type == "class"]),
            "has_embeddings": self.embedder is not None,
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
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Saved {len(self.entities)} entities to {path}[/green]")

    def load(self, path: str = "autodoc_cache.json"):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.entities = [CodeEntity(**entity) for entity in data["entities"]]
            console.print(f"[green]Loaded {len(self.entities)} entities from {path}[/green]")
        except FileNotFoundError:
            console.print(f"[yellow]No cache file found at {path}[/yellow]")

    def generate_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive codebase summary optimized for LLM context"""
        if not self.entities:
            return {"error": "No analyzed code found. Run 'analyze' first."}

        # Calculate comprehensive statistics
        stats = self._calculate_statistics()

        # Group entities by file with enhanced information
        files = {}
        for entity in self.entities:
            file_path = entity.file_path
            if file_path not in files:
                files[file_path] = {
                    "functions": [],
                    "classes": [],
                    "module_doc": self._extract_module_docstring(file_path),
                    "imports": self._extract_imports(file_path),
                    "complexity_score": 0,
                    "exports": [],
                }

            if entity.type == "function":
                func_info = {
                    "name": entity.name,
                    "line": entity.line_number,
                    "signature": self._extract_signature(entity),
                    "docstring": entity.docstring or "No description",
                    "purpose": self._extract_purpose(entity),
                    "complexity": self._estimate_complexity(entity),
                    "calls": self._extract_function_calls(entity),
                    "decorators": self._extract_decorators(entity),
                    "parameters": self._extract_parameters(entity),
                    "return_type": self._extract_return_type(entity),
                    "is_async": self._is_async_function(entity),
                    "is_generator": self._is_generator(entity),
                }
                files[file_path]["functions"].append(func_info)

                # Track public exports
                if not entity.name.startswith("_"):
                    files[file_path]["exports"].append(entity.name)

            elif entity.type == "class":
                class_info = {
                    "name": entity.name,
                    "line": entity.line_number,
                    "docstring": entity.docstring or "No description",
                    "base_classes": self._extract_base_classes(entity),
                    "methods": [
                        {
                            "name": m.name,
                            "line": m.line_number,
                            "signature": self._extract_signature(m),
                            "docstring": m.docstring or "No description",
                            "purpose": self._extract_purpose(m),
                            "is_static": self._is_static_method(m),
                            "is_class_method": self._is_class_method(m),
                            "is_property": self._is_property(m),
                            "is_private": m.name.startswith("_"),
                            "is_dunder": m.name.startswith("__") and m.name.endswith("__"),
                        }
                        for m in self._get_class_methods_detailed(entity, file_path)
                    ],
                    "attributes": self._extract_class_attributes(entity),
                    "is_abstract": self._is_abstract_class(entity),
                    "metaclass": self._extract_metaclass(entity),
                }
                files[file_path]["classes"].append(class_info)

                # Track public exports
                if not entity.name.startswith("_"):
                    files[file_path]["exports"].append(entity.name)

            # Update file complexity
            files[file_path]["complexity_score"] += (
                func_info.get("complexity", 1) if entity.type == "function" else 1
            )

        # Build comprehensive analysis
        dependencies = self._analyze_dependencies(files)
        feature_map = self._build_enhanced_feature_map()
        key_functions = self._identify_key_functions()
        class_hierarchy = self._build_detailed_class_hierarchy()
        entry_points = self._identify_entry_points()
        data_flows = self._analyze_data_flows()
        architecture_patterns = self._identify_architecture_patterns()
        build_system = self._analyze_build_system()
        test_system = self._analyze_test_system()
        ci_configuration = self._analyze_ci_configuration()
        deployment_info = self._analyze_deployment_configuration()

        # Create comprehensive summary
        summary = {
            "overview": {
                "total_files": len(files),
                "total_functions": len([e for e in self.entities if e.type == "function"]),
                "total_classes": len([e for e in self.entities if e.type == "class"]),
                "has_tests": any("test" in Path(f).name for f in files.keys()),
                "main_language": "Python",
                "analysis_date": datetime.now().isoformat(),
                "tool_version": "autodoc 0.1.0",
                "total_lines_analyzed": sum(
                    len(open(f, "r", encoding="utf-8", errors="ignore").readlines())
                    for f in files.keys()
                    if Path(f).exists()
                ),
                "complexity_distribution": self._calculate_complexity_distribution(files),
            },
            "statistics": stats,
            "modules": {},
            "feature_map": feature_map,
            "key_functions": key_functions,
            "class_hierarchy": class_hierarchy,
            "dependencies": dependencies,
            "entry_points": entry_points,
            "data_flows": data_flows,
            "architecture_patterns": architecture_patterns,
            "project_structure": self._analyze_project_structure(files),
            "code_quality_metrics": self._calculate_code_quality_metrics(files),
            "build_system": build_system,
            "test_system": test_system,
            "ci_configuration": ci_configuration,
            "deployment_info": deployment_info,
        }

        # Process each file with detailed module information
        for file_path, content in files.items():
            module_name = self._path_to_module(file_path)
            summary["modules"][module_name] = {
                "file_path": file_path,
                "relative_path": (
                    str(Path(file_path).relative_to(Path.cwd(), walk_up=True))
                    if Path(file_path).is_absolute()
                    else file_path
                ),
                "purpose": self._infer_detailed_module_purpose(file_path, content),
                "module_docstring": content["module_doc"],
                "functions": content["functions"],
                "classes": content["classes"],
                "imports": content["imports"],
                "exports": content["exports"],
                "complexity_score": content["complexity_score"],
                "file_size_bytes": (
                    Path(file_path).stat().st_size if Path(file_path).exists() else 0
                ),
                "last_modified": (
                    Path(file_path).stat().st_mtime if Path(file_path).exists() else None
                ),
                "dependencies": dependencies.get(module_name, {}).get("imports", []),
                "dependents": dependencies.get(module_name, {}).get("used_by", []),
            }

        return summary

    def _extract_purpose(self, entity: CodeEntity) -> str:
        """Extract purpose from function name and docstring"""
        name_lower = entity.name.lower()
        if "test_" in name_lower:
            return "Test function"
        elif "get_" in name_lower or "fetch_" in name_lower:
            return "Retrieves data"
        elif "set_" in name_lower or "update_" in name_lower:
            return "Updates data"
        elif "create_" in name_lower or "make_" in name_lower:
            return "Creates new objects"
        elif "delete_" in name_lower or "remove_" in name_lower:
            return "Removes data"
        elif "is_" in name_lower or "has_" in name_lower:
            return "Checks condition"
        elif entity.docstring:
            return entity.docstring.split("\n")[0]
        else:
            return "General purpose function"

    def _get_class_methods(self, class_entity: CodeEntity, file_path: str) -> List[str]:
        """Get methods belonging to a class"""
        methods = []
        class_line = class_entity.line_number

        for entity in self.entities:
            if (
                entity.type == "function"
                and entity.file_path == file_path
                and entity.line_number > class_line
            ):
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
            "utilities": [],
        }

        for entity in self.entities:
            name_lower = entity.name.lower()
            file_lower = entity.file_path.lower()

            if any(auth in name_lower for auth in ["auth", "login", "token", "permission"]):
                feature_map["authentication"].append(
                    f"{entity.name} in {Path(entity.file_path).name}"
                )

            if any(db in name_lower for db in ["db", "database", "query", "model", "orm"]):
                feature_map["database"].append(f"{entity.name} in {Path(entity.file_path).name}")

            if any(api in name_lower for api in ["api", "endpoint", "route", "view"]):
                feature_map["api_endpoints"].append(
                    f"{entity.name} in {Path(entity.file_path).name}"
                )

            if any(proc in name_lower for proc in ["process", "transform", "parse", "analyze"]):
                feature_map["data_processing"].append(
                    f"{entity.name} in {Path(entity.file_path).name}"
                )

            if any(file_op in name_lower for file_op in ["read", "write", "save", "load", "file"]):
                feature_map["file_operations"].append(
                    f"{entity.name} in {Path(entity.file_path).name}"
                )

            if "test" in file_lower or "test_" in name_lower:
                feature_map["testing"].append(f"{entity.name} in {Path(entity.file_path).name}")

            if any(conf in file_lower for conf in ["config", "settings", "env"]):
                feature_map["configuration"].append(
                    f"{entity.name} in {Path(entity.file_path).name}"
                )

            if any(util in file_lower for util in ["util", "helper", "common"]):
                feature_map["utilities"].append(f"{entity.name} in {Path(entity.file_path).name}")

        return {k: v for k, v in feature_map.items() if v}

    def _identify_key_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify the most important functions"""
        key_functions = []

        for entity in self.entities:
            if (
                entity.type == "function"
                and entity.docstring
                and not entity.name.startswith("test_")
                and not entity.name.startswith("_")
            ):

                key_functions.append(
                    {
                        "name": entity.name,
                        "module": self._path_to_module(entity.file_path),
                        "purpose": entity.docstring.split("\n")[0],
                        "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                    }
                )

        return key_functions[:limit]

    def _build_class_hierarchy(self) -> Dict[str, Any]:
        """Build class hierarchy information"""
        classes = {}

        for entity in self.entities:
            if entity.type == "class":
                classes[entity.name] = {
                    "module": self._path_to_module(entity.file_path),
                    "docstring": entity.docstring or "No description",
                    "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                }

        return classes

    def _path_to_module(self, file_path: str) -> str:
        """Convert file path to module name"""
        path = Path(file_path)
        parts = path.with_suffix("").parts

        skip = {"src", ".", ".."}
        module_parts = [p for p in parts if p not in skip]

        return ".".join(module_parts) if module_parts else path.stem

    def _infer_module_purpose(self, file_path: str, content: Dict) -> str:
        """Infer the purpose of a module from its contents"""
        filename = Path(file_path).stem.lower()

        if filename == "__init__":
            return "Package initialization"
        elif filename == "__main__":
            return "Entry point"
        elif "test" in filename:
            return "Test module"
        elif "config" in filename or "settings" in filename:
            return "Configuration"
        elif "model" in filename:
            return "Data models"
        elif "util" in filename or "helper" in filename:
            return "Utility functions"
        elif "cli" in filename:
            return "Command-line interface"
        elif "api" in filename:
            return "API endpoints"
        elif content["classes"]:
            return f"Defines {len(content['classes'])} classes"
        elif content["functions"]:
            return f"Contains {len(content['functions'])} functions"
        else:
            return "Module"

    def _extract_imports(self, file_path: str) -> List[str]:
        """Extract imports from a file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")

            return imports
        except Exception:
            return []

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive codebase statistics"""
        stats = {
            "function_count": len([e for e in self.entities if e.type == "function"]),
            "class_count": len([e for e in self.entities if e.type == "class"]),
            "total_entities": len(self.entities),
            "files_analyzed": len(set(e.file_path for e in self.entities)),
            "avg_functions_per_file": 0,
            "avg_classes_per_file": 0,
            "private_functions": len(
                [e for e in self.entities if e.type == "function" and e.name.startswith("_")]
            ),
            "public_functions": len(
                [e for e in self.entities if e.type == "function" and not e.name.startswith("_")]
            ),
            "test_functions": len(
                [e for e in self.entities if e.type == "function" and "test_" in e.name.lower()]
            ),
            "documented_entities": len([e for e in self.entities if e.docstring]),
            "documentation_coverage": 0,
        }

        if stats["files_analyzed"] > 0:
            stats["avg_functions_per_file"] = stats["function_count"] / stats["files_analyzed"]
            stats["avg_classes_per_file"] = stats["class_count"] / stats["files_analyzed"]

        if stats["total_entities"] > 0:
            stats["documentation_coverage"] = stats["documented_entities"] / stats["total_entities"]

        return stats

    def _extract_module_docstring(self, file_path: str) -> Optional[str]:
        """Extract module-level docstring"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            ):
                return tree.body[0].value.value
        except Exception:
            pass
        return None

    def _extract_signature(self, entity: CodeEntity) -> str:
        """Extract function/method signature"""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            if entity.line_number <= len(lines):
                line = lines[entity.line_number - 1].strip()
                if line.startswith("def ") or line.startswith("async def "):
                    return line
        except Exception:
            pass
        return f"def {entity.name}(...):"

    def _estimate_complexity(self, entity: CodeEntity) -> int:
        """Estimate code complexity based on entity name and context"""
        complexity = 1
        name = entity.name.lower()

        # Add complexity for certain patterns
        if any(pattern in name for pattern in ["_complex", "_handler", "_processor", "_manager"]):
            complexity += 2
        if entity.docstring and len(entity.docstring.split()) > 20:
            complexity += 1
        if any(pattern in name for pattern in ["create", "update", "delete", "process"]):
            complexity += 1

        return complexity

    def _extract_function_calls(self, entity: CodeEntity) -> List[str]:
        """Extract function calls made by this entity (simplified)"""
        # This would require more sophisticated AST analysis
        # For now, return empty list
        return []

    def _extract_decorators(self, entity: CodeEntity) -> List[str]:
        """Extract decorators for functions/methods"""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            decorators = []
            start_line = max(0, entity.line_number - 5)
            for i in range(start_line, min(entity.line_number, len(lines))):
                line = lines[i].strip()
                if line.startswith("@"):
                    decorators.append(line)

            return decorators
        except Exception:
            return []

    def _extract_parameters(self, entity: CodeEntity) -> List[Dict[str, str]]:
        """Extract function parameters"""
        # Simplified implementation
        signature = self._extract_signature(entity)
        params = []

        # Extract parameters from signature (basic regex)
        match = re.search(r"\((.*?)\):", signature)
        if match:
            param_str = match.group(1)
            if param_str.strip():
                for param in param_str.split(","):
                    param = param.strip()
                    if param and param != "self" and param != "cls":
                        params.append(
                            {"name": param.split("=")[0].strip(), "default": "=" in param}
                        )

        return params

    def _extract_return_type(self, entity: CodeEntity) -> Optional[str]:
        """Extract return type annotation"""
        signature = self._extract_signature(entity)
        match = re.search(r"->\s*([^:]+):", signature)
        return match.group(1).strip() if match else None

    def _is_async_function(self, entity: CodeEntity) -> bool:
        """Check if function is async"""
        signature = self._extract_signature(entity)
        return signature.strip().startswith("async def")

    def _is_generator(self, entity: CodeEntity) -> bool:
        """Check if function is a generator (simplified)"""
        # Would need AST analysis to detect yield statements
        return False

    def _get_class_methods_detailed(
        self, class_entity: CodeEntity, file_path: str
    ) -> List[CodeEntity]:
        """Get detailed methods belonging to a class"""
        methods = []
        class_line = class_entity.line_number

        for entity in self.entities:
            if (
                entity.type == "function"
                and entity.file_path == file_path
                and entity.line_number > class_line
            ):
                methods.append(entity)
                if len(methods) > 20:  # Limit to prevent excessive data
                    break

        return methods

    def _extract_base_classes(self, entity: CodeEntity) -> List[str]:
        """Extract base classes"""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ClassDef)
                    and node.name == entity.name
                    and node.lineno == entity.line_number
                ):
                    return [ast.unparse(base) for base in node.bases]
        except Exception:
            pass
        return []

    def _is_static_method(self, entity: CodeEntity) -> bool:
        """Check if method is static"""
        decorators = self._extract_decorators(entity)
        return any("@staticmethod" in dec for dec in decorators)

    def _is_class_method(self, entity: CodeEntity) -> bool:
        """Check if method is a class method"""
        decorators = self._extract_decorators(entity)
        return any("@classmethod" in dec for dec in decorators)

    def _is_property(self, entity: CodeEntity) -> bool:
        """Check if method is a property"""
        decorators = self._extract_decorators(entity)
        return any("@property" in dec for dec in decorators)

    def _extract_class_attributes(self, entity: CodeEntity) -> List[Dict[str, Any]]:
        """Extract class attributes"""
        # Simplified implementation
        return []

    def _is_abstract_class(self, entity: CodeEntity) -> bool:
        """Check if class is abstract"""
        decorators = self._extract_decorators(entity)
        return any("ABC" in dec or "abstractmethod" in dec for dec in decorators)

    def _extract_metaclass(self, entity: CodeEntity) -> Optional[str]:
        """Extract metaclass information"""
        # Would need AST analysis
        return None

    def _analyze_dependencies(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze module dependencies"""
        dependencies = {}

        for file_path, content in files.items():
            module_name = self._path_to_module(file_path)
            dependencies[module_name] = {
                "imports": content["imports"],
                "used_by": [],
                "complexity": content["complexity_score"],
            }

        return dependencies

    def _build_enhanced_feature_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build enhanced feature map with detailed locations"""
        feature_map = {
            "authentication": [],
            "database": [],
            "api_endpoints": [],
            "data_processing": [],
            "file_operations": [],
            "testing": [],
            "configuration": [],
            "utilities": [],
            "cli_commands": [],
            "async_operations": [],
        }

        for entity in self.entities:
            name_lower = entity.name.lower()
            file_lower = entity.file_path.lower()

            entity_info = {
                "name": entity.name,
                "type": entity.type,
                "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                "module": self._path_to_module(entity.file_path),
                "purpose": self._extract_purpose(entity),
            }

            if any(auth in name_lower for auth in ["auth", "login", "token", "permission"]):
                feature_map["authentication"].append(entity_info)

            if any(db in name_lower for db in ["db", "database", "query", "model", "orm"]):
                feature_map["database"].append(entity_info)

            if any(api in name_lower for api in ["api", "endpoint", "route", "view"]):
                feature_map["api_endpoints"].append(entity_info)

            if any(proc in name_lower for proc in ["process", "transform", "parse", "analyze"]):
                feature_map["data_processing"].append(entity_info)

            if any(file_op in name_lower for file_op in ["read", "write", "save", "load", "file"]):
                feature_map["file_operations"].append(entity_info)

            if "test" in file_lower or "test_" in name_lower:
                feature_map["testing"].append(entity_info)

            if any(conf in file_lower for conf in ["config", "settings", "env"]):
                feature_map["configuration"].append(entity_info)

            if any(util in file_lower for util in ["util", "helper", "common"]):
                feature_map["utilities"].append(entity_info)

            if "cli" in file_lower or any(cli in name_lower for cli in ["command", "click"]):
                feature_map["cli_commands"].append(entity_info)

            if self._is_async_function(entity):
                feature_map["async_operations"].append(entity_info)

        return {k: v for k, v in feature_map.items() if v}

    def _build_detailed_class_hierarchy(self) -> Dict[str, Any]:
        """Build detailed class hierarchy information"""
        classes = {}

        for entity in self.entities:
            if entity.type == "class":
                classes[entity.name] = {
                    "module": self._path_to_module(entity.file_path),
                    "file_path": entity.file_path,
                    "line_number": entity.line_number,
                    "docstring": entity.docstring or "No description",
                    "base_classes": self._extract_base_classes(entity),
                    "methods": [
                        m.name for m in self._get_class_methods_detailed(entity, entity.file_path)
                    ],
                    "is_abstract": self._is_abstract_class(entity),
                    "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                }

        return classes

    def _identify_entry_points(self) -> List[Dict[str, Any]]:
        """Identify entry points in the codebase"""
        entry_points = []

        for entity in self.entities:
            if entity.type == "function":
                # Main functions
                if entity.name == "main":
                    entry_points.append(
                        {
                            "type": "main_function",
                            "name": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "module": self._path_to_module(entity.file_path),
                        }
                    )

                # CLI commands
                decorators = self._extract_decorators(entity)
                if any("@click.command" in dec or "@cli.command" in dec for dec in decorators):
                    entry_points.append(
                        {
                            "type": "cli_command",
                            "name": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "module": self._path_to_module(entity.file_path),
                        }
                    )

        return entry_points

    def _analyze_data_flows(self) -> List[Dict[str, Any]]:
        """Analyze data flows in the codebase"""
        # Simplified implementation
        flows = []

        # Identify common patterns
        for entity in self.entities:
            if entity.type == "function":
                name = entity.name.lower()
                if "load" in name or "read" in name:
                    flows.append(
                        {
                            "type": "data_input",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Loads/reads data",
                        }
                    )
                elif "save" in name or "write" in name:
                    flows.append(
                        {
                            "type": "data_output",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Saves/writes data",
                        }
                    )
                elif "process" in name or "transform" in name:
                    flows.append(
                        {
                            "type": "data_processing",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Processes/transforms data",
                        }
                    )

        return flows

    def _identify_architecture_patterns(self) -> List[Dict[str, Any]]:
        """Identify architectural patterns in the codebase"""
        patterns = []

        # Check for common patterns
        class_names = [e.name for e in self.entities if e.type == "class"]
        function_names = [e.name for e in self.entities if e.type == "function"]

        # Singleton pattern
        if any("singleton" in name.lower() for name in class_names):
            patterns.append({"pattern": "Singleton", "confidence": "high"})

        # Factory pattern
        if any("factory" in name.lower() for name in class_names + function_names):
            patterns.append({"pattern": "Factory", "confidence": "medium"})

        # Observer pattern
        if any("observer" in name.lower() or "listener" in name.lower() for name in class_names):
            patterns.append({"pattern": "Observer", "confidence": "medium"})

        # Command pattern
        if any("command" in name.lower() for name in class_names):
            patterns.append({"pattern": "Command", "confidence": "medium"})

        return patterns

    def _analyze_project_structure(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall project structure"""
        structure = {
            "directories": {},
            "file_types": {},
            "organization_score": 0,
        }

        # Analyze directory structure
        for file_path in files.keys():
            path = Path(file_path)
            dir_name = str(path.parent)

            if dir_name not in structure["directories"]:
                structure["directories"][dir_name] = {"file_count": 0, "functions": 0, "classes": 0}

            structure["directories"][dir_name]["file_count"] += 1
            structure["directories"][dir_name]["functions"] += len(files[file_path]["functions"])
            structure["directories"][dir_name]["classes"] += len(files[file_path]["classes"])

        # Analyze file types
        for file_path in files.keys():
            ext = Path(file_path).suffix
            structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

        return structure

    def _calculate_code_quality_metrics(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate code quality metrics"""
        total_functions = sum(len(f["functions"]) for f in files.values())
        documented_functions = sum(
            len([func for func in f["functions"] if func["docstring"] != "No description"])
            for f in files.values()
        )

        return {
            "documentation_coverage": (
                documented_functions / total_functions if total_functions > 0 else 0
            ),
            "average_complexity": (
                sum(f["complexity_score"] for f in files.values()) / len(files) if files else 0
            ),
            "public_api_ratio": (
                sum(len(f["exports"]) for f in files.values()) / total_functions
                if total_functions > 0
                else 0
            ),
        }

    def _calculate_complexity_distribution(self, files: Dict[str, Any]) -> Dict[str, int]:
        """Calculate complexity distribution across files"""
        distribution = {"low": 0, "medium": 0, "high": 0}

        for file_data in files.values():
            score = file_data["complexity_score"]
            if score <= 5:
                distribution["low"] += 1
            elif score <= 15:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1

        return distribution

    def _analyze_build_system(self) -> Dict[str, Any]:
        """Analyze build system configuration and tools"""
        build_info = {
            "build_tools": [],
            "package_managers": [],
            "configuration_files": [],
            "build_commands": [],
            "dependencies": {},
            "scripts": {},
        }

        cwd = Path.cwd()

        # Check for common Python build files
        build_files = {
            "pyproject.toml": "Modern Python packaging (PEP 518)",
            "setup.py": "Traditional Python setup",
            "setup.cfg": "Setup configuration",
            "requirements.txt": "Pip requirements",
            "requirements-dev.txt": "Development requirements",
            "Pipfile": "Pipenv configuration",
            "poetry.lock": "Poetry lock file",
            "hatch.toml": "Hatch configuration",
            "tox.ini": "Tox testing configuration",
            "Makefile": "Make build system",
            "noxfile.py": "Nox testing configuration",
        }

        for filename, description in build_files.items():
            file_path = cwd / filename
            if file_path.exists():
                build_info["configuration_files"].append(
                    {"file": filename, "description": description, "size": file_path.stat().st_size}
                )

        # Detect build tools and package managers
        if (cwd / "pyproject.toml").exists():
            build_info["build_tools"].append("setuptools/build")
            build_info["package_managers"].append("pip")

            # Parse pyproject.toml for more details
            try:
                try:
                    import tomllib
                except ImportError:
                    tomllib = None
                if tomllib:
                    with open(cwd / "pyproject.toml", "rb") as f:
                        pyproject = tomllib.load(f)

                    if "tool" in pyproject:
                        if "hatch" in pyproject["tool"]:
                            build_info["build_tools"].append("hatch")
                        if "poetry" in pyproject["tool"]:
                            build_info["build_tools"].append("poetry")
                            build_info["package_managers"].append("poetry")
                        if "flit" in pyproject["tool"]:
                            build_info["build_tools"].append("flit")
                        if "setuptools" in pyproject["tool"]:
                            build_info["build_tools"].append("setuptools")

                    # Extract scripts and commands
                    if "project" in pyproject and "scripts" in pyproject["project"]:
                        build_info["scripts"] = pyproject["project"]["scripts"]

                    # Extract dependencies
                    if "project" in pyproject and "dependencies" in pyproject["project"]:
                        build_info["dependencies"]["runtime"] = pyproject["project"]["dependencies"]

            except Exception:
                pass

        if (cwd / "setup.py").exists():
            build_info["build_tools"].append("setuptools")
            build_info["package_managers"].append("pip")

        if (cwd / "Pipfile").exists():
            build_info["package_managers"].append("pipenv")

        if (cwd / "poetry.lock").exists():
            build_info["build_tools"].append("poetry")
            build_info["package_managers"].append("poetry")

        # Check for common build commands in scripts or documentation
        common_commands = [
            "python -m build",
            "pip install -e .",
            "hatch build",
            "poetry build",
            "make build",
            "python setup.py build",
            "python setup.py sdist bdist_wheel",
        ]

        # Look for commands in common files
        command_files = ["Makefile", "README.md", "README.rst", "DEVELOPMENT.md", "CONTRIBUTING.md"]
        for cmd_file in command_files:
            if (cwd / cmd_file).exists():
                try:
                    with open(cwd / cmd_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        for cmd in common_commands:
                            if cmd.lower() in content:
                                build_info["build_commands"].append(cmd)
                except Exception:
                    pass

        return build_info

    def _analyze_test_system(self) -> Dict[str, Any]:
        """Analyze testing configuration and framework"""
        test_info = {
            "test_frameworks": [],
            "test_runners": [],
            "configuration_files": [],
            "test_commands": [],
            "test_directories": [],
            "coverage_tools": [],
            "test_files_count": 0,
            "test_functions_count": 0,
        }

        cwd = Path.cwd()

        # Count test files and functions from already analyzed entities
        test_files = set()
        for entity in self.entities:
            file_path = Path(entity.file_path)
            if (
                "test" in file_path.name.lower()
                or "test" in str(file_path.parent).lower()
                or entity.name.startswith("test_")
            ):
                test_files.add(entity.file_path)
                if entity.name.startswith("test_"):
                    test_info["test_functions_count"] += 1

        test_info["test_files_count"] = len(test_files)

        # Find test directories
        for test_file in test_files:
            test_dir = str(Path(test_file).parent)
            if test_dir not in test_info["test_directories"]:
                test_info["test_directories"].append(test_dir)

        # Check for testing configuration files
        test_config_files = {
            "pytest.ini": "pytest configuration",
            "pyproject.toml": "pytest/testing configuration",
            "tox.ini": "tox multi-environment testing",
            "noxfile.py": "nox testing sessions",
            ".coveragerc": "coverage.py configuration",
            "coverage.ini": "coverage configuration",
            "conftest.py": "pytest fixtures and configuration",
        }

        for filename, description in test_config_files.items():
            file_path = cwd / filename
            if file_path.exists():
                test_info["configuration_files"].append(
                    {"file": filename, "description": description}
                )

        # Detect test frameworks and runners
        # framework_indicators = {
        #     "pytest": ["pytest.ini", "conftest.py", "@pytest"],
        #     "unittest": ["unittest", "TestCase"],
        #     "nose": ["nosetests", "nose"],
        #     "doctest": ["doctest"],
        # }

        # Check imports and code for framework usage
        for entity in self.entities:
            if entity.type == "function" and entity.name.startswith("test_"):
                # This suggests pytest or unittest
                if "pytest" not in test_info["test_frameworks"]:
                    test_info["test_frameworks"].append("pytest")  # Default assumption

        # Check for specific files that indicate frameworks
        if (cwd / "conftest.py").exists() or (cwd / "pytest.ini").exists():
            test_info["test_frameworks"].append("pytest")
            test_info["test_runners"].append("pytest")

        if (cwd / "tox.ini").exists():
            test_info["test_runners"].append("tox")

        if (cwd / "noxfile.py").exists():
            test_info["test_runners"].append("nox")

        # Check for coverage tools
        coverage_files = [".coveragerc", "coverage.ini"]
        for cov_file in coverage_files:
            if (cwd / cov_file).exists():
                test_info["coverage_tools"].append("coverage.py")
                break

        # Common test commands
        common_test_commands = [
            "pytest",
            "python -m pytest",
            "hatch run test",
            "poetry run pytest",
            "tox",
            "nox",
            "python -m unittest",
            "make test",
        ]

        # Look for test commands in documentation and scripts
        command_files = ["Makefile", "README.md", "README.rst", "pyproject.toml", "DEVELOPMENT.md"]
        for cmd_file in command_files:
            if (cwd / cmd_file).exists():
                try:
                    with open(cwd / cmd_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        for cmd in common_test_commands:
                            if cmd.lower() in content and cmd not in test_info["test_commands"]:
                                test_info["test_commands"].append(cmd)
                except Exception:
                    pass

        return test_info

    def _analyze_ci_configuration(self) -> Dict[str, Any]:
        """Analyze CI/CD configuration"""
        ci_info = {
            "has_ci": False,
            "platforms": [],
            "workflows": [],
            "configuration_files": [],
            "triggers": [],
            "jobs": [],
            "environments": [],
        }

        cwd = Path.cwd()

        # GitHub Actions
        github_workflows_dir = cwd / ".github" / "workflows"
        if github_workflows_dir.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("GitHub Actions")

            workflow_files = list(github_workflows_dir.glob("*.yml")) + list(
                github_workflows_dir.glob("*.yaml")
            )
            for workflow_file in workflow_files:
                ci_info["configuration_files"].append(
                    {
                        "file": str(workflow_file.relative_to(cwd)),
                        "platform": "GitHub Actions",
                        "name": workflow_file.stem,
                    }
                )

                # Try to parse workflow file for more details
                try:
                    import yaml

                    with open(workflow_file, "r", encoding="utf-8") as f:
                        workflow_data = yaml.safe_load(f)

                    if isinstance(workflow_data, dict):
                        # Extract workflow info
                        workflow_info = {
                            "name": workflow_data.get("name", workflow_file.stem),
                            "triggers": (
                                list(workflow_data.get("on", {}).keys())
                                if isinstance(workflow_data.get("on"), dict)
                                else [workflow_data.get("on", "unknown")]
                            ),
                            "jobs": list(workflow_data.get("jobs", {}).keys()),
                        }
                        ci_info["workflows"].append(workflow_info)

                        # Collect triggers
                        for trigger in workflow_info["triggers"]:
                            if trigger not in ci_info["triggers"]:
                                ci_info["triggers"].append(trigger)

                        # Collect jobs
                        for job in workflow_info["jobs"]:
                            if job not in ci_info["jobs"]:
                                ci_info["jobs"].append(job)

                except Exception:
                    # If YAML parsing fails, still record the file
                    ci_info["workflows"].append(
                        {"name": workflow_file.stem, "triggers": ["unknown"], "jobs": ["unknown"]}
                    )

        # GitLab CI
        gitlab_ci_file = cwd / ".gitlab-ci.yml"
        if gitlab_ci_file.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("GitLab CI")
            ci_info["configuration_files"].append(
                {"file": ".gitlab-ci.yml", "platform": "GitLab CI"}
            )

        # Travis CI
        travis_files = [".travis.yml", ".travis.yaml"]
        for travis_file in travis_files:
            if (cwd / travis_file).exists():
                ci_info["has_ci"] = True
                ci_info["platforms"].append("Travis CI")
                ci_info["configuration_files"].append(
                    {"file": travis_file, "platform": "Travis CI"}
                )
                break

        # Circle CI
        circle_ci_dir = cwd / ".circleci"
        if circle_ci_dir.exists() and (circle_ci_dir / "config.yml").exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("Circle CI")
            ci_info["configuration_files"].append(
                {"file": ".circleci/config.yml", "platform": "Circle CI"}
            )

        # Azure Pipelines
        azure_files = ["azure-pipelines.yml", "azure-pipelines.yaml", ".azure-pipelines.yml"]
        for azure_file in azure_files:
            if (cwd / azure_file).exists():
                ci_info["has_ci"] = True
                ci_info["platforms"].append("Azure Pipelines")
                ci_info["configuration_files"].append(
                    {"file": azure_file, "platform": "Azure Pipelines"}
                )
                break

        # Jenkins
        jenkins_file = cwd / "Jenkinsfile"
        if jenkins_file.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("Jenkins")
            ci_info["configuration_files"].append({"file": "Jenkinsfile", "platform": "Jenkins"})

        return ci_info

    def _analyze_deployment_configuration(self) -> Dict[str, Any]:
        """Analyze deployment and distribution configuration"""
        deploy_info = {
            "deployment_platforms": [],
            "containerization": [],
            "configuration_files": [],
            "package_distribution": [],
            "hosting_indicators": [],
        }

        cwd = Path.cwd()

        # Docker
        docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]
        for docker_file in docker_files:
            if (cwd / docker_file).exists():
                if "Docker" not in deploy_info["containerization"]:
                    deploy_info["containerization"].append("Docker")
                deploy_info["configuration_files"].append(
                    {"file": docker_file, "type": "containerization", "platform": "Docker"}
                )

        # Kubernetes
        k8s_patterns = ["*.yaml", "*.yml"]
        # k8s_keywords = ["apiVersion", "kind: Deployment", "kind: Service"]
        for pattern in k8s_patterns:
            for yaml_file in cwd.glob(pattern):
                if yaml_file.name.startswith(("k8s", "kubernetes")) or "k8s" in str(
                    yaml_file.parent
                ):
                    if "Kubernetes" not in deploy_info["containerization"]:
                        deploy_info["containerization"].append("Kubernetes")
                    break

        # Heroku
        heroku_files = ["Procfile", "app.json", "runtime.txt"]
        for heroku_file in heroku_files:
            if (cwd / heroku_file).exists():
                if "Heroku" not in deploy_info["deployment_platforms"]:
                    deploy_info["deployment_platforms"].append("Heroku")
                deploy_info["configuration_files"].append(
                    {"file": heroku_file, "type": "deployment", "platform": "Heroku"}
                )

        # Vercel
        vercel_files = ["vercel.json", "now.json"]
        for vercel_file in vercel_files:
            if (cwd / vercel_file).exists():
                if "Vercel" not in deploy_info["deployment_platforms"]:
                    deploy_info["deployment_platforms"].append("Vercel")
                deploy_info["configuration_files"].append(
                    {"file": vercel_file, "type": "deployment", "platform": "Vercel"}
                )

        # Package distribution
        if (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
            deploy_info["package_distribution"].append("PyPI")

        # Look for publishing workflows in CI
        github_workflows_dir = cwd / ".github" / "workflows"
        if github_workflows_dir.exists():
            for workflow_file in github_workflows_dir.glob("*.yml"):
                try:
                    with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        if "pypi" in content or "twine" in content or "python -m build" in content:
                            if "PyPI" not in deploy_info["package_distribution"]:
                                deploy_info["package_distribution"].append("PyPI")
                        if "docker" in content and "push" in content:
                            if "Docker Registry" not in deploy_info["package_distribution"]:
                                deploy_info["package_distribution"].append("Docker Registry")
                except Exception:
                    pass

        return deploy_info

    def _infer_detailed_module_purpose(self, file_path: str, content: Dict[str, Any]) -> str:
        """Infer detailed module purpose"""
        filename = Path(file_path).stem.lower()

        if filename == "__init__":
            return "Package initialization and exports"
        elif filename == "__main__":
            return "Application entry point"
        elif "test" in filename:
            return f"Test module with {len(content['functions'])} test functions"
        elif "config" in filename or "settings" in filename:
            return "Configuration and settings management"
        elif "model" in filename:
            return f"Data models and schemas ({len(content['classes'])} classes)"
        elif "util" in filename or "helper" in filename:
            return f"Utility functions and helpers ({len(content['functions'])} functions)"
        elif "cli" in filename:
            return f"Command-line interface with {len(content['functions'])} commands"
        elif "api" in filename:
            return f"API endpoints and handlers ({len(content['functions'])} endpoints)"
        elif content["classes"]:
            return f"Module defining {len(content['classes'])} classes and {len(content['functions'])} functions"
        elif content["functions"]:
            return f"Function module with {len(content['functions'])} functions"
        else:
            return "General purpose module"

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format comprehensive summary as detailed Markdown optimized for LLM context"""
        md = []

        # Header with metadata
        md.append("# Comprehensive Codebase Documentation")
        md.append(
            f"*Generated on {summary['overview']['analysis_date']} with {summary['overview']['tool_version']}*\n"
        )

        # Executive Summary
        overview = summary["overview"]
        md.append("## Executive Summary")
        md.append(
            f"This codebase contains {overview['total_functions']} functions and {overview['total_classes']} classes across {overview['total_files']} files, written primarily in {overview['main_language']}."
        )
        md.append(f"Total lines analyzed: {overview['total_lines_analyzed']:,}")
        md.append(f"Testing coverage: {'Comprehensive' if overview['has_tests'] else 'Limited'}")

        # Add build system summary
        if summary.get("build_system") and summary["build_system"].get("build_tools"):
            md.append(f"Build system: {', '.join(summary['build_system']['build_tools'])}")

        if summary.get("ci_configuration") and summary["ci_configuration"].get("has_ci"):
            platforms = summary["ci_configuration"].get("platforms", [])
            md.append(f"CI/CD: {', '.join(platforms) if platforms else 'Configured'}")
        else:
            md.append("CI/CD: Not configured")

        # Statistics and Quality Metrics
        if "statistics" in summary:
            stats = summary["statistics"]
            md.append("\n## Codebase Statistics")
            md.append(f"- **Total Entities**: {stats['total_entities']}")
            md.append(f"- **Public Functions**: {stats['public_functions']}")
            md.append(f"- **Private Functions**: {stats['private_functions']}")
            md.append(f"- **Test Functions**: {stats['test_functions']}")
            md.append(f"- **Documentation Coverage**: {stats['documentation_coverage']:.1%}")
            md.append(f"- **Average Functions per File**: {stats['avg_functions_per_file']:.1f}")
            md.append(f"- **Average Classes per File**: {stats['avg_classes_per_file']:.1f}")

        if "code_quality_metrics" in summary:
            quality = summary["code_quality_metrics"]
            md.append("\n### Code Quality Metrics")
            md.append(f"- **Documentation Coverage**: {quality['documentation_coverage']:.1%}")
            md.append(f"- **Average Complexity**: {quality['average_complexity']:.1f}")
            md.append(f"- **Public API Ratio**: {quality['public_api_ratio']:.1%}")

        # Build System and Tooling
        if summary.get("build_system"):
            build = summary["build_system"]
            md.append("\n## Build System and Tooling")

            if build.get("build_tools"):
                md.append(f"**Build Tools**: {', '.join(build['build_tools'])}")

            if build.get("package_managers"):
                md.append(f"**Package Managers**: {', '.join(build['package_managers'])}")

            if build.get("configuration_files"):
                md.append("\n**Configuration Files**:")
                for config in build["configuration_files"]:
                    md.append(f"- `{config['file']}` - {config['description']}")

            if build.get("build_commands"):
                md.append("\n**Build Commands**:")
                for cmd in build["build_commands"]:
                    md.append(f"- `{cmd}`")

            if build.get("scripts"):
                md.append("\n**Project Scripts**:")
                for script, command in build["scripts"].items():
                    md.append(f"- `{script}`: {command}")

        # Testing System
        if summary.get("test_system"):
            test = summary["test_system"]
            md.append("\n## Testing System")
            md.append(f"**Test Files**: {test.get('test_files_count', 0)} files")
            md.append(f"**Test Functions**: {test.get('test_functions_count', 0)} functions")

            if test.get("test_frameworks"):
                md.append(f"**Testing Frameworks**: {', '.join(test['test_frameworks'])}")

            if test.get("test_runners"):
                md.append(f"**Test Runners**: {', '.join(test['test_runners'])}")

            if test.get("coverage_tools"):
                md.append(f"**Coverage Tools**: {', '.join(test['coverage_tools'])}")

            if test.get("test_commands"):
                md.append("\n**Test Commands**:")
                for cmd in test["test_commands"]:
                    md.append(f"- `{cmd}`")

            if test.get("test_directories"):
                md.append("\n**Test Directories**:")
                for test_dir in test["test_directories"]:
                    md.append(f"- `{test_dir}`")

        # CI/CD Configuration
        if summary.get("ci_configuration"):
            ci = summary["ci_configuration"]
            md.append("\n## CI/CD Configuration")

            if ci.get("has_ci"):
                md.append(f"**CI Platforms**: {', '.join(ci.get('platforms', []))}")

                if ci.get("workflows"):
                    md.append("\n**Workflows**:")
                    for workflow in ci["workflows"]:
                        md.append(f"- **{workflow['name']}**")
                        if workflow.get("triggers"):
                            md.append(f"  - Triggers: {', '.join(workflow['triggers'])}")
                        if workflow.get("jobs"):
                            md.append(f"  - Jobs: {', '.join(workflow['jobs'])}")

                if ci.get("configuration_files"):
                    md.append("\n**CI Configuration Files**:")
                    for config in ci["configuration_files"]:
                        md.append(f"- `{config['file']}` ({config['platform']})")
            else:
                md.append("**CI/CD**: No CI configuration detected")

        # Deployment Configuration
        if summary.get("deployment_info"):
            deploy = summary["deployment_info"]
            md.append("\n## Deployment and Distribution")

            if deploy.get("containerization"):
                md.append(f"**Containerization**: {', '.join(deploy['containerization'])}")

            if deploy.get("deployment_platforms"):
                md.append(f"**Deployment Platforms**: {', '.join(deploy['deployment_platforms'])}")

            if deploy.get("package_distribution"):
                md.append(f"**Package Distribution**: {', '.join(deploy['package_distribution'])}")

            if deploy.get("configuration_files"):
                md.append("\n**Deployment Configuration Files**:")
                for config in deploy["configuration_files"]:
                    md.append(f"- `{config['file']}` ({config['platform']}) - {config['type']}")

        # Project Structure
        if "project_structure" in summary:
            structure = summary["project_structure"]
            md.append("\n## Project Structure")
            md.append("### Directory Organization")
            for dir_name, info in sorted(structure["directories"].items()):
                md.append(
                    f"- **`{dir_name}`**: {info['file_count']} files, {info['functions']} functions, {info['classes']} classes"
                )

            md.append("\n### File Types")
            for ext, count in sorted(structure["file_types"].items()):
                md.append(f"- **`{ext}`**: {count} files")

        # Entry Points
        if summary.get("entry_points"):
            md.append("\n## Entry Points")
            md.append("Key entry points for understanding code execution flow:")
            for entry in summary["entry_points"]:
                md.append(
                    f"- **{entry['type'].replace('_', ' ').title()}**: `{entry['name']}` in {entry['location']}"
                )

        # Architecture Patterns
        if summary.get("architecture_patterns"):
            md.append("\n## Architecture Patterns")
            md.append("Identified design patterns in the codebase:")
            for pattern in summary["architecture_patterns"]:
                md.append(f"- **{pattern['pattern']}** (confidence: {pattern['confidence']})")

        # Feature Map - Where to Find Key Functionality
        if summary.get("feature_map"):
            md.append("\n## Feature Map - Where to Find Key Functionality")
            md.append("This section helps you quickly locate code related to specific features:\n")

            for feature, items in summary["feature_map"].items():
                if items:
                    md.append(f"### {feature.replace('_', ' ').title()}")
                    for item in items[:8]:  # Show more items for better context
                        md.append(f"- **`{item['name']}`** ({item['type']}) - {item['purpose']}")
                        md.append(f"  - Location: `{item['location']}`")
                        md.append(f"  - Module: `{item['module']}`")
                    if len(items) > 8:
                        md.append(f"- *...and {len(items) - 8} more related items*")
                    md.append("")

        # Data Flows
        if summary.get("data_flows"):
            md.append("\n## Data Flow Analysis")
            md.append("Understanding how data moves through the system:")

            flow_types = {}
            for flow in summary["data_flows"]:
                flow_type = flow["type"]
                if flow_type not in flow_types:
                    flow_types[flow_type] = []
                flow_types[flow_type].append(flow)

            for flow_type, flows in flow_types.items():
                md.append(f"\n### {flow_type.replace('_', ' ').title()}")
                for flow in flows[:5]:
                    md.append(
                        f"- **`{flow['function']}`** at `{flow['location']}` - {flow['purpose']}"
                    )

        # Detailed Module Documentation
        md.append("\n## Detailed Module Documentation")
        md.append("Complete reference for all modules, classes, and functions:\n")

        for module_name, module_info in sorted(summary["modules"].items()):
            md.append(f"### Module: `{module_name}`")
            md.append(f"**File Path**: `{module_info['relative_path']}`")
            md.append(f"**Purpose**: {module_info['purpose']}")

            if module_info.get("module_docstring"):
                md.append("**Module Documentation**:")
                md.append("```")
                md.append(module_info["module_docstring"])
                md.append("```")

            md.append(f"**Complexity Score**: {module_info['complexity_score']}")
            md.append(
                f"**Exports**: {', '.join(module_info['exports']) if module_info['exports'] else 'None'}"
            )

            # Dependencies
            if module_info.get("dependencies") or module_info.get("dependents"):
                md.append(f"**Dependencies**: {len(module_info.get('dependencies', []))} imports")
                md.append(f"**Used By**: {len(module_info.get('dependents', []))} modules")

            # Imports
            if module_info.get("imports"):
                md.append("\n**Key Imports**:")
                for imp in module_info["imports"][:10]:  # Show first 10 imports
                    md.append(f"- `{imp}`")
                if len(module_info["imports"]) > 10:
                    md.append(f"- *...and {len(module_info['imports']) - 10} more imports*")

            # Classes
            if module_info["classes"]:
                md.append(f"\n#### Classes ({len(module_info['classes'])})")
                for cls in module_info["classes"]:
                    md.append(f"\n**`{cls['name']}`** (line {cls['line']})")
                    md.append(f"- **Purpose**: {cls['docstring']}")

                    if cls.get("base_classes"):
                        md.append(f"- **Inherits from**: {', '.join(cls['base_classes'])}")

                    if cls.get("is_abstract"):
                        md.append("- **Abstract Class**: Yes")

                    if cls["methods"]:
                        md.append(f"- **Methods** ({len(cls['methods'])}):")
                        for method in cls["methods"][:8]:  # Show first 8 methods
                            method_type = []
                            if method.get("is_static"):
                                method_type.append("static")
                            if method.get("is_class_method"):
                                method_type.append("classmethod")
                            if method.get("is_property"):
                                method_type.append("property")
                            if method.get("is_private"):
                                method_type.append("private")

                            type_str = f" ({', '.join(method_type)})" if method_type else ""
                            md.append(f"  - `{method['signature']}`{type_str}")
                            if method["docstring"] != "No description":
                                md.append(f"    - {method['docstring']}")

                        if len(cls["methods"]) > 8:
                            md.append(f"  - *...and {len(cls['methods']) - 8} more methods*")

            # Functions
            if module_info["functions"]:
                md.append(f"\n#### Functions ({len(module_info['functions'])})")
                for func in module_info["functions"]:
                    md.append(f"\n**`{func['signature']}`** (line {func['line']})")
                    md.append(f"- **Purpose**: {func['purpose']}")
                    md.append(f"- **Complexity**: {func['complexity']}/10")

                    if func["docstring"] != "No description":
                        md.append(f"- **Documentation**: {func['docstring']}")

                    if func.get("parameters"):
                        param_list = [p["name"] for p in func["parameters"]]
                        md.append(f"- **Parameters**: {', '.join(param_list)}")

                    if func.get("return_type"):
                        md.append(f"- **Returns**: {func['return_type']}")

                    if func.get("decorators"):
                        md.append(f"- **Decorators**: {', '.join(func['decorators'])}")

                    flags = []
                    if func.get("is_async"):
                        flags.append("async")
                    if func.get("is_generator"):
                        flags.append("generator")
                    if flags:
                        md.append(f"- **Special**: {', '.join(flags)}")

            md.append("")  # Spacing between modules

        # Dependencies Graph
        if summary.get("dependencies"):
            md.append("\n## Module Dependencies")
            md.append("Understanding module interconnections:")

            for module, deps in summary["dependencies"].items():
                if deps.get("imports") or deps.get("used_by"):
                    md.append(f"\n### `{module}`")
                    if deps.get("imports"):
                        md.append(f"**Imports**: {len(deps['imports'])} dependencies")
                    if deps.get("used_by"):
                        md.append(f"**Used by**: {len(deps['used_by'])} modules")
                    md.append(f"**Complexity**: {deps.get('complexity', 0)}")

        # Key Functions Reference
        if summary.get("key_functions"):
            md.append("\n## Key Functions Reference")
            md.append("Most important functions for understanding the codebase:")

            for func in summary["key_functions"]:
                md.append(f"\n### `{func['name']}`")
                md.append(f"- **Module**: `{func['module']}`")
                md.append(f"- **Location**: `{func['location']}`")
                md.append(f"- **Purpose**: {func['purpose']}")

        # Class Hierarchy
        if summary.get("class_hierarchy"):
            md.append("\n## Class Hierarchy")
            md.append("Object-oriented structure and relationships:")

            for class_name, class_info in summary["class_hierarchy"].items():
                md.append(f"\n### `{class_name}`")
                md.append(f"- **Module**: `{class_info['module']}`")
                md.append(f"- **Location**: `{class_info['location']}`")
                md.append(f"- **Documentation**: {class_info['docstring']}")

                if class_info.get("base_classes"):
                    md.append(f"- **Inherits from**: {', '.join(class_info['base_classes'])}")

                if class_info.get("methods"):
                    md.append(f"- **Methods**: {', '.join(class_info['methods'][:10])}")
                    if len(class_info["methods"]) > 10:
                        md.append(f"  *...and {len(class_info['methods']) - 10} more*")

                if class_info.get("is_abstract"):
                    md.append("- **Abstract**: Yes")

        # Footer
        md.append("\n---")
        md.append("*This documentation was automatically generated by Autodoc.*")
        md.append(
            "*For the most up-to-date information, regenerate this document after code changes.*"
        )

        return "\n".join(md)


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


class Autodoc(SimpleAutodoc):
    """Public API"""

    async def analyze(self, path: str) -> Dict[str, Any]:
        return await self.analyze_directory(Path(path))


def main():
    cli()


if __name__ == "__main__":
    main()
