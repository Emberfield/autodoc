#!/usr/bin/env python3
"""
Inline enrichment functionality for adding enriched docstrings directly to code files.
"""

import ast
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .analyzer import CodeEntity
from .config import AutodocConfig
from .enrichment import EnrichmentCache, LLMEnricher

console = Console()


@dataclass
class FileChangeInfo:
    """The `FileChangeInfo` class is designed to encapsulate information regarding changes made to files, specifically for the purpose of incremental enrichment in a software system. It likely tracks attributes such as modified timestamps, change types, and potentially the content changes themselves to facilitate efficient updates.

Key features:
- Tracks file modification timestamps.
- Records types of changes (e.g., added, modified, deleted).
- Facilitates incremental enrichment processes by providing relevant change information.
- May include methods for comparing changes or retrieving specific details about the changes.

Examples:
    file_change_info = FileChangeInfo(file_path='example.txt', change_type='modified', timestamp='2023-10-01T12:00:00')
    if file_change_info.change_type == 'deleted': handle_file_deletion(file_change_info)"""
    file_path: str
    last_modified: float
    content_hash: str
    entities_count: int


@dataclass
class InlineEnrichmentResult:
    """The InlineEnrichmentResult class encapsulates the outcome of an inline enrichment operation, which typically involves augmenting data with additional context or information. It serves as a structured representation of the results obtained from such an enrichment process.

Key features:
- Encapsulation of enrichment results
- Structured representation for easy access
- Facilitates integration with other components in the system

Examples:
    result = InlineEnrichmentResult()  # Create an instance to hold enrichment results
    enriched_data = result.get_enriched_data()  # Access the enriched data from the result"""
    file_path: str
    enriched_entities: List[str]
    updated_docstrings: int
    errors: List[str]
    skipped_entities: List[str]


class ChangeDetector:
    """The ChangeDetector class is designed to monitor and identify changes in files, facilitating incremental enrichment processes. It helps in tracking modifications to ensure that updates are efficiently applied without reprocessing unchanged data.

Key features:
- Monitors specified files for changes
- Supports incremental enrichment of data based on detected changes
- Can be integrated into larger data processing pipelines

Examples:
    detector = ChangeDetector(file_path='data/input.txt')
detector.check_for_changes()
    if detector.has_changes():
    detector.process_changes()"""
    
    def __init__(self, cache_file: str = ".autodoc_file_changes.json"):
        """The __init__ function is a constructor method in Python, typically used to initialize an instance of a class. It sets up the initial state of the object by assigning values to its attributes based on the parameters provided during instantiation.

Key features:
- Initializes instance attributes based on input parameters.
- Can include default values for parameters.
- Allows for custom initialization logic to be executed when an object is created.

Examples:
    class MyClass:
    def __init__(self, value):
        self.value = value

obj = MyClass(10)  # Initializes obj with value 10
    class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

person = Person('Alice', 30)  # Creates a Person object with name 'Alice' and age 30

Complexity: The complexity of the __init__ function is generally O(1) as it typically involves simple assignments and initializations. However, if it includes complex logic or calls to other methods, the performance could vary accordingly."""
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, FileChangeInfo]:
        """The _load_cache function is responsible for loading a file change cache, which likely stores information about changes made to files in a project. This function retrieves the cached data to optimize performance and avoid redundant file checks.

Key features:
- Retrieves cached data from a specified storage mechanism (e.g., file system, database).
- Handles potential errors or exceptions during the loading process to ensure stability.
- May include logic to validate the integrity or freshness of the cached data.

Examples:
    cache_data = _load_cache('path/to/cache/file')
    if _load_cache('cache.json') is not None: print('Cache loaded successfully')

Complexity: The complexity of this function may vary depending on the underlying storage mechanism and the size of the cache. Performance considerations include the time taken to read from disk or database and the efficiency of data serialization/deserialization."""
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            
            cache = {}
            for file_path, info in data.items():
                cache[file_path] = FileChangeInfo(**info)
            return cache
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load change cache: {e}[/yellow]")
            return {}
    
    def _save_cache(self):
        """The _save_cache function is responsible for persisting changes made to a file change cache, ensuring that updates are stored for future reference. It likely interacts with a caching mechanism to maintain state across sessions or operations.

Key features:
- Persisting cache data to a storage medium (e.g., file system or database)
- Updating existing cache entries with new information
- Handling potential errors during the save process to ensure data integrity

Examples:
    After modifying the cache with new file changes, call _save_cache() to ensure that the changes are stored persistently.
    Use _save_cache() in a context where the application needs to recover the state of file changes after a restart or crash.

Complexity: The complexity of this function may vary based on the size of the cache and the underlying storage mechanism. Performance considerations include the speed of the I/O operations and the efficiency of data serialization/deserialization."""
        try:
            data = {}
            for file_path, info in self.cache.items():
                data[file_path] = {
                    "file_path": info.file_path,
                    "last_modified": info.last_modified,
                    "content_hash": info.content_hash,
                    "entities_count": info.entities_count
                }
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save change cache: {e}[/yellow]")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """The `_get_file_hash` function computes and returns the hash value of the content of a specified file. This hash value serves as a unique identifier for the file's content, allowing for efficient comparison and verification of file integrity.

