"""
Main Autodoc class that orchestrates code analysis and documentation generation.
"""

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from .analyzer import CodeEntity, SimpleASTAnalyzer
from .chromadb_embedder import ChromaDBEmbedder
from .config import AutodocConfig
from .embedder import OpenAIEmbedder
from .project_analyzer import ProjectAnalyzer
from .summary import CodeAnalyzer, MarkdownFormatter

# Optional TypeScript analyzer import
try:
    from .typescript_analyzer import TypeScriptAnalyzer
    TYPESCRIPT_AVAILABLE = True
except ImportError:
    TYPESCRIPT_AVAILABLE = False

console = Console()


class SimpleAutodoc:
    """Main class for analyzing codebases and generating documentation."""

    def __init__(self, config: Optional[AutodocConfig] = None):
        self.config = config or AutodocConfig.load()
        self.analyzer = SimpleASTAnalyzer()
        self.ts_analyzer = None
        self.embedder = None
        self.chromadb_embedder = None

        # Initialize TypeScript analyzer if available
        if TYPESCRIPT_AVAILABLE:
            self.ts_analyzer = TypeScriptAnalyzer()
            if not self.ts_analyzer.is_available():
                console.print("[yellow]TypeScript analyzer initialized but tree-sitter not available[/yellow]")
        else:
            console.print("[yellow]TypeScript analyzer not available[/yellow]")

        # Initialize embedder based on config
        embedding_provider = self.config.embeddings.get("provider", "openai")
        
        if embedding_provider == "chromadb":
            # Use ChromaDB for local embeddings
            try:
                self.chromadb_embedder = ChromaDBEmbedder(
                    collection_name="autodoc_embeddings",
                    persist_directory=self.config.embeddings.get("persist_directory", ".autodoc_chromadb"),
                    embedding_model=self.config.embeddings.get("chromadb_model", "all-MiniLM-L6-v2")
                )
                console.print(f"[green]Using ChromaDB for embeddings (model: {self.config.embeddings.get('chromadb_model')})[/green]")
            except Exception as e:
                console.print(f"[red]Failed to initialize ChromaDB: {e}[/red]")
                console.print("[yellow]Embeddings disabled[/yellow]")
        else:
            # Default to OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and api_key != "sk-...":
                self.embedder = OpenAIEmbedder(api_key)
                console.print("[green]Using OpenAI for embeddings[/green]")
            else:
                console.print("[yellow]No OpenAI API key found - embeddings disabled[/yellow]")

        self.entities: List[CodeEntity] = []

    async def analyze_directory(self, path: Path, incremental: bool = False, exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """Analyze a directory and return analysis summary."""
        console.print(f"[blue]Analyzing directory: {path}[/blue]")
        
        if exclude_patterns:
            console.print(f"[yellow]Excluding patterns: {', '.join(exclude_patterns)}[/yellow]")
        
        # Load existing entities if incremental
        existing_entities = []
        changed_files = set()
        if incremental and Path("autodoc_cache.json").exists():
            self.load()
            existing_entities = self.entities.copy()
            console.print(f"[yellow]Incremental mode: loaded {len(existing_entities)} existing entities[/yellow]")
            
            # Import ChangeDetector for file change detection
            from .inline_enrichment import ChangeDetector
            change_detector = ChangeDetector()
            
            # Get list of changed files
            changed_files = change_detector.get_changed_files(existing_entities)
            if changed_files:
                console.print(f"[yellow]Found {len(changed_files)} changed files[/yellow]")
            else:
                console.print("[green]No files have changed since last analysis[/green]")
                return self._create_summary(existing_entities)
        
        # Analyze Python files
        if incremental and changed_files:
            # Only analyze changed files
            python_entities = []
            for file_path in changed_files:
                if file_path.endswith('.py'):
                    file_entities = self.analyzer.analyze_file(Path(file_path))
                    python_entities.extend(file_entities)
            
            # Keep entities from unchanged files
            unchanged_entities = [e for e in existing_entities if e.file_path not in changed_files]
            all_entities = unchanged_entities + python_entities
        else:
            # Full analysis
            python_entities = self.analyzer.analyze_directory(path, exclude_patterns)
            all_entities = python_entities.copy()  # Create a copy to avoid modifying the original list
        
        # Analyze TypeScript files if analyzer is available
        typescript_entities = []
        if self.ts_analyzer and self.ts_analyzer.is_available():
            if incremental and changed_files:
                # Only analyze changed TypeScript files
                for file_path in changed_files:
                    if file_path.endswith(('.ts', '.tsx')):
                        file_entities = self.ts_analyzer.analyze_file(Path(file_path))
                        typescript_entities.extend(file_entities)
                
                # Add TypeScript entities from unchanged files
                unchanged_ts_entities = [e for e in existing_entities 
                                       if e.file_path.endswith(('.ts', '.tsx')) 
                                       and e.file_path not in changed_files]
                typescript_entities.extend(unchanged_ts_entities)
            else:
                # Full analysis
                typescript_entities = self.ts_analyzer.analyze_directory(path, exclude_patterns)
            all_entities.extend(typescript_entities)
        
        console.print(f"[green]Found {len(python_entities)} Python entities and {len(typescript_entities)} TypeScript entities[/green]")

        # Generate embeddings using appropriate provider
        if self.chromadb_embedder and all_entities:
            console.print("[blue]Generating ChromaDB embeddings...[/blue]")
            
            # Use ChromaDB for embeddings
            embedded_count = await self.chromadb_embedder.embed_entities(
                all_entities, 
                use_enrichment=True,
                batch_size=self.config.embeddings.get("batch_size", 100)
            )
            console.print(f"[green]Embedded {embedded_count} entities in ChromaDB[/green]")
            
        elif self.embedder and all_entities:
            console.print("[blue]Generating OpenAI embeddings...[/blue]")
            
            # Load enrichment cache if available
            enrichment_cache = None
            try:
                from .enrichment import EnrichmentCache
                enrichment_cache = EnrichmentCache()
            except Exception:
                pass
            
            texts = []
            for entity in all_entities:
                text = f"{entity.type} {entity.name}"
                
                # Use enriched description if available
                if enrichment_cache:
                    cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                    enrichment = enrichment_cache.get_enrichment(cache_key)
                    if enrichment and enrichment.get("description"):
                        text += f": {enrichment['description']}"
                        if enrichment.get("key_features"):
                            text += " Features: " + ", ".join(enrichment['key_features'])
                    elif entity.docstring:
                        text += f": {entity.docstring}"
                elif entity.docstring:
                    text += f": {entity.docstring}"
                    
                texts.append(text)

            embeddings = await self.embedder.embed_batch(texts)
            for entity, embedding in zip(all_entities, embeddings):
                entity.embedding = embedding

            console.print(f"[green]Generated {len(embeddings)} embeddings[/green]")

        self.entities = all_entities

        # Update change detector with analyzed files
        if incremental:
            for file_path in set(e.file_path for e in all_entities):
                file_entities = [e for e in all_entities if e.file_path == file_path]
                change_detector.mark_processed(Path(file_path), file_entities)

        return self._create_summary(all_entities, python_entities, typescript_entities)
    
    def _create_summary(self, all_entities: List[CodeEntity], 
                       python_entities: List[CodeEntity] = None, 
                       typescript_entities: List[CodeEntity] = None) -> Dict[str, Any]:
        """Create analysis summary from entities."""
        if python_entities is None:
            python_entities = [e for e in all_entities if e.file_path.endswith('.py')]
        if typescript_entities is None:
            typescript_entities = [e for e in all_entities if e.file_path.endswith(('.ts', '.tsx'))]
        
        # Calculate language-specific stats
        python_files = len(set(e.file_path for e in python_entities))
        typescript_files = len(set(e.file_path for e in typescript_entities))
        
        return {
            "files_analyzed": len(set(e.file_path for e in all_entities)),
            "total_entities": len(all_entities),
            "functions": len([e for e in all_entities if e.type == "function"]),
            "classes": len([e for e in all_entities if e.type == "class"]),
            "methods": len([e for e in all_entities if e.type == "method"]),
            "interfaces": len([e for e in all_entities if e.type == "interface"]),
            "types": len([e for e in all_entities if e.type == "type"]),
            "has_embeddings": self.embedder is not None or self.chromadb_embedder is not None,
            "languages": {
                "python": {
                    "files": python_files,
                    "entities": len(python_entities),
                    "functions": len([e for e in python_entities if e.type == "function"]),
                    "classes": len([e for e in python_entities if e.type == "class"])
                },
                "typescript": {
                    "files": typescript_files,
                    "entities": len(typescript_entities),
                    "functions": len([e for e in typescript_entities if e.type == "function"]),
                    "classes": len([e for e in typescript_entities if e.type == "class"]),
                    "methods": len([e for e in typescript_entities if e.type == "method"]),
                    "interfaces": len([e for e in typescript_entities if e.type == "interface"]),
                    "types": len([e for e in typescript_entities if e.type == "type"])
                }
            }
        }

    async def search(self, query: str, limit: int = 10, type_filter: str = None, 
                    file_filter: str = None, use_regex: bool = False) -> List[Dict[str, Any]]:
        """Search for code entities using embeddings or text matching.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            type_filter: Filter by entity type (function, class, method, etc.)
            file_filter: Filter by file pattern (supports wildcards)
            use_regex: Use regex pattern matching for query
        """
        # If we have entities in memory, use them (for tests and direct usage)
        if self.entities:
            # Use in-memory search
            results = await self.search_async(query, limit, type_filter, file_filter, use_regex)
            formatted_results = []
            for entity, similarity in results:
                entity_dict = asdict(entity)
                formatted_results.append({
                    "entity": entity_dict,
                    "similarity": similarity
                })
            return formatted_results
        
        # Otherwise use ChromaDB search if available
        elif self.chromadb_embedder:
            console.print(f"[blue]Searching ChromaDB for: {query}[/blue]")
            # For ChromaDB, we need to post-filter results
            results = await self.chromadb_embedder.search(query, limit=limit * 3)  # Get more results for filtering
            
            # Convert ChromaDB results to expected format and apply filters
            formatted_results = []
            for result in results:
                entity_data = result["entity"]
                
                # Apply type filter
                if type_filter and entity_data["type"] != type_filter:
                    continue
                
                # Apply file filter
                if file_filter:
                    import fnmatch
                    if not fnmatch.fnmatch(entity_data["file_path"], file_filter):
                        continue
                
                # Load the full entity from cache if needed
                entity_dict = {
                    "type": entity_data["type"],
                    "name": entity_data["name"],
                    "file_path": entity_data["file_path"],
                    "line_number": entity_data["line_number"],
                    "docstring": "",  # Would need to load from cache
                    "code": "",  # Would need to load from cache
                    "embedding": None,
                    "is_internal": result["metadata"].get("is_internal", False),
                }
                formatted_results.append({
                    "entity": entity_dict,
                    "similarity": result["similarity"]
                })
                
                if len(formatted_results) >= limit:
                    break
                    
            return formatted_results
            
        else:
            return []

    async def analyze_directory_async(self, path: Path, save: bool = True) -> Dict[str, Any]:
        """Async version of analyze_directory."""
        result = await self.analyze_directory(path)
        if save:
            self.save()
        return result

    async def analyze_file_async(self, file_path: Path, save: bool = True) -> Dict[str, Any]:
        """Analyze a single file asynchronously."""
        entities = self.analyzer.analyze_file(file_path)

        if self.embedder and entities:
            console.print("[blue]Generating embeddings...[/blue]")
            texts = []
            for entity in entities:
                text = f"{entity.type} {entity.name}"
                if entity.docstring:
                    text += f": {entity.docstring}"
                texts.append(text)

            embeddings = await self.embedder.embed_batch(texts)
            for entity, embedding in zip(entities, embeddings):
                entity.embedding = embedding

            console.print(f"[green]Generated {len(embeddings)} embeddings[/green]")

        self.entities.extend(entities)

        if save:
            self.save()

        return {
            "file_analyzed": str(file_path),
            "entities_found": len(entities),
            "functions": len([e for e in entities if e.type == "function"]),
            "classes": len([e for e in entities if e.type == "class"]),
            "has_embeddings": self.embedder is not None or self.chromadb_embedder is not None,
        }

    async def search_async(self, query: str, limit: int = 10, type_filter: str = None,
                          file_filter: str = None, use_regex: bool = False) -> List[tuple]:
        """Async version of search that returns (entity, score) tuples.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            type_filter: Filter by entity type (function, class, method, etc.)
            file_filter: Filter by file pattern (supports wildcards)
            use_regex: Use regex pattern matching for query
        """
        if not self.entities:
            return []

        # Apply type and file filters first
        filtered_entities = self.entities
        
        if type_filter:
            filtered_entities = [e for e in filtered_entities if e.type == type_filter]
        
        if file_filter:
            import fnmatch
            filtered_entities = [e for e in filtered_entities 
                               if fnmatch.fnmatch(e.file_path, file_filter)]
        
        if not filtered_entities:
            return []

        if self.embedder and all(e.embedding for e in filtered_entities):
            console.print(f"[blue]Searching for: {query}[/blue]")
            query_embedding = await self.embedder.embed(query)

            results = []
            for entity in filtered_entities:
                similarity = sum(a * b for a, b in zip(query_embedding, entity.embedding))
                results.append((entity, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]
        else:
            # Text-based search with optional regex
            results = []
            
            if use_regex:
                import re
                try:
                    pattern = re.compile(query, re.IGNORECASE)
                except re.error:
                    console.print(f"[red]Invalid regex pattern: {query}[/red]")
                    return []
                
                for entity in filtered_entities:
                    if pattern.search(entity.name):
                        results.append((entity, 1.0))
                    elif entity.docstring and pattern.search(entity.docstring):
                        results.append((entity, 0.5))
            else:
                query_lower = query.lower()
                for entity in filtered_entities:
                    if query_lower in entity.name.lower():
                        results.append((entity, 1.0))
                    elif entity.docstring and query_lower in entity.docstring.lower():
                        results.append((entity, 0.5))

            # Sort by score and limit results
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    def save(self, path: str = "autodoc_cache.json"):
        """Save analyzed entities to cache file."""
        data = {"entities": [asdict(e) for e in self.entities]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Saved {len(self.entities)} entities to {path}[/green]")

    def load(self, path: str = "autodoc_cache.json"):
        """Load analyzed entities from cache file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            # Filter entity data to only include fields that CodeEntity accepts
            from inspect import signature
            valid_fields = set(signature(CodeEntity).parameters.keys())
            
            self.entities = []
            for entity_data in data["entities"]:
                # Only keep fields that exist in CodeEntity
                filtered_data = {k: v for k, v in entity_data.items() if k in valid_fields}
                self.entities.append(CodeEntity(**filtered_data))
            
            console.print(f"[green]Loaded {len(self.entities)} entities from {path}[/green]")
        except FileNotFoundError:
            console.print(f"[yellow]No cache file found at {path}[/yellow]")

    def generate_summary(self, use_enrichment: bool = True) -> Dict[str, Any]:
        """Generate a comprehensive codebase summary optimized for LLM context."""
        if not self.entities:
            return {"error": "No analyzed code found. Run 'analyze' first."}

        # Load enrichment cache if available
        enrichment_cache = None
        if use_enrichment:
            from .enrichment import EnrichmentCache
            enrichment_cache = EnrichmentCache()

        # Initialize analyzers
        code_analyzer = CodeAnalyzer(self.entities)
        project_analyzer = ProjectAnalyzer(self.entities)

        # Calculate comprehensive statistics
        stats = code_analyzer.calculate_statistics()

        # Group entities by file with enhanced information
        files = {}
        for entity in self.entities:
            file_path = entity.file_path
            if file_path not in files:
                files[file_path] = {
                    "functions": [],
                    "classes": [],
                    "module_doc": code_analyzer.extract_module_docstring(file_path),
                    "imports": code_analyzer.extract_imports(file_path),
                    "complexity_score": 0,
                    "exports": [],
                }

            if entity.type == "function":
                # Get enrichment if available
                enriched_data = {}
                if enrichment_cache:
                    cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                    enrichment = enrichment_cache.get_enrichment(cache_key)
                    if enrichment:
                        enriched_data = enrichment
                
                func_info = {
                    "name": entity.name,
                    "line": entity.line_number,
                    "signature": code_analyzer.extract_signature(entity),
                    "docstring": enriched_data.get("description") or entity.docstring or "No description",
                    "purpose": enriched_data.get("purpose") or code_analyzer.extract_purpose(entity),
                    "complexity": code_analyzer.estimate_complexity(entity),
                    "calls": [],  # Would need more sophisticated analysis
                    "decorators": code_analyzer.extract_decorators(entity),
                    "parameters": code_analyzer.extract_parameters(entity),
                    "return_type": code_analyzer.extract_return_type(entity),
                    "is_async": code_analyzer.is_async_function(entity),
                    "key_features": enriched_data.get("key_features", []),
                    "complexity_notes": enriched_data.get("complexity_notes"),
                    "usage_examples": enriched_data.get("usage_examples", []),
                    "is_generator": code_analyzer.is_generator(entity),
                }
                files[file_path]["functions"].append(func_info)

                # Track public exports
                if not entity.name.startswith("_"):
                    files[file_path]["exports"].append(entity.name)

            elif entity.type == "class":
                # Get enrichment if available
                enriched_data = {}
                if enrichment_cache:
                    cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                    enrichment = enrichment_cache.get_enrichment(cache_key)
                    if enrichment:
                        enriched_data = enrichment
                
                class_info = {
                    "name": entity.name,
                    "line": entity.line_number,
                    "docstring": enriched_data.get("description") or entity.docstring or "No description",
                    "purpose": enriched_data.get("purpose", ""),
                    "key_features": enriched_data.get("key_features", []),
                    "design_patterns": enriched_data.get("design_patterns", []),
                    "base_classes": code_analyzer.extract_base_classes(entity),
                    "methods": [
                        {
                            "name": m.name,
                            "line": m.line_number,
                            "signature": code_analyzer.extract_signature(m),
                            "docstring": m.docstring or "No description",
                            "purpose": code_analyzer.extract_purpose(m),
                            "is_static": code_analyzer.is_static_method(m),
                            "is_class_method": code_analyzer.is_class_method(m),
                            "is_property": code_analyzer.is_property(m),
                            "is_private": m.name.startswith("_"),
                            "is_dunder": m.name.startswith("__") and m.name.endswith("__"),
                        }
                        for m in code_analyzer.get_class_methods_detailed(entity, file_path)
                    ],
                    "attributes": [],  # Simplified implementation
                    "is_abstract": code_analyzer.is_abstract_class(entity),
                    "metaclass": None,  # Would need more analysis
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
        feature_map = code_analyzer.build_enhanced_feature_map()
        key_functions = code_analyzer.identify_key_functions()
        class_hierarchy = self._build_detailed_class_hierarchy(code_analyzer)
        entry_points = code_analyzer.identify_entry_points()
        data_flows = code_analyzer.analyze_data_flows()
        architecture_patterns = code_analyzer.identify_architecture_patterns()
        build_system = project_analyzer.analyze_build_system()
        test_system = project_analyzer.analyze_test_system()
        ci_configuration = project_analyzer.analyze_ci_configuration()
        deployment_info = project_analyzer.analyze_deployment_configuration()

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
            module_name = code_analyzer.path_to_module(file_path)
            summary["modules"][module_name] = {
                "file_path": file_path,
                "relative_path": (
                    str(Path(file_path).relative_to(Path.cwd(), walk_up=True))
                    if Path(file_path).is_absolute()
                    else file_path
                ),
                "purpose": code_analyzer.infer_detailed_module_purpose(file_path, content),
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

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format comprehensive summary as detailed Markdown."""
        formatter = MarkdownFormatter()
        return formatter.format_summary_markdown(summary)

    def _analyze_dependencies(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze module dependencies."""
        dependencies = {}
        code_analyzer = CodeAnalyzer(self.entities)

        for file_path, content in files.items():
            module_name = code_analyzer.path_to_module(file_path)
            dependencies[module_name] = {
                "imports": content["imports"],
                "used_by": [],
                "complexity": content["complexity_score"],
            }

        return dependencies

    def _build_detailed_class_hierarchy(self, code_analyzer: CodeAnalyzer) -> Dict[str, Any]:
        """Build detailed class hierarchy information."""
        classes = {}

        for entity in self.entities:
            if entity.type == "class":
                classes[entity.name] = {
                    "module": code_analyzer.path_to_module(entity.file_path),
                    "file_path": entity.file_path,
                    "line_number": entity.line_number,
                    "docstring": entity.docstring or "No description",
                    "base_classes": code_analyzer.extract_base_classes(entity),
                    "methods": [
                        m.name
                        for m in code_analyzer.get_class_methods_detailed(entity, entity.file_path)
                    ],
                    "is_abstract": code_analyzer.is_abstract_class(entity),
                    "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                }

        return classes

    def _analyze_project_structure(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall project structure."""
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
        """Calculate code quality metrics."""
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
        """Calculate complexity distribution across files."""
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

    def _extract_imports(self, file_path: str) -> List[str]:
        """Extract imports from a file."""
        try:
            import ast

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

    def _extract_imports(self, file_path: str) -> List[str]:
        """Extract import statements from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            import ast

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
        except Exception as e:
            console.print(f"[red]Error extracting imports from {file_path}: {e}[/red]")
            return []

    def _get_class_methods_detailed(
        self, class_entity: CodeEntity, file_path: str
    ) -> List[CodeEntity]:
        """Get detailed information about class methods."""
        methods = []

        # Find all functions in the same file that come after the class
        for entity in self.entities:
            if (
                entity.file_path == file_path
                and entity.type == "function"
                and entity.line_number > class_entity.line_number
            ):

                # Simple heuristic: if the function is indented and comes after the class,
                # it's likely a method. More sophisticated analysis would check indentation.
                methods.append(entity)

        return methods


class Autodoc(SimpleAutodoc):
    """Public API class."""

    async def analyze(self, path: str) -> Dict[str, Any]:
        return await self.analyze_directory(Path(path))
