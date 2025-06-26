# Comprehensive Codebase Documentation
*Generated on 2025-06-26T12:04:10.755167 with autodoc 0.1.0*

## Executive Summary
This codebase contains 216 functions and 32 classes across 17 files, written primarily in Python.
Total lines analyzed: 7,260
Testing coverage: Comprehensive
Build system: setuptools/build, hatch
CI/CD: GitHub Actions

## Codebase Statistics
- **Total Entities**: 248
- **Public Functions**: 149
- **Private Functions**: 67
- **Test Functions**: 63
- **Documentation Coverage**: 82.7%
- **Average Functions per File**: 12.7
- **Average Classes per File**: 1.9

### Code Quality Metrics
- **Documentation Coverage**: 82.4%
- **Average Complexity**: 16.8
- **Public API Ratio**: 83.8%

## Build System and Tooling
**Build Tools**: setuptools/build, hatch
**Package Managers**: pip

**Configuration Files**:
- `pyproject.toml` - Modern Python packaging (PEP 518)
- `Makefile` - Make build system

**Build Commands**:
- `pip install -e .`
- `make build`
- `make build`

**Project Scripts**:
- `autodoc`: autodoc.cli:main

## Testing System
**Test Files**: 7 files
**Test Functions**: 59 functions
**Testing Frameworks**: pytest

**Test Commands**:
- `pytest`
- `make test`

**Test Directories**:
- `tests`
- `tests/unit`
- `tests/integration`

## CI/CD Configuration
**CI Platforms**: GitHub Actions

**Workflows**:
- **Build and Publish to GCP Artifact Registry**
  - Triggers: unknown
  - Jobs: publish
- **Claude Code**
  - Triggers: unknown
  - Jobs: claude

**CI Configuration Files**:
- `.github/workflows/publish.yml` (GitHub Actions)
- `.github/workflows/claude.yml` (GitHub Actions)

## Deployment and Distribution
**Package Distribution**: PyPI, Docker Registry

## Project Structure
### Directory Organization
- **`.`**: 1 files, 1 functions, 0 classes
- **`src/autodoc`**: 9 files, 152 functions, 18 classes
- **`tests`**: 2 files, 30 functions, 7 classes
- **`tests/integration`**: 1 files, 5 functions, 1 classes
- **`tests/unit`**: 4 files, 28 functions, 6 classes

### File Types
- **`.py`**: 17 files

## Entry Points
Key entry points for understanding code execution flow:
- **Main Function**: `main` in local_graph.py:243
- **Cli Command**: `analyze` in cli_old.py:1816
- **Cli Command**: `search` in cli_old.py:1839
- **Cli Command**: `check` in cli_old.py:1879
- **Main Function**: `main` in cli_old.py:1985
- **Main Function**: `main` in graph.py:702
- **Cli Command**: `analyze` in cli.py:44
- **Main Function**: `main` in cli.py:449

## Feature Map - Where to Find Key Functionality
This section helps you quickly locate code related to specific features:

### Database
- **`TestCodeGraphQuery`** (class) - Test graph query functionality
  - Location: `test_graph.py:127`
  - Module: `tests.test_graph`
- **`test_query_initialization`** (function) - Test function
  - Location: `test_graph.py:130`
  - Module: `tests.test_graph`
- **`format_summary_markdown`** (function) - Format comprehensive summary as detailed Markdown optimized for LLM context
  - Location: `cli_old.py:1444`
  - Module: `autodoc.cli_old`
- **`CodeGraphQuery`** (class) - Query and analyze the code graph
  - Location: `graph.py:325`
  - Module: `autodoc.graph`
- **`MarkdownFormatter`** (class) - Formats code analysis results as detailed Markdown documentation.
  - Location: `summary.py:463`
  - Module: `autodoc.summary`
- **`format_summary_markdown`** (function) - Format comprehensive summary as detailed Markdown optimized for LLM context.
  - Location: `summary.py:466`
  - Module: `autodoc.summary`