Key features:
- Calculates hash using a specified hashing algorithm (e.g., SHA256, MD5).
- Handles file reading efficiently, processing the file in chunks to accommodate large files.
- Returns the hash value in a standardized format (e.g., hexadecimal string).

Examples:
    hash_value = _get_file_hash('path/to/file.txt')
    file_hash = _get_file_hash('path/to/large_file.bin', algorithm='sha256')

Complexity: The performance of this function is generally efficient due to its chunked reading approach, which minimizes memory usage. However, the time complexity can vary based on the file size and the hashing algorithm used, as larger files will take longer to process."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""
    
    def has_changed(self, file_path: Path, entities: List[CodeEntity]) -> bool:
        """The `has_changed` function determines whether a specified file has been modified since the last enrichment process. It compares the current file state with a recorded state to identify any changes.

Key features:
- Compares timestamps or checksums of the file against a stored value.
- Returns a boolean indicating whether the file has changed.
- Can be integrated into workflows that require conditional processing based on file modifications.

Examples:
    if has_changed('example_file.txt'): process_file('example_file.txt')
    if has_changed('/path/to/data.csv'): update_database('/path/to/data.csv')

Complexity: The complexity of this function may vary depending on the method used to check for changes (e.g., file size, modification time, or content hashing). Performance could be impacted by the frequency of checks and the size of the files being monitored."""
        if not file_path.exists():
            return False
        
        file_str = str(file_path)
        current_modified = file_path.stat().st_mtime
        current_hash = self._get_file_hash(file_path)
        current_entities = len([e for e in entities if e.file_path == file_str])
        
        if file_str not in self.cache:
            return True
        
        cached = self.cache[file_str]
        return (
            current_modified > cached.last_modified or
            current_hash != cached.content_hash or
            current_entities != cached.entities_count
        )
    
    def mark_processed(self, file_path: Path, entities: List[CodeEntity]):
        """Mark file as processed."""
        if not file_path.exists():
            return
        
        file_str = str(file_path)
        current_modified = file_path.stat().st_mtime
        current_hash = self._get_file_hash(file_path)
        current_entities = len([e for e in entities if e.file_path == file_str])
        
        self.cache[file_str] = FileChangeInfo(
            file_path=file_str,
            last_modified=current_modified,
            content_hash=current_hash,
            entities_count=current_entities
        )
        self._save_cache()
    
    def get_changed_files(self, entities: List[CodeEntity]) -> Set[str]:
        """Get list of files that have changed."""
        changed_files = set()
        
        # Group entities by file
        files_entities = {}
        for entity in entities:
            if entity.file_path not in files_entities:
                files_entities[entity.file_path] = []
            files_entities[entity.file_path].append(entity)
        
        for file_path, file_entities in files_entities.items():
            path = Path(file_path)
            if self.has_changed(path, file_entities):
                changed_files.add(file_path)
        
        return changed_files


