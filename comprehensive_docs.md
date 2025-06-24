# Comprehensive Codebase Documentation
*Generated on 2025-06-24T13:05:17.828518 with autodoc 0.1.0*

## Executive Summary
This codebase contains 48 functions and 5 classes across 1 files, written primarily in Python.
Total lines analyzed: 1,354
Testing coverage: Limited

## Codebase Statistics
- **Total Entities**: 53
- **Public Functions**: 10
- **Private Functions**: 38
- **Test Functions**: 0
- **Documentation Coverage**: 79.2%
- **Average Functions per File**: 48.0
- **Average Classes per File**: 5.0

### Code Quality Metrics
- **Documentation Coverage**: 85.4%
- **Average Complexity**: 57.0
- **Public API Ratio**: 31.2%

## Project Structure
### Directory Organization
- **`src/autodoc`**: 1 files, 48 functions, 5 classes

### File Types
- **`.py`**: 1 files

## Entry Points
Key entry points for understanding code execution flow:
- **Cli Command**: `check` in cli.py:1254
- **Cli Command**: `generate_summary` in cli.py:1273
- **Main Function**: `main` in cli.py:1338

## Feature Map - Where to Find Key Functionality
This section helps you quickly locate code related to specific features:

### Database
- **`format_summary_markdown`** (function) - Format comprehensive summary as detailed Markdown optimized for LLM context
  - Location: `cli.py:957`
  - Module: `autodoc.cli`

### Data Processing
- **`SimpleASTAnalyzer`** (class) - General purpose function
  - Location: `cli.py:38`
  - Module: `autodoc.cli`
- **`analyze_file`** (function) - General purpose function
  - Location: `cli.py:39`
  - Module: `autodoc.cli`
- **`_analyze_dependencies`** (function) - Analyze module dependencies
  - Location: `cli.py:692`
  - Module: `autodoc.cli`
- **`_analyze_data_flows`** (function) - Analyze data flows in the codebase
  - Location: `cli.py:811`
  - Module: `autodoc.cli`
- **`_analyze_project_structure`** (function) - Analyze overall project structure
  - Location: `cli.py:870`
  - Module: `autodoc.cli`

### File Operations
- **`analyze_file`** (function) - General purpose function
  - Location: `cli.py:39`
  - Module: `autodoc.cli`
- **`save`** (function) - General purpose function
  - Location: `cli.py:187`
  - Module: `autodoc.cli`
- **`load`** (function) - General purpose function
  - Location: `cli.py:193`
  - Module: `autodoc.cli`

### Cli Commands
- **`CodeEntity`** (class) - General purpose function
  - Location: `cli.py:28`
  - Module: `autodoc.cli`
- **`SimpleASTAnalyzer`** (class) - General purpose function
  - Location: `cli.py:38`
  - Module: `autodoc.cli`
- **`OpenAIEmbedder`** (class) - General purpose function
  - Location: `cli.py:70`
  - Module: `autodoc.cli`
- **`SimpleAutodoc`** (class) - General purpose function
  - Location: `cli.py:100`
  - Module: `autodoc.cli`
- **`cli`** (function) - Autodoc - AI-powered code intelligence
  - Location: `cli.py:1196`
  - Module: `autodoc.cli`
- **`check`** (function) - Check dependencies and configuration
  - Location: `cli.py:1254`
  - Module: `autodoc.cli`
- **`generate_summary`** (function) - Generate a comprehensive codebase summary optimized for LLM context
  - Location: `cli.py:1273`
  - Module: `autodoc.cli`
- **`Autodoc`** (class) - Public API
  - Location: `cli.py:1332`
  - Module: `autodoc.cli`
- *...and 45 more related items*


## Data Flow Analysis
Understanding how data moves through the system:

### Data Output
- **`save`** at `cli.py:187` - Saves/writes data

### Data Input
- **`load`** at `cli.py:193` - Loads/reads data

## Detailed Module Documentation
Complete reference for all modules, classes, and functions:

### Module: `autodoc.cli`
**File Path**: `src/autodoc/cli.py`
**Purpose**: Command-line interface with 48 commands
**Module Documentation**:
```

Minimal Autodoc implementation that just works.

```
**Complexity Score**: 57
**Exports**: CodeEntity, SimpleASTAnalyzer, OpenAIEmbedder, SimpleAutodoc, cli, check, generate_summary, Autodoc, main, analyze_file, save, load, generate_summary, format_summary_markdown, invoke
**Dependencies**: 21 imports
**Used By**: 0 modules

