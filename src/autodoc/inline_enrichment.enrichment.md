# inline_enrichment - Module Enrichment

**File:** `src/autodoc/inline_enrichment.py`
**Last Updated:** 2025-06-27T07:47:21.517117
**Total Entities:** 27
**Functions:** 22
**Classes:** 5

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__init__` (line 75)
> The __init__ function is a constructor method in Python, typically used to initialize an instance of a class. It sets up the initial state of the object by assigning values to its attributes based on the parameters provided during instantiation.

#### `__init__` (line 256)

#### `__init__` (line 564)

#### `_backup_file` (line 261)
> Create backup of original file.

#### `_find_entity_node` (line 279)
> Find the AST node for a given entity.

#### `_format_docstring` (line 310)
> Format enriched description as a proper docstring.

#### `_generate_json_enrichment` (line 699)
> Generate JSON enrichment file.

#### `_generate_markdown_enrichment` (line 642)
> Generate markdown enrichment file.

#### `_generate_module_overview` (line 571)
> Generate module overview.

#### `_get_existing_docstring` (line 288)
> Get existing docstring from AST node.

#### `_get_file_hash` (line 156)
> The `_get_file_hash` function computes and returns the hash value of the content of a specified file. This hash value serves as a unique identifier for the file's content, allowing for efficient comparison and verification of file integrity.

#### `_get_module_entities` (line 567)
> Get all entities for a specific module.

#### `_load_cache` (line 100)
> The _load_cache function is responsible for loading a file change cache, which likely stores information about changes made to files in a project. This function retrieves the cached data to optimize performance and avoid redundant file checks.

#### `_parse_python_file` (line 269)
> Parse Python file to AST.

#### `_save_cache` (line 128)
> The _save_cache function is responsible for persisting changes made to a file change cache, ensuring that updates are stored for future reference. It likely interacts with a caching mechanism to maintain state across sessions or operations.

#### `_should_update_docstring` (line 297)
> Determine if docstring should be updated.

#### `_update_file_with_docstrings` (line 335)
> Update file with enriched docstrings.

#### `enrich_files_inline` (line 458)
> Enrich files with inline docstrings.

#### `generate_module_enrichment_files` (line 585)
> Generate module-level enrichment files.

#### `get_changed_files` (line 225)
> Get list of files that have changed.

#### `has_changed` (line 176)
> The `has_changed` function determines whether a specified file has been modified since the last enrichment process. It compares the current file state with a recorded state to identify any changes.

#### `mark_processed` (line 207)
> Mark file as processed.

### Classes

#### `ChangeDetector` (line 61)
> The ChangeDetector class is designed to monitor and identify changes in files, facilitating incremental enrichment processes. It helps in tracking modifications to ensure that updates are efficiently applied without reprocessing unchanged data.

#### `FileChangeInfo` (line 24)
> The `FileChangeInfo` class is designed to encapsulate information regarding changes made to files, specifically for the purpose of incremental enrichment in a software system. It likely tracks attributes such as modified timestamps, change types, and potentially the content changes themselves to facilitate efficient updates.

#### `InlineEnricher` (line 244)
> The InlineEnricher class is designed to enhance Python code files by adding or updating docstrings directly within the code. This functionality aims to improve code documentation and maintainability by ensuring that functions and classes are well-documented inline.

#### `InlineEnrichmentResult` (line 43)
> The InlineEnrichmentResult class encapsulates the outcome of an inline enrichment operation, which typically involves augmenting data with additional context or information. It serves as a structured representation of the results obtained from such an enrichment process.

#### `ModuleEnrichmentGenerator` (line 552)
> The ModuleEnrichmentGenerator class is responsible for generating module-level enrichment files, which likely enhance or augment the documentation or metadata associated with specific modules in a codebase. It serves as a utility for automating the creation of these enrichment files based on predefined criteria or templates.