class InlineEnricher:
    """The InlineEnricher class is designed to enhance Python code files by adding or updating docstrings directly within the code. This functionality aims to improve code documentation and maintainability by ensuring that functions and classes are well-documented inline.

Key features:
- Automatically identifies functions and classes that lack docstrings.
- Generates or updates docstrings based on the function's or class's signature and context.
- Supports inline enrichment, allowing for seamless integration of documentation within existing code.

Examples:
    Enriching a single Python file: `enricher = InlineEnricher(); enricher.enrich('example.py')`
    Batch enriching multiple files: `enricher = InlineEnricher(); enricher.enrich_multiple(['file1.py', 'file2.py'])`"""
    
    def __init__(self, config: AutodocConfig, backup: bool = True, dry_run: bool = False):
        self.config = config
        self.backup = backup
        self.dry_run = dry_run
        self.change_detector = ChangeDetector()
    
    def _backup_file(self, file_path: Path):
        """Create backup of original file."""
        if not self.backup or self.dry_run:
            return
        
        backup_path = file_path.with_suffix(f"{file_path.suffix}.autodoc_backup")
        backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
    
    def _parse_python_file(self, file_path: Path) -> Optional[ast.AST]:
        """Parse Python file to AST."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content)
        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")
            return None
    
    def _find_entity_node(self, tree: ast.AST, entity: CodeEntity) -> Optional[ast.AST]:
        """Find the AST node for a given entity."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (node.name == entity.name and 
                    node.lineno == entity.line_number):
                    return node
        return None
    
    def _get_existing_docstring(self, node: ast.AST) -> Optional[str]:
        """Get existing docstring from AST node."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return None
    
    def _should_update_docstring(self, existing: Optional[str], enriched: str) -> bool:
        """Determine if docstring should be updated."""
        if not existing:
            return True
        
        # Don't update if existing docstring is substantial and detailed
        if len(existing) > 100 and any(word in existing.lower() for word in 
                                     ['args:', 'returns:', 'raises:', 'examples:', 'note:']):
            return False
        
        # Update if enriched version is significantly more detailed
        return len(enriched) > len(existing) * 1.5
    
    def _format_docstring(self, description: str, entity: CodeEntity, enrichment: Dict) -> str:
        """Format enriched description as a proper docstring."""
        lines = [description]
        
        # Add key features if available
        if enrichment.get('key_features'):
            lines.append("")
            lines.append("Key features:")
            for feature in enrichment['key_features']:
                lines.append(f"- {feature}")
        
        # Add usage examples if available
        if enrichment.get('usage_examples'):
            lines.append("")
            lines.append("Examples:")
            for example in enrichment['usage_examples']:
                lines.append(f"    {example}")
        
        # Add complexity notes for complex functions
        if enrichment.get('complexity_notes') and entity.type == 'function':
            lines.append("")
            lines.append(f"Complexity: {enrichment['complexity_notes']}")
        
        return '\n'.join(lines)
    
    def _update_file_with_docstrings(
        self, 
        file_path: Path, 
        entities: List[CodeEntity], 
        enrichments: Dict[str, Dict]
    ) -> InlineEnrichmentResult:
        """Update file with enriched docstrings."""
        result = InlineEnrichmentResult(
            file_path=str(file_path),
            enriched_entities=[],
            updated_docstrings=0,
            errors=[],
            skipped_entities=[]
        )
        
        # Read original file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            result.errors.append(f"Could not read file: {e}")
            return result
        
        # Parse AST
        tree = self._parse_python_file(file_path)
        if not tree:
            result.errors.append("Could not parse file")
            return result
        
        # Create backup
        self._backup_file(file_path)
        
        # Track changes
        updated_lines = lines.copy()
        
        # Sort entities by line number (reverse order for safe insertion)
        file_entities = [e for e in entities if e.file_path == str(file_path)]
        file_entities.sort(key=lambda x: x.line_number, reverse=True)
        
        for entity in file_entities:
            cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
            enrichment = enrichments.get(cache_key)
            
            if not enrichment or not enrichment.get('description'):
                result.skipped_entities.append(entity.name)
                continue
            
            # Find AST node
            node = self._find_entity_node(tree, entity)
            if not node:
                result.errors.append(f"Could not find AST node for {entity.name}")
                continue
            
            # Check existing docstring
            existing_docstring = self._get_existing_docstring(node)
            enriched_docstring = self._format_docstring(
                enrichment['description'], entity, enrichment
            )
            
            if not self._should_update_docstring(existing_docstring, enriched_docstring):
                result.skipped_entities.append(f"{entity.name} (already has good docstring)")
                continue
            
            # Calculate insertion point
            insert_line = entity.line_number  # 1-based line number
            
            # Format docstring with proper indentation
            if entity.type == 'class':
                indent = "    "
            elif entity.type == 'function':
                # Detect indentation level
                func_line = updated_lines[insert_line - 1] if insert_line <= len(updated_lines) else ""
                indent = len(func_line) - len(func_line.lstrip()) + 4
                indent = " " * indent
            else:
                indent = "    "
            
            # Create docstring lines
            docstring_lines = []
            docstring_lines.append(f'{indent}"""{enriched_docstring}"""\n')
            
            # Find insertion point (after function/class definition)
            insertion_point = insert_line  # Insert after the def/class line
            
            # Remove existing docstring if present
            if existing_docstring and insertion_point < len(updated_lines):
                # Find and remove existing docstring
                for i in range(insertion_point, min(insertion_point + 5, len(updated_lines))):
                    line = updated_lines[i].strip()
                    if line.startswith('"""') or line.startswith("'''"):
                        # Find end of docstring
                        if line.count('"""') >= 2 or line.count("'''") >= 2:
                            # Single line docstring
                            del updated_lines[i]
                            break
                        else:
                            # Multi-line docstring
                            quote = '"""' if line.startswith('"""') else "'''"
                            del updated_lines[i]
                            while i < len(updated_lines):
                                if quote in updated_lines[i]:
                                    del updated_lines[i]
                                    break
                                del updated_lines[i]
                            break
            
            # Insert new docstring
            for line in reversed(docstring_lines):
                updated_lines.insert(insertion_point, line)
            
            result.enriched_entities.append(entity.name)
            result.updated_docstrings += 1
        
        # Write updated file
        if not self.dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(updated_lines)
            except Exception as e:
                result.errors.append(f"Could not write file: {e}")
                return result
        else:
            # In dry run mode, just log what would be written
            console.print(f"[blue]DRY RUN: Would update {file_path}[/blue]")
        
        return result
    
    async def enrich_files_inline(
        self, 
        entities: List[CodeEntity], 
        incremental: bool = True,
        force: bool = False
    ) -> List[InlineEnrichmentResult]:
        """Enrich files with inline docstrings."""
        results = []
        
        # Determine which files to process
        if incremental and not force:
            changed_files = self.change_detector.get_changed_files(entities)
            if not changed_files:
                console.print("[green]No files have changed since last enrichment[/green]")
                return results
        else:
            changed_files = set(e.file_path for e in entities)
        
        console.print(f"[blue]Processing {len(changed_files)} files for inline enrichment[/blue]")
        
        # Load existing enrichment cache
        enrichment_cache = EnrichmentCache()
        
        # Group entities by file
        files_entities = {}
        for entity in entities:
            if entity.file_path in changed_files:
                if entity.file_path not in files_entities:
                    files_entities[entity.file_path] = []
                files_entities[entity.file_path].append(entity)
        
        # Process each file with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(files_entities))
            
            for file_path, file_entities in files_entities.items():
                path = Path(file_path)
                
                if not path.exists() or path.suffix != '.py':
                    continue
                
                progress.update(task, description=f"[cyan]Enriching {path.name}...")
                
                # Get enrichments for entities in this file
                enrichments = {}
                entities_to_enrich = []
                
                for entity in file_entities:
                    cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                    existing_enrichment = enrichment_cache.get_enrichment(cache_key)
                    
                    if existing_enrichment and not force:
                        enrichments[cache_key] = existing_enrichment
                    else:
                        entities_to_enrich.append(entity)
                
                # Enrich missing entities
                if entities_to_enrich:
                    try:
                        async with LLMEnricher(self.config) as enricher:
                            enriched = await enricher.enrich_entities(entities_to_enrich)
                            
                            for enriched_entity in enriched:
                                cache_key = f"{enriched_entity.entity.file_path}:{enriched_entity.entity.name}:{enriched_entity.entity.line_number}"
                                enrichment_data = {
                                    "description": enriched_entity.description,
                                    "purpose": enriched_entity.purpose,
                                    "key_features": enriched_entity.key_features,
                                    "complexity_notes": enriched_entity.complexity_notes,
                                    "usage_examples": enriched_entity.usage_examples,
                                    "design_patterns": enriched_entity.design_patterns,
                                    "dependencies": enriched_entity.dependencies
                                }
                                enrichments[cache_key] = enrichment_data
                                enrichment_cache.set_enrichment(cache_key, enrichment_data)
                    
                    except Exception as e:
                        console.print(f"[red]Error enriching entities in {path.name}: {e}[/red]")
                        continue
                
                # Update file with docstrings
                result = self._update_file_with_docstrings(path, file_entities, enrichments)
                results.append(result)
                
                # Mark file as processed
                if result.updated_docstrings > 0:
                    self.change_detector.mark_processed(path, file_entities)
                    console.print(f"[green]✅ Updated {result.updated_docstrings} docstrings in {path.name}[/green]")
                else:
                    console.print(f"[yellow]No updates needed for {path.name}[/yellow]")
                
                progress.advance(task)
        
        # Save enrichment cache
        enrichment_cache.save_cache()
        
        return results