**Key Imports**:
- `import os`
- `import ast`
- `import json`
- `import asyncio`
- `import re`
- `from datetime import datetime`
- `from pathlib import Path`
- `from typing import Dict`
- `from typing import List`
- `from typing import Any`
- *...and 11 more imports*

#### Classes (5)

**`CodeEntity`** (line 28)
- **Purpose**: No description
- **Methods** (21):
  - `def cli():`
    - Autodoc - AI-powered code intelligence
  - `def check():`
    - Check dependencies and configuration
  - `def generate_summary(output, output_format):`
    - Generate a comprehensive codebase summary optimized for LLM context
  - `def main():`
  - `def analyze_file(self, file_path: Path) -> List[CodeEntity]:`
  - `def __init__(self, api_key: str):` (private)
  - `def __init__(self):` (private)
  - `def save(self, path: str = "autodoc_cache.json"):`
  - *...and 13 more methods*

**`SimpleASTAnalyzer`** (line 38)
- **Purpose**: No description
- **Methods** (21):
  - `def cli():`
    - Autodoc - AI-powered code intelligence
  - `def check():`
    - Check dependencies and configuration
  - `def generate_summary(output, output_format):`
    - Generate a comprehensive codebase summary optimized for LLM context
  - `def main():`
  - `def analyze_file(self, file_path: Path) -> List[CodeEntity]:`
  - `def __init__(self, api_key: str):` (private)
  - `def __init__(self):` (private)
  - `def save(self, path: str = "autodoc_cache.json"):`
  - *...and 13 more methods*

**`OpenAIEmbedder`** (line 70)
- **Purpose**: No description
- **Methods** (21):
  - `def cli():`
    - Autodoc - AI-powered code intelligence
  - `def check():`
    - Check dependencies and configuration
  - `def generate_summary(output, output_format):`
    - Generate a comprehensive codebase summary optimized for LLM context
  - `def main():`
  - `def __init__(self, api_key: str):` (private)
  - `def __init__(self):` (private)
  - `def save(self, path: str = "autodoc_cache.json"):`
  - `def load(self, path: str = "autodoc_cache.json"):`
  - *...and 13 more methods*

**`SimpleAutodoc`** (line 100)
- **Purpose**: No description
- **Methods** (21):
  - `def cli():`
    - Autodoc - AI-powered code intelligence
  - `def check():`
    - Check dependencies and configuration
  - `def generate_summary(output, output_format):`
    - Generate a comprehensive codebase summary optimized for LLM context
  - `def main():`
  - `def __init__(self):` (private)
  - `def save(self, path: str = "autodoc_cache.json"):`
  - `def load(self, path: str = "autodoc_cache.json"):`
  - `def generate_summary(self) -> Dict[str, Any]:`
    - Generate a comprehensive codebase summary optimized for LLM context
  - *...and 13 more methods*

**`Autodoc`** (line 1332)
- **Purpose**: Public API
- **Inherits from**: SimpleAutodoc
- **Methods** (2):
  - `def main():`
  - `def invoke(ctx):`

#### Functions (48)

**`def cli():`** (line 1196)
- **Purpose**: Autodoc - AI-powered code intelligence
- **Complexity**: 1/10
- **Documentation**: Autodoc - AI-powered code intelligence
- **Decorators**: @click.group()

**`def check():`** (line 1254)
- **Purpose**: Check dependencies and configuration
- **Complexity**: 1/10
- **Documentation**: Check dependencies and configuration
- **Decorators**: @cli.command()

**`def generate_summary(output, output_format):`** (line 1273)
- **Purpose**: Generate a comprehensive codebase summary optimized for LLM context
- **Complexity**: 1/10
- **Documentation**: Generate a comprehensive codebase summary optimized for LLM context
- **Parameters**: output, output_format
- **Decorators**: @cli.command(name="generate-summary"), @click.option("--output", "-o", help="Save summary to file (e.g., summary.md)"), @click.option("--format", "output_format", default="markdown", type=click.Choice(["markdown", "json"]), help="Output format")

