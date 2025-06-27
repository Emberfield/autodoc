# typescript_analyzer - Module Enrichment

**File:** `src/autodoc/typescript_analyzer.py`
**Last Updated:** 2025-06-27T07:47:21.520667
**Total Entities:** 44
**Functions:** 42
**Classes:** 2

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__init__` (line 53)

#### `__post_init__` (line 43)

#### `_analyze_class` (line 289)
> Analyze a class declaration node.

#### `_analyze_content_fallback` (line 748)
> Analyze TypeScript content using regex patterns.

#### `_analyze_function` (line 223)
> Analyze a function declaration node.

#### `_analyze_interface` (line 321)
> Analyze an interface declaration node.

#### `_analyze_method` (line 257)
> Analyze a method definition node.

#### `_analyze_node` (line 180)
> Recursively analyze a tree-sitter node and extract entities.

#### `_analyze_type_alias` (line 350)
> Analyze a type alias declaration.

#### `_analyze_variable_function` (line 376)
> Analyze variable declarations that might be function assignments.

#### `_classify_internal_vs_external` (line 702)
> Classify if entity represents internal or external functionality.

#### `_enhance_with_api_detection` (line 425)
> Enhance entity with API framework detection and classification.

#### `_extract_access_modifier` (line 558)
> Extract access modifier (public, private, protected).

#### `_extract_access_modifier_fallback` (line 847)
> Extract access modifier from line using regex.

#### `_extract_extends_class` (line 573)
> Extract extended class name.

#### `_extract_extends_interface` (line 596)
> Extract extended interface name.

#### `_extract_external_domain_from_calls` (line 735)
> Extract domain from external API calls.

#### `_extract_function_parameters` (line 503)
> Extract function parameters with types.

#### `_extract_generic_parameters` (line 547)
> Extract generic type parameters.

#### `_extract_http_methods_from_code` (line 611)
> Extract HTTP methods from Express/Fastify style code.

#### `_extract_implements_interfaces` (line 583)
> Extract implemented interface names.

#### `_extract_imports` (line 412)
> Extract import statements from the file.

#### `_extract_imports_fallback` (line 742)
> Extract import statements using regex.

#### `_extract_jsdoc_comment` (line 462)
> Extract JSDoc comment preceding a node.

#### `_extract_nestjs_decorators` (line 639)
> Extract NestJS decorators.

#### `_extract_nestjs_http_methods` (line 649)
> Extract HTTP methods from NestJS decorators.

#### `_extract_nestjs_route_path` (line 668)
> Extract route path from NestJS decorators.

#### `_extract_return_type` (line 536)
> Extract return type annotation.

#### `_extract_route_path_from_code` (line 630)
> Extract route path from Express/Fastify style code.

#### `_find_external_calls_in_code` (line 678)
> Find external API calls in the code.

#### `_get_node_text` (line 458)
> Extract text content from a tree-sitter node.

#### `_initialize_parser` (line 86)
> Initialize tree-sitter parser for TypeScript.

#### `_is_abstract_class` (line 606)
> Check if class is abstract.

#### `_is_async_function` (line 488)
> Check if a function is async.

#### `_is_exported` (line 493)
> Check if a declaration is exported.

#### `_is_static_method` (line 568)
> Check if method is static.

#### `_parse_parameter` (line 517)
> Parse a single parameter node.

#### `_use_fallback_parser` (line 98)
> Use regex-based fallback parser when tree-sitter is not available.

#### `analyze_directory` (line 138)
> Analyze all TypeScript files in a directory.

#### `analyze_file` (line 107)
> Analyze a single TypeScript file and extract code entities.

#### `is_available` (line 103)
> Check if TypeScript parsing is available.

#### `traverse_for_imports` (line 416)

### Classes

#### `TypeScriptAnalyzer` (line 50)
> Analyzes TypeScript files using tree-sitter to extract code entities.

#### `TypeScriptEntity` (line 27)
> Extended CodeEntity for TypeScript-specific properties.