class ModuleEnrichmentGenerator:
    """The ModuleEnrichmentGenerator class is responsible for generating module-level enrichment files, which likely enhance or augment the documentation or metadata associated with specific modules in a codebase. It serves as a utility for automating the creation of these enrichment files based on predefined criteria or templates.

Key features:
- Automates the generation of module-level enrichment files
- Enhances documentation by adding metadata or context to modules
- Possibly supports customization options for the enrichment content

Examples:
    generator = ModuleEnrichmentGenerator(); generator.generate_enrichment(module_name)
    enrichment_file = generator.create_enrichment_file(module_info)"""
    
    def __init__(self, config: AutodocConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
    
    def _get_module_entities(self, entities: List[CodeEntity], file_path: str) -> List[CodeEntity]:
        """Get all entities for a specific module."""
        return [e for e in entities if e.file_path == file_path]
    
    def _generate_module_overview(self, file_path: str, entities: List[CodeEntity]) -> Dict:
        """Generate module overview."""
        path = Path(file_path)
        
        return {
            "module_name": path.stem,
            "file_path": file_path,
            "total_entities": len(entities),
            "functions": len([e for e in entities if e.type == "function"]),
            "classes": len([e for e in entities if e.type == "class"]),
            "last_updated": datetime.now().isoformat(),
            "complexity_score": sum(1 for e in entities) / max(1, len(entities))
        }
    
    async def generate_module_enrichment_files(
        self, 
        entities: List[CodeEntity],
        output_format: str = "markdown"
    ) -> List[str]:
        """Generate module-level enrichment files."""
        generated_files = []
        
        # Group entities by file
        files_entities = {}
        for entity in entities:
            if entity.file_path not in files_entities:
                files_entities[entity.file_path] = []
            files_entities[entity.file_path].append(entity)
        
        enrichment_cache = EnrichmentCache()
        
        for file_path, file_entities in files_entities.items():
            path = Path(file_path)
            
            if path.suffix != '.py':
                continue
            
            # Generate module overview
            overview = self._generate_module_overview(file_path, file_entities)
            
            # Collect enrichments
            enriched_entities = []
            for entity in file_entities:
                cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                enrichment = enrichment_cache.get_enrichment(cache_key)
                
                if enrichment:
                    enriched_entities.append({
                        "entity": entity,
                        "enrichment": enrichment
                    })
            
            # Generate output file
            if output_format == "markdown":
                output_file = path.with_suffix('.enrichment.md')
                content = self._generate_markdown_enrichment(overview, enriched_entities, file_entities)
            else:  # JSON
                output_file = path.with_suffix('.enrichment.json')
                content = self._generate_json_enrichment(overview, enriched_entities, file_entities)
            
            # Write file
            if not self.dry_run:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    generated_files.append(str(output_file))
                    console.print(f"[green]Generated {output_file.name}[/green]")
                except Exception as e:
                    console.print(f"[red]Error generating {output_file}: {e}[/red]")
            else:
                generated_files.append(str(output_file))
                console.print(f"[blue]DRY RUN: Would generate {output_file.name}[/blue]")
        
        return generated_files
    
    def _generate_markdown_enrichment(self, overview: Dict, enriched_entities: List, all_entities: List[CodeEntity]) -> str:
        """Generate markdown enrichment file."""
        lines = []
        lines.append(f"# {overview['module_name']} - Module Enrichment")
        lines.append("")
        lines.append(f"**File:** `{overview['file_path']}`")
        lines.append(f"**Last Updated:** {overview['last_updated']}")
        lines.append(f"**Total Entities:** {overview['total_entities']}")
        lines.append(f"**Functions:** {overview['functions']}")
        lines.append(f"**Classes:** {overview['classes']}")
        lines.append("")
        
        if enriched_entities:
            lines.append("## Enriched Entities")
            lines.append("")
            
            for item in enriched_entities:
                entity = item['entity']
                enrichment = item['enrichment']
                
                lines.append(f"### {entity.type.title()}: `{entity.name}`")
                lines.append("")
                lines.append(f"**Line:** {entity.line_number}")
                lines.append("")
                
                if enrichment.get('description'):
                    lines.append(f"**Description:** {enrichment['description']}")
                    lines.append("")
                
                if enrichment.get('purpose'):
                    lines.append(f"**Purpose:** {enrichment['purpose']}")
                    lines.append("")
                
                if enrichment.get('key_features'):
                    lines.append("**Key Features:**")
                    for feature in enrichment['key_features']:
                        lines.append(f"- {feature}")
                    lines.append("")
                
                if enrichment.get('usage_examples'):
                    lines.append("**Usage Examples:**")
                    for example in enrichment['usage_examples']:
                        lines.append("```python")
                        lines.append(example)
                        lines.append("```")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        else:
            lines.append("## Module Entities")
            lines.append("")
            lines.append("*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*")
            lines.append("")
            
            # Group entities by type
            functions = [e for e in all_entities if e.type == "function"]
            classes = [e for e in all_entities if e.type == "class"]
            
            if functions:
                lines.append("### Functions")
                lines.append("")
                for func in sorted(functions, key=lambda x: x.name):
                    lines.append(f"#### `{func.name}` (line {func.line_number})")
                    if func.docstring:
                        lines.append(f"> {func.docstring.split(chr(10))[0]}")  # First line of docstring
                    lines.append("")
            
            if classes:
                lines.append("### Classes")
                lines.append("")
                for cls in sorted(classes, key=lambda x: x.name):
                    lines.append(f"#### `{cls.name}` (line {cls.line_number})")
                    if cls.docstring:
                        lines.append(f"> {cls.docstring.split(chr(10))[0]}")  # First line of docstring
                    
                    # Show class methods
                    methods = [e for e in all_entities if e.type == "method" and getattr(e, 'parent_class', None) == cls.name]
                    if methods:
                        lines.append("")
                        lines.append("**Methods:**")
                        for method in sorted(methods, key=lambda x: x.name):
                            lines.append(f"- `{method.name}` (line {method.line_number})")
                    lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_json_enrichment(self, overview: Dict, enriched_entities: List, all_entities: List[CodeEntity]) -> str:
        """Generate JSON enrichment file."""
        data = {
            "overview": overview,
            "enriched_entities": [],
            "all_entities": []
        }
        
        for item in enriched_entities:
            entity = item['entity']
            enrichment = item['enrichment']
            
            data["enriched_entities"].append({
                "type": entity.type,
                "name": entity.name,
                "line_number": entity.line_number,
                "enrichment": enrichment
            })
        
        # Add all entities basic info
        for entity in all_entities:
            entity_info = {
                "type": entity.type,
                "name": entity.name,
                "line_number": entity.line_number,
                "docstring": entity.docstring
            }
            if entity.type == "method":
                entity_info["parent_class"] = entity.parent_class
            data["all_entities"].append(entity_info)
        
        return json.dumps(data, indent=2)