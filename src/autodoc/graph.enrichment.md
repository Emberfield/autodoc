# graph - Module Enrichment

**File:** `src/autodoc/graph.py`
**Last Updated:** 2025-06-27T07:47:21.518941
**Total Entities:** 32
**Functions:** 28
**Classes:** 4

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__init__` (line 46)

#### `__init__` (line 328)

#### `__init__` (line 486)

#### `_connect` (line 51)
> Establish connection to Neo4j

#### `_connect` (line 333)
> Establish connection to Neo4j

#### `_create_class_node` (line 212)
> Create a Class node

#### `_create_contains_relationship` (line 234)
> Create CONTAINS relationship between file and entity

#### `_create_entity_node` (line 176)
> Create a node for a code entity

#### `_create_entity_relationships` (line 251)
> Create relationships between entities (calls, imports, etc.)

#### `_create_file_node` (line 145)
> Create a File node

#### `_create_function_node` (line 183)
> Create a Function node

#### `_create_import_relationship` (line 290)
> Create IMPORTS relationship

#### `_create_indexes` (line 115)
> Create indexes for better query performance

#### `_create_method_relationship` (line 303)
> Create HAS_METHOD relationship between class and method

#### `build_from_autodoc` (line 79)
> Build graph from analyzed code entities

#### `clear_graph` (line 70)
> Clear all nodes and relationships

#### `close` (line 65)
> Close database connection

#### `close` (line 343)
> Close database connection

#### `create_complexity_heatmap` (line 653)
> Create a complexity heatmap using plotly

#### `create_interactive_graph` (line 489)
> Create an interactive graph visualization using pyvis

#### `create_module_dependency_graph` (line 611)
> Create a module dependency graph

#### `find_code_patterns` (line 413)
> Identify common code patterns

#### `find_dependencies` (line 389)
> Find what an entity depends on and what depends on it

#### `find_entry_points` (line 348)
> Find all entry points (main functions, CLI commands)

#### `find_test_coverage` (line 363)
> Analyze test coverage

#### `from_env` (line 33)
> Load configuration from environment variables

#### `get_module_complexity` (line 455)
> Calculate complexity metrics for each module

#### `main` (line 703)
> Example usage of the graph functionality

### Classes

#### `CodeGraphBuilder` (line 43)
> Builds a graph representation of code in Neo4j

#### `CodeGraphQuery` (line 325)
> Query and analyze the code graph

#### `CodeGraphVisualizer` (line 483)
> Visualize the code graph

#### `GraphConfig` (line 24)
> Configuration for graph database connection