- **`query_graph`** (function) - Query the code graph for insights
  - Location: `cli.py:211`
  - Module: `autodoc.cli`
- **`format_summary_markdown`** (function) - Format comprehensive summary as detailed Markdown.
  - Location: `autodoc.py:274`
  - Module: `autodoc.autodoc`
- *...and 3 more related items*

### Api Endpoints
- **`test_initialization_without_api_key`** (function) - Test function
  - Location: `test_autodoc.py:193`
  - Module: `tests.unit.test_autodoc`
- **`test_initialization_with_api_key`** (function) - Test function
  - Location: `test_autodoc.py:201`
  - Module: `tests.unit.test_autodoc`
- **`test_api_key_initialization`** (function) - Test function
  - Location: `test_embedder.py:43`
  - Module: `tests.unit.test_embedder`
- **`test_full_python_api_workflow`** (function) - Test function
  - Location: `test_end_to_end.py:20`
  - Module: `tests.integration.test_end_to_end`

### Data Processing
- **`ProjectAnalyzer`** (class) - Analyzes project configuration, build systems, testing, and CI/CD setup.
  - Location: `project_analyzer.py:11`
  - Module: `autodoc.project_analyzer`
- **`analyze_build_system`** (function) - Analyze build system configuration and tools.
  - Location: `project_analyzer.py:17`
  - Module: `autodoc.project_analyzer`
- **`analyze_test_system`** (function) - Test function
  - Location: `project_analyzer.py:126`
  - Module: `autodoc.project_analyzer`
- **`analyze_ci_configuration`** (function) - Analyze CI/CD configuration.
  - Location: `project_analyzer.py:232`
  - Module: `autodoc.project_analyzer`
- **`analyze_deployment_configuration`** (function) - Analyze deployment and distribution configuration.
  - Location: `project_analyzer.py:349`
  - Module: `autodoc.project_analyzer`
- **`SimpleASTAnalyzer`** (class) - General purpose function
  - Location: `cli_old.py:38`
  - Module: `autodoc.cli_old`
- **`analyze`** (function) - Analyze a codebase
  - Location: `cli_old.py:1816`
  - Module: `autodoc.cli_old`
- **`analyze_file`** (function) - General purpose function
  - Location: `cli_old.py:39`
  - Module: `autodoc.cli_old`
- *...and 27 more related items*

### File Operations
- **`sample_python_file`** (function) - Create a sample Python file for testing
  - Location: `conftest.py:13`
  - Module: `tests.conftest`
- **`sample_test_file`** (function) - Test function
  - Location: `conftest.py:80`
  - Module: `tests.conftest`
- **`test_file_type_detection`** (function) - Test function
  - Location: `test_graph.py:366`
  - Module: `tests.test_graph`
- **`load_entities`** (function) - Load entities from autodoc cache
  - Location: `local_graph.py:29`
  - Module: `autodoc.local_graph`
- **`create_file_dependency_graph`** (function) - Creates new objects
  - Location: `local_graph.py:40`
  - Module: `autodoc.local_graph`
- **`analyze_file`** (function) - General purpose function
  - Location: `cli_old.py:39`
  - Module: `autodoc.cli_old`
- **`save`** (function) - General purpose function
  - Location: `cli_old.py:187`
  - Module: `autodoc.cli_old`
- **`load`** (function) - General purpose function
  - Location: `cli_old.py:193`
  - Module: `autodoc.cli_old`
- *...and 10 more related items*

### Testing
- **`sample_python_file`** (function) - Create a sample Python file for testing
  - Location: `conftest.py:13`
  - Module: `tests.conftest`
- **`sample_test_file`** (function) - Test function
  - Location: `conftest.py:80`
  - Module: `tests.conftest`
- **`sample_project_dir`** (function) - Create a sample project directory structure
  - Location: `conftest.py:99`
  - Module: `tests.conftest`