**`def main():`** (line 1338)
- **Purpose**: General purpose function
- **Complexity**: 1/10

**`def analyze_file(self, file_path: Path) -> List[CodeEntity]:`** (line 39)
- **Purpose**: General purpose function
- **Complexity**: 1/10
- **Returns**: List[CodeEntity]

**`def __init__(self, api_key: str):`** (line 71)
- **Purpose**: General purpose function
- **Complexity**: 1/10
- **Parameters**: api_key: str

**`def __init__(self):`** (line 101)
- **Purpose**: General purpose function
- **Complexity**: 1/10

**`def save(self, path: str = "autodoc_cache.json"):`** (line 187)
- **Purpose**: General purpose function
- **Complexity**: 1/10
- **Parameters**: path: str

**`def load(self, path: str = "autodoc_cache.json"):`** (line 193)
- **Purpose**: General purpose function
- **Complexity**: 1/10
- **Parameters**: path: str

**`def generate_summary(self) -> Dict[str, Any]:`** (line 202)
- **Purpose**: Generate a comprehensive codebase summary optimized for LLM context
- **Complexity**: 1/10
- **Documentation**: Generate a comprehensive codebase summary optimized for LLM context
- **Returns**: Dict[str, Any]

**`def _extract_purpose(self, entity: CodeEntity) -> str:`** (line 335)
- **Purpose**: Extract purpose from function name and docstring
- **Complexity**: 1/10
- **Documentation**: Extract purpose from function name and docstring
- **Returns**: str

**`def _get_class_methods(self, class_entity: CodeEntity, file_path: str) -> List[str]:`** (line 355)
- **Purpose**: Retrieves data
- **Complexity**: 1/10
- **Documentation**: Get methods belonging to a class
- **Returns**: List[str]

**`def _build_feature_map(self) -> Dict[str, List[str]]:`** (line 370)
- **Purpose**: Build a map of features to locations
- **Complexity**: 1/10
- **Documentation**: Build a map of features to locations
- **Returns**: Dict[str, List[str]]

**`def _identify_key_functions(self, limit: int = 10) -> List[Dict[str, Any]]:`** (line 413)
- **Purpose**: Identify the most important functions
- **Complexity**: 1/10
- **Documentation**: Identify the most important functions
- **Returns**: List[Dict[str, Any]]

**`def _build_class_hierarchy(self) -> Dict[str, Any]:`** (line 432)
- **Purpose**: Build class hierarchy information
- **Complexity**: 1/10
- **Documentation**: Build class hierarchy information
- **Returns**: Dict[str, Any]

**`def _path_to_module(self, file_path: str) -> str:`** (line 446)
- **Purpose**: Convert file path to module name
- **Complexity**: 1/10
- **Documentation**: Convert file path to module name
- **Returns**: str

**`def _infer_module_purpose(self, file_path: str, content: Dict) -> str:`** (line 456)
- **Purpose**: Infer the purpose of a module from its contents
- **Complexity**: 1/10
- **Documentation**: Infer the purpose of a module from its contents
- **Returns**: str

**`def _extract_imports(self, file_path: str) -> List[str]:`** (line 483)
- **Purpose**: Extract imports from a file
- **Complexity**: 1/10
- **Documentation**: Extract imports from a file
- **Returns**: List[str]

**`def _calculate_statistics(self) -> Dict[str, Any]:`** (line 505)
- **Purpose**: Calculate comprehensive codebase statistics
- **Complexity**: 1/10
- **Documentation**: Calculate comprehensive codebase statistics
- **Returns**: Dict[str, Any]

**`def _extract_module_docstring(self, file_path: str) -> Optional[str]:`** (line 530)
- **Purpose**: Extract module-level docstring
- **Complexity**: 1/10
- **Documentation**: Extract module-level docstring
- **Returns**: Optional[str]

**`def _extract_signature(self, entity: CodeEntity) -> str:`** (line 545)
- **Purpose**: Extract function/method signature
- **Complexity**: 1/10
- **Documentation**: Extract function/method signature
- **Returns**: str

**`def _estimate_complexity(self, entity: CodeEntity) -> int:`** (line 559)
- **Purpose**: Estimate code complexity based on entity name and context
- **Complexity**: 3/10
- **Documentation**: Estimate code complexity based on entity name and context
- **Returns**: int

