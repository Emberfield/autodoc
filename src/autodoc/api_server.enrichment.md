# api_server - Module Enrichment

**File:** `src/autodoc/api_server.py`
**Last Updated:** 2025-06-27T07:47:21.520171
**Total Entities:** 22
**Functions:** 21
**Classes:** 1

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__init__` (line 28)

#### `_entity_to_dict` (line 548)
> Convert CodeEntity to dictionary for JSON serialization.

#### `_initialize_components` (line 91)
> Initialize Autodoc and graph components.

#### `_setup_cors` (line 48)
> Configure CORS settings.

#### `_setup_routes` (line 63)
> Setup API routes.

#### `analyze_codebase` (line 111)
> Analyze a codebase and extract entities.

#### `build_graph` (line 397)
> Build graph from analyzed entities.

#### `create_app` (line 568)
> Create and configure the aiohttp application.

#### `create_relationship` (line 234)
> Create a custom relationship between nodes.

#### `delete_relationship` (line 352)
> Delete a relationship.

#### `get_api_endpoints` (line 518)
> Get all detected API endpoints.

#### `get_external_entities` (line 497)
> Get all external entities.

#### `get_graph_stats` (line 357)
> Get graph statistics.

#### `get_internal_entities` (line 476)
> Get all internal entities.

#### `get_node` (line 209)
> Get a specific node by ID.

#### `get_nodes` (line 161)
> Get all nodes/entities with optional filtering.

#### `get_relationships` (line 299)
> Get relationships with optional filtering.

#### `health_check` (line 101)
> Health check endpoint.

#### `query_graph` (line 422)
> Execute custom graph queries.

#### `run` (line 562)
> Run the API server.

#### `search_entities` (line 445)
> Search entities using semantic or text search.

### Classes

#### `APIServer` (line 25)
> API server for Autodoc with enhanced node connection capabilities.