- **`sample_code_entities`** (function) - Sample CodeEntity objects for testing
  - Location: `conftest.py:130`
  - Module: `tests.conftest`
- **`TestGraphConfig`** (class) - Test graph configuration
  - Location: `test_graph.py:27`
  - Module: `tests.test_graph`
- **`TestCodeGraphBuilder`** (class) - Test graph builder functionality
  - Location: `test_graph.py:57`
  - Module: `tests.test_graph`
- **`TestCodeGraphQuery`** (class) - Test graph query functionality
  - Location: `test_graph.py:127`
  - Module: `tests.test_graph`
- **`TestCodeGraphVisualizer`** (class) - Test graph visualization functionality
  - Location: `test_graph.py:199`
  - Module: `tests.test_graph`
- *...and 72 more related items*

### Cli Commands
- **`test_cli_commands_imported`** (function) - Test function
  - Location: `test_graph.py:399`
  - Module: `tests.test_graph`
- **`test_graph_commands_handle_missing_deps`** (function) - Test function
  - Location: `test_graph.py:421`
  - Module: `tests.test_graph`
- **`CodeEntity`** (class) - General purpose function
  - Location: `cli_old.py:28`
  - Module: `autodoc.cli_old`
- **`SimpleASTAnalyzer`** (class) - General purpose function
  - Location: `cli_old.py:38`
  - Module: `autodoc.cli_old`
- **`OpenAIEmbedder`** (class) - General purpose function
  - Location: `cli_old.py:75`
  - Module: `autodoc.cli_old`
- **`SimpleAutodoc`** (class) - General purpose function
  - Location: `cli_old.py:97`
  - Module: `autodoc.cli_old`
- **`cli`** (function) - Autodoc - AI-powered code intelligence
  - Location: `cli_old.py:1808`
  - Module: `autodoc.cli_old`
- **`analyze`** (function) - Analyze a codebase
  - Location: `cli_old.py:1816`
  - Module: `autodoc.cli_old`
- *...and 77 more related items*

### Async Operations
- **`demo`** (function) - Run a demo of Autodoc features
  - Location: `demo.py:18`
  - Module: `demo`
- **`embed`** (function) - General purpose function
  - Location: `cli_old.py:80`
  - Module: `autodoc.cli_old`
- **`embed_batch`** (function) - General purpose function
  - Location: `cli_old.py:89`
  - Module: `autodoc.cli_old`
- **`analyze_directory`** (function) - General purpose function
  - Location: `cli_old.py:110`
  - Module: `autodoc.cli_old`
- **`search`** (function) - General purpose function
  - Location: `cli_old.py:156`
  - Module: `autodoc.cli_old`
- **`analyze`** (function) - General purpose function
  - Location: `cli_old.py:1981`
  - Module: `autodoc.cli_old`
- **`embed`** (function) - Generate embedding for a single text.
  - Location: `embedder.py:17`
  - Module: `autodoc.embedder`
- **`embed_batch`** (function) - Generate embeddings for multiple texts.
  - Location: `embedder.py:27`
  - Module: `autodoc.embedder`
- *...and 10 more related items*


## Data Flow Analysis
Understanding how data moves through the system:

### Data Input
- **`load_entities`** at `local_graph.py:29` - Loads/reads data
- **`load`** at `cli_old.py:193` - Loads/reads data
- **`load`** at `autodoc.py:105` - Loads/reads data
- **`test_save_and_load`** at `test_autodoc.py:43` - Loads/reads data

### Data Output
- **`save`** at `cli_old.py:187` - Saves/writes data
- **`save`** at `autodoc.py:98` - Saves/writes data
- **`test_analyze_command_with_save`** at `test_cli.py:115` - Saves/writes data

---
*This documentation was automatically generated by Autodoc.*
*For the most up-to-date information, regenerate this document after code changes.*