**`def _extract_function_calls(self, entity: CodeEntity) -> List[str]:`** (line 574)
- **Purpose**: Extract function calls made by this entity (simplified)
- **Complexity**: 1/10
- **Documentation**: Extract function calls made by this entity (simplified)
- **Returns**: List[str]

**`def _extract_decorators(self, entity: CodeEntity) -> List[str]:`** (line 580)
- **Purpose**: Extract decorators for functions/methods
- **Complexity**: 1/10
- **Documentation**: Extract decorators for functions/methods
- **Returns**: List[str]

**`def _extract_parameters(self, entity: CodeEntity) -> List[Dict[str, str]]:`** (line 597)
- **Purpose**: Extract function parameters
- **Complexity**: 1/10
- **Documentation**: Extract function parameters
- **Returns**: List[Dict[str, str]]

**`def _extract_return_type(self, entity: CodeEntity) -> Optional[str]:`** (line 615)
- **Purpose**: Extract return type annotation
- **Complexity**: 1/10
- **Documentation**: Extract return type annotation
- **Returns**: Optional[str]

**`def _is_async_function(self, entity: CodeEntity) -> bool:`** (line 621)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if function is async
- **Returns**: bool

**`def _is_generator(self, entity: CodeEntity) -> bool:`** (line 626)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if function is a generator (simplified)
- **Returns**: bool

**`def _get_class_methods_detailed(self, class_entity: CodeEntity, file_path: str) -> List[CodeEntity]:`** (line 631)
- **Purpose**: Retrieves data
- **Complexity**: 1/10
- **Documentation**: Get detailed methods belonging to a class
- **Returns**: List[CodeEntity]

**`def _extract_base_classes(self, entity: CodeEntity) -> List[str]:`** (line 646)
- **Purpose**: Extract base classes
- **Complexity**: 1/10
- **Documentation**: Extract base classes
- **Returns**: List[str]

**`def _is_static_method(self, entity: CodeEntity) -> bool:`** (line 662)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if method is static
- **Returns**: bool

**`def _is_class_method(self, entity: CodeEntity) -> bool:`** (line 667)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if method is a class method
- **Returns**: bool

**`def _is_property(self, entity: CodeEntity) -> bool:`** (line 672)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if method is a property
- **Returns**: bool

**`def _extract_class_attributes(self, entity: CodeEntity) -> List[Dict[str, Any]]:`** (line 677)
- **Purpose**: Extract class attributes
- **Complexity**: 1/10
- **Documentation**: Extract class attributes
- **Returns**: List[Dict[str, Any]]

**`def _is_abstract_class(self, entity: CodeEntity) -> bool:`** (line 682)
- **Purpose**: Checks condition
- **Complexity**: 1/10
- **Documentation**: Check if class is abstract
- **Returns**: bool

**`def _extract_metaclass(self, entity: CodeEntity) -> Optional[str]:`** (line 687)
- **Purpose**: Extract metaclass information
- **Complexity**: 1/10
- **Documentation**: Extract metaclass information
- **Returns**: Optional[str]

**`def _analyze_dependencies(self, files: Dict[str, Any]) -> Dict[str, Any]:`** (line 692)
- **Purpose**: Analyze module dependencies
- **Complexity**: 1/10
- **Documentation**: Analyze module dependencies
- **Returns**: Dict[str, Any]

**`def _build_enhanced_feature_map(self) -> Dict[str, List[Dict[str, Any]]]:`** (line 706)
- **Purpose**: Build enhanced feature map with detailed locations
- **Complexity**: 1/10
- **Documentation**: Build enhanced feature map with detailed locations
- **Returns**: Dict[str, List[Dict[str, Any]]]

**`def _build_detailed_class_hierarchy(self) -> Dict[str, Any]:`** (line 765)
- **Purpose**: Build detailed class hierarchy information
- **Complexity**: 1/10
- **Documentation**: Build detailed class hierarchy information
- **Returns**: Dict[str, Any]

**`def _identify_entry_points(self) -> List[Dict[str, Any]]:`** (line 784)
- **Purpose**: Identify entry points in the codebase
- **Complexity**: 1/10
- **Documentation**: Identify entry points in the codebase
- **Returns**: List[Dict[str, Any]]

