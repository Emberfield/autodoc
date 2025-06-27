# analyzer - Module Enrichment

**File:** `src/autodoc/analyzer.py`
**Last Updated:** 2025-06-27T07:47:21.519209
**Total Entities:** 21
**Functions:** 18
**Classes:** 3

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__init__` (line 120)

#### `_analyze_class_node` (line 257)
> Analyze class node for patterns.

#### `_analyze_function_node` (line 227)
> Analyze function node for API patterns.

#### `_classify_endpoint_type` (line 350)
> Classify the type of endpoint.

#### `_classify_internal_vs_external` (line 404)
> Classify if entity represents internal or external functionality.

#### `_detect_auth_requirement` (line 362)
> Check if authentication is required.

#### `_detect_framework` (line 282)
> Detect web framework from imports and decorators.

#### `_detect_http_methods` (line 302)
> Detect HTTP methods from decorators and function names.

#### `_enhance_entity_analysis` (line 209)
> Enhance entity with detailed analysis.

#### `_extract_decorators` (line 265)
> Extract decorator strings from AST node.

#### `_extract_external_domain` (line 445)
> Extract domain from external API calls.

#### `_extract_file_imports` (line 196)
> Extract all import statements from the AST.

#### `_extract_route_path` (line 334)
> Extract route path from decorators.

#### `_find_external_calls` (line 377)
> Find external API calls within the function.

#### `_find_project_root` (line 173)
> Find project root by looking for common markers.

#### `analyze_directory` (line 79)
> Analyze all Python files in a directory.

#### `analyze_file` (line 43)
> Analyze a single Python file and extract code entities.

#### `analyze_file` (line 148)
> Enhanced analysis with API detection.

### Classes

#### `CodeEntity` (line 17)

#### `EnhancedASTAnalyzer` (line 117)
> Extended analyzer with API endpoint detection and internal/external classification.

#### `SimpleASTAnalyzer` (line 40)
> Analyzes Python files using AST to extract code entities.