**`def _analyze_data_flows(self) -> List[Dict[str, Any]]:`** (line 811)
- **Purpose**: Analyze data flows in the codebase
- **Complexity**: 1/10
- **Documentation**: Analyze data flows in the codebase
- **Returns**: List[Dict[str, Any]]

**`def _identify_architecture_patterns(self) -> List[Dict[str, Any]]:`** (line 844)
- **Purpose**: Identify architectural patterns in the codebase
- **Complexity**: 1/10
- **Documentation**: Identify architectural patterns in the codebase
- **Returns**: List[Dict[str, Any]]

**`def _analyze_project_structure(self, files: Dict[str, Any]) -> Dict[str, Any]:`** (line 870)
- **Purpose**: Analyze overall project structure
- **Complexity**: 1/10
- **Documentation**: Analyze overall project structure
- **Returns**: Dict[str, Any]

**`def _calculate_code_quality_metrics(self, files: Dict[str, Any]) -> Dict[str, Any]:`** (line 901)
- **Purpose**: Calculate code quality metrics
- **Complexity**: 1/10
- **Documentation**: Calculate code quality metrics
- **Returns**: Dict[str, Any]

**`def _calculate_complexity_distribution(self, files: Dict[str, Any]) -> Dict[str, int]:`** (line 915)
- **Purpose**: Calculate complexity distribution across files
- **Complexity**: 3/10
- **Documentation**: Calculate complexity distribution across files
- **Returns**: Dict[str, int]

**`def _infer_detailed_module_purpose(self, file_path: str, content: Dict[str, Any]) -> str:`** (line 930)
- **Purpose**: Infer detailed module purpose
- **Complexity**: 1/10
- **Documentation**: Infer detailed module purpose
- **Returns**: str

**`def format_summary_markdown(self, summary: Dict[str, Any]) -> str:`** (line 957)
- **Purpose**: Format comprehensive summary as detailed Markdown optimized for LLM context
- **Complexity**: 1/10
- **Documentation**: Format comprehensive summary as detailed Markdown optimized for LLM context
- **Returns**: str

**`def invoke(ctx):`** (line 1344)
- **Purpose**: General purpose function
- **Complexity**: 1/10
- **Parameters**: ctx


## Module Dependencies
Understanding module interconnections:

### `autodoc.cli`
**Imports**: 21 dependencies
**Complexity**: 57

## Key Functions Reference
Most important functions for understanding the codebase:

### `cli`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:1196`
- **Purpose**: Autodoc - AI-powered code intelligence

### `check`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:1254`
- **Purpose**: Check dependencies and configuration

### `generate_summary`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:1273`
- **Purpose**: Generate a comprehensive codebase summary optimized for LLM context

### `generate_summary`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:202`
- **Purpose**: Generate a comprehensive codebase summary optimized for LLM context

### `format_summary_markdown`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:957`
- **Purpose**: Format comprehensive summary as detailed Markdown optimized for LLM context

## Class Hierarchy
Object-oriented structure and relationships:

### `CodeEntity`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:28`
- **Documentation**: No description
- **Methods**: cli, check, generate_summary, main, analyze_file, __init__, __init__, save, load, generate_summary
  *...and 11 more*

### `SimpleASTAnalyzer`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:38`
- **Documentation**: No description
- **Methods**: cli, check, generate_summary, main, analyze_file, __init__, __init__, save, load, generate_summary
  *...and 11 more*

### `OpenAIEmbedder`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:70`
- **Documentation**: No description
- **Methods**: cli, check, generate_summary, main, __init__, __init__, save, load, generate_summary, _extract_purpose
  *...and 11 more*

### `SimpleAutodoc`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:100`
- **Documentation**: No description
- **Methods**: cli, check, generate_summary, main, __init__, save, load, generate_summary, _extract_purpose, _get_class_methods
  *...and 11 more*

### `Autodoc`
- **Module**: `autodoc.cli`
- **Location**: `cli.py:1332`
- **Documentation**: Public API
- **Inherits from**: SimpleAutodoc
- **Methods**: main, invoke

---
*This documentation was automatically generated by Autodoc.*
*For the most up-to-date information, regenerate this document after code changes.*