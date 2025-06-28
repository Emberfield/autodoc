"""
API server for Autodoc with support for node connections and graph queries.
Provides REST endpoints for managing relationships between code entities.
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Set

from aiohttp import web, WSMsgType
from aiohttp_cors import ResourceOptions
from aiohttp_cors import setup as setup_cors

from .analyzer import CodeEntity, EnhancedASTAnalyzer
from .autodoc import SimpleAutodoc
from .graph import CodeGraphBuilder, CodeGraphQuery, GraphConfig
from .ot_engine import OTWebSocketInterface

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIServer:
    """API server for Autodoc with enhanced node connection capabilities."""

    def __init__(
        self, host: str = "localhost", port: int = 8080, graph_config: Optional[GraphConfig] = None
    ):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.autodoc: Optional[SimpleAutodoc] = None
        self.graph_builder: Optional[CodeGraphBuilder] = None
        self.graph_query: Optional[CodeGraphQuery] = None
        self.graph_config = graph_config or GraphConfig.from_env()
        self.websockets: Set[web.WebSocketResponse] = set() # Store active WebSocket connections
        self.ot_interface: OTWebSocketInterface = OTWebSocketInterface() # OT Engine interface

        # Setup CORS
        self._setup_cors()

        # Setup routes
        self._setup_routes()

        # Initialize components
        self._initialize_components()

    def _setup_cors(self):
        """Configure CORS settings."""
        cors = setup_cors(
            self.app,
            defaults={
                "*": ResourceOptions(
                    allow_credentials=True, expose_headers="*", allow_headers="*", allow_methods="*"
                )
            },
        )

        # Apply CORS to all routes
        for route in self.app.router.routes():
            cors.add(route)

    def _setup_routes(self):
        """Setup API routes."""
        # Health check
        self.app.router.add_get("/health", self.health_check)

        # Node management
        self.app.router.add_get("/api/nodes", self.get_nodes)
        self.app.router.add_get("/api/nodes/{node_id}", self.get_node)
        self.app.router.add_post("/api/nodes/analyze", self.analyze_codebase)

        # Relationship management
        self.app.router.add_get("/api/relationships", self.get_relationships)
        self.app.router.add_post("/api/relationships", self.create_relationship)
        self.app.router.add_delete("/api/relationships/{rel_id}", self.delete_relationship)

        # Graph operations
        self.app.router.add_get("/api/graph/stats", self.get_graph_stats)
        self.app.router.add_post("/api/graph/build", self.build_graph)
        self.app.router.add_post("/api/graph/query", self.query_graph)

        # WebSocket endpoint
        self.app.router.add_get("/ws", self.websocket_handler)

        # Search functionality
        self.app.router.add_post("/api/search", self.search_entities)

        # Entity classification
        self.app.router.add_get("/api/entities/internal", self.get_internal_entities)
        self.app.router.add_get("/api/entities/external", self.get_external_entities)
        self.app.router.add_get("/api/entities/endpoints", self.get_api_endpoints)

    def _initialize_components(self):
        """Initialize Autodoc and graph components."""
        try:
            self.autodoc = SimpleAutodoc()
            self.graph_builder = CodeGraphBuilder(self.graph_config)
            self.graph_query = CodeGraphQuery(self.graph_config)
            logger.info("API server components initialized successfully")
        except Exception as e:
            logger.warning(f"Some components failed to initialize: {e}")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        status = {
            "status": "healthy",
            "autodoc_loaded": self.autodoc is not None,
            "graph_available": self.graph_builder and self.graph_builder.driver is not None,
            "entities_count": len(self.autodoc.entities) if self.autodoc else 0,
        }
        return web.json_response(status)

    async def analyze_codebase(self, request: web.Request) -> web.Response:
        """Analyze a codebase and extract entities."""
        try:
            data = await request.json()
            path = data.get("path")
            use_enhanced = data.get("enhanced", True)
            save_cache = data.get("save", True)

            if not path:
                return web.json_response({"error": "Missing 'path' parameter"}, status=400)

            path_obj = Path(path)
            if not path_obj.exists():
                return web.json_response({"error": f"Path does not exist: {path}"}, status=400)

            # Use enhanced analyzer if requested
            if use_enhanced:
                analyzer = EnhancedASTAnalyzer()
            else:
                from .analyzer import SimpleASTAnalyzer

                analyzer = SimpleASTAnalyzer()

            # Analyze the codebase
            if not self.autodoc:
                self.autodoc = SimpleAutodoc()

            # Replace the analyzer with enhanced version
            self.autodoc.analyzer = analyzer

            if path_obj.is_dir():
                await self.autodoc.analyze_directory_async(path_obj, save=save_cache)
            else:
                await self.autodoc.analyze_file_async(path_obj, save=save_cache)

            # Return analysis results
            result = {
                "message": f"Successfully analyzed {path}",
                "entities_count": len(self.autodoc.entities),
                "internal_count": len([e for e in self.autodoc.entities if e.is_internal]),
                "external_count": len([e for e in self.autodoc.entities if not e.is_internal]),
                "api_endpoints_count": len([e for e in self.autodoc.entities if e.endpoint_type]),
            }

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error analyzing codebase: {e}")
            return web.json_response({"error": f"Analysis failed: {str(e)}"}, status=500)

    async def get_nodes(self, request: web.Request) -> web.Response:
        """Get all nodes/entities with optional filtering."""
        try:
            if not self.autodoc or not self.autodoc.entities:
                return web.json_response(
                    {"error": "No entities loaded. Run analysis first."}, status=400
                )

            # Parse query parameters
            entity_type = request.query.get("type")
            is_internal = request.query.get("internal")
            framework = request.query.get("framework")
            endpoint_type = request.query.get("endpoint_type")

            entities = self.autodoc.entities

            # Apply filters
            if entity_type:
                entities = [e for e in entities if e.type == entity_type]

            if is_internal is not None:
                internal_bool = is_internal.lower() == "true"
                entities = [e for e in entities if e.is_internal == internal_bool]

            if framework:
                entities = [e for e in entities if e.framework == framework]

            if endpoint_type:
                entities = [e for e in entities if e.endpoint_type == endpoint_type]

            # Convert to serializable format
            result = {
                "entities": [self._entity_to_dict(e) for e in entities],
                "total_count": len(entities),
                "filters_applied": {
                    "type": entity_type,
                    "internal": is_internal,
                    "framework": framework,
                    "endpoint_type": endpoint_type,
                },
            }

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return web.json_response({"error": f"Failed to get nodes: {str(e)}"}, status=500)

    async def get_node(self, request: web.Request) -> web.Response:
        """Get a specific node by ID."""
        try:
            node_id = request.match_info["node_id"]

            if not self.autodoc or not self.autodoc.entities:
                return web.json_response({"error": "No entities loaded"}, status=400)

            # Find entity by ID (using combination of name and file_path)
            entity = None
            for e in self.autodoc.entities:
                entity_id = f"{e.name}_{hash(e.file_path)}"
                if entity_id == node_id:
                    entity = e
                    break

            if not entity:
                return web.json_response({"error": f"Node not found: {node_id}"}, status=404)

            return web.json_response(self._entity_to_dict(entity))

        except Exception as e:
            logger.error(f"Error getting node: {e}")
            return web.json_response({"error": f"Failed to get node: {str(e)}"}, status=500)

    async def create_relationship(self, request: web.Request) -> web.Response:
        """Create a custom relationship between nodes."""
        try:
            data = await request.json()

            # Validate required fields
            required_fields = ["source", "target", "relationship"]
            for field in required_fields:
                if field not in data:
                    return web.json_response(
                        {"error": f"Missing required field: {field}"}, status=400
                    )

            source = data["source"]
            target = data["target"]
            relationship = data["relationship"]
            metadata = data.get("metadata", {})

            # Create relationship in graph database
            if self.graph_builder and self.graph_builder.driver:
                with self.graph_builder.driver.session() as session:
                    # Create custom relationship
                    query = """
                    MATCH (s) WHERE s.name = $source_name AND s.file_path = $source_file
                    MATCH (t) WHERE t.name = $target_name
                    CREATE (s)-[r:CUSTOM_RELATION {
                        type: $relationship,
                        metadata: $metadata,
                        created_at: datetime()
                    }]->(t)
                    RETURN r
                    """

                    result = session.run(
                        query,
                        source_name=source.get("name"),
                        source_file=source.get("file"),
                        target_name=target.get("name"),
                        relationship=relationship,
                        metadata=json.dumps(metadata),
                    )

                    if result.single():
                        return web.json_response(
                            {
                                "message": "Relationship created successfully",
                                "source": source,
                                "target": target,
                                "relationship": relationship,
                                "metadata": metadata,
                            }
                        )
                    else:
                        return web.json_response(
                            {"error": "Failed to create relationship - nodes not found"}, status=400
                        )
            else:
                return web.json_response({"error": "Graph database not available"}, status=503)

        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return web.json_response(
                {"error": f"Failed to create relationship: {str(e)}"}, status=500
            )

    async def get_relationships(self, request: web.Request) -> web.Response:
        """Get relationships with optional filtering."""
        try:
            if not self.graph_query or not self.graph_query.driver:
                return web.json_response({"error": "Graph database not available"}, status=503)

            relationship_type = request.query.get("type")
            source_node = request.query.get("source")

            with self.graph_query.driver.session() as session:
                if relationship_type:
                    query = """
                    MATCH (s)-[r]->(t)
                    WHERE type(r) = $rel_type
                    RETURN s.name as source, t.name as target, type(r) as relationship, r as props
                    """
                    result = session.run(query, rel_type=relationship_type)
                elif source_node:
                    query = """
                    MATCH (s)-[r]->(t)
                    WHERE s.name = $source
                    RETURN s.name as source, t.name as target, type(r) as relationship, r as props
                    """
                    result = session.run(query, source=source_node)
                else:
                    query = """
                    MATCH (s)-[r]->(t)
                    RETURN s.name as source, t.name as target, type(r) as relationship, r as props
                    LIMIT 100
                    """
                    result = session.run(query)

                relationships = []
                for record in result:
                    relationships.append(
                        {
                            "source": record["source"],
                            "target": record["target"],
                            "relationship": record["relationship"],
                            "properties": dict(record["props"]) if record["props"] else {},
                        }
                    )

                return web.json_response(
                    {"relationships": relationships, "count": len(relationships)}
                )

        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return web.json_response(
                {"error": f"Failed to get relationships: {str(e)}"}, status=500
            )

    async def delete_relationship(self, request: web.Request) -> web.Response:
        """Delete a relationship."""
        # Implementation for deleting relationships
        return web.json_response({"message": "Delete relationship endpoint - not implemented yet"})

    async def get_graph_stats(self, request: web.Request) -> web.Response:
        """Get graph statistics."""
        try:
            if not self.graph_query or not self.graph_query.driver:
                return web.json_response({"error": "Graph database not available"}, status=503)

            with self.graph_query.driver.session() as session:
                # Count nodes by type
                node_counts = {}
                result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
                for record in result:
                    labels = record["labels"]
                    if labels:
                        node_counts[labels[0]] = record["count"]

                # Count relationships by type
                rel_counts = {}
                result = session.run(
                    "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count"
                )
                for record in result:
                    rel_counts[record["rel_type"]] = record["count"]

                # Get total counts
                total_nodes = sum(node_counts.values())
                total_relationships = sum(rel_counts.values())

                stats = {
                    "total_nodes": total_nodes,
                    "total_relationships": total_relationships,
                    "node_types": node_counts,
                    "relationship_types": rel_counts,
                }

                return web.json_response(stats)

        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return web.json_response({"error": f"Failed to get graph stats: {str(e)}"}, status=500)

    async def build_graph(self, request: web.Request) -> web.Response:
        """Build graph from analyzed entities."""
        try:
            if not self.autodoc or not self.autodoc.entities:
                return web.json_response(
                    {"error": "No entities loaded. Run analysis first."}, status=400
                )

            if not self.graph_builder:
                return web.json_response({"error": "Graph builder not available"}, status=503)

            # Build graph
            self.graph_builder.build_from_autodoc(self.autodoc)

            return web.json_response(
                {
                    "message": "Graph built successfully",
                    "entities_processed": len(self.autodoc.entities),
                }
            )

        except Exception as e:
            logger.error(f"Error building graph: {e}")
            return web.json_response({"error": f"Failed to build graph: {str(e)}"}, status=500)

    async def query_graph(self, request: web.Request) -> web.Response:
        """Execute custom graph queries."""
        try:
            data = await request.json()
            query = data.get("query")
            params = data.get("params", {})

            if not query:
                return web.json_response({"error": "Missing 'query' parameter"}, status=400)

            if not self.graph_query or not self.graph_query.driver:
                return web.json_response({"error": "Graph database not available"}, status=503)

            with self.graph_query.driver.session() as session:
                result = session.run(query, params)
                records = [dict(record) for record in result]

                return web.json_response({"results": records, "count": len(records)})

        except Exception as e:
            logger.error(f"Error executing graph query: {e}")
            return web.json_response({"error": f"Query execution failed: {str(e)}"}, status=500)

    async def search_entities(self, request: web.Request) -> web.Response:
        """Search entities using semantic or text search."""
        try:
            data = await request.json()
            query = data.get("query")
            limit = data.get("limit", 10)

            if not query:
                return web.json_response({"error": "Missing 'query' parameter"}, status=400)

            if not self.autodoc:
                return web.json_response({"error": "Autodoc not initialized"}, status=400)

            # Perform search
            results = await self.autodoc.search_async(query, limit=limit)

            # Convert results to serializable format
            search_results = []
            for entity, score in results:
                result_dict = self._entity_to_dict(entity)
                result_dict["score"] = score
                search_results.append(result_dict)

            return web.json_response(
                {"results": search_results, "query": query, "count": len(search_results)}
            )

        except Exception as e:
            logger.error(f"Error in search: {e}")
            return web.json_response({"error": f"Search failed: {str(e)}"}, status=500)

    async def get_internal_entities(self, request: web.Request) -> web.Response:
        """Get all internal entities."""
        try:
            if not self.autodoc or not self.autodoc.entities:
                return web.json_response({"error": "No entities loaded"}, status=400)

            internal_entities = [e for e in self.autodoc.entities if e.is_internal]

            return web.json_response(
                {
                    "entities": [self._entity_to_dict(e) for e in internal_entities],
                    "count": len(internal_entities),
                }
            )

        except Exception as e:
            logger.error(f"Error getting internal entities: {e}")
            return web.json_response(
                {"error": f"Failed to get internal entities: {str(e)}"}, status=500
            )

    async def get_external_entities(self, request: web.Request) -> web.Response:
        """Get all external entities."""
        try:
            if not self.autodoc or not self.autodoc.entities:
                return web.json_response({"error": "No entities loaded"}, status=400)

            external_entities = [e for e in self.autodoc.entities if not e.is_internal]

            return web.json_response(
                {
                    "entities": [self._entity_to_dict(e) for e in external_entities],
                    "count": len(external_entities),
                }
            )

        except Exception as e:
            logger.error(f"Error getting external entities: {e}")
            return web.json_response(
                {"error": f"Failed to get external entities: {str(e)}"}, status=500
            )

    async def get_api_endpoints(self, request: web.Request) -> web.Response:
        """Get all detected API endpoints."""
        try:
            if not self.autodoc or not self.autodoc.entities:
                return web.json_response({"error": "No entities loaded"}, status=400)

            api_endpoints = [e for e in self.autodoc.entities if e.endpoint_type]

            # Group by framework
            by_framework = {}
            for entity in api_endpoints:
                framework = entity.framework or "unknown"
                if framework not in by_framework:
                    by_framework[framework] = []
                by_framework[framework].append(self._entity_to_dict(entity))

            return web.json_response(
                {
                    "endpoints": [self._entity_to_dict(e) for e in api_endpoints],
                    "by_framework": by_framework,
                    "total_count": len(api_endpoints),
                }
            )

        except Exception as e:
            logger.error(f"Error getting API endpoints: {e}")
            return web.json_response(
                {"error": f"Failed to get API endpoints: {str(e)}"}, status=500
            )

    async def websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handles WebSocket connections for real-time collaboration."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        logger.info(f"WebSocket connection established: {ws.peername}. Total active connections: {len(self.websockets)}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    document_id = data.get("document_id", "default_doc") # Assuming a document_id
                    operation_data = data.get("operation")

                    if operation_data:
                        try:
                            # Handle the operation using the OT engine
                            result = await self.ot_interface.handle_operation(document_id, operation_data)
                            # Broadcast the updated document state or transformed operation
                            await self.broadcast(result, sender_ws=ws)
                        except Exception as ot_e:
                            logger.error(f"OT Engine error: {ot_e}")
                            await self.send_json(ws, {"error": str(ot_e)})
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket connection error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"WebSocket connection closed. Total active connections: {len(self.websockets)}")
        return ws

    async def broadcast(self, message: Dict[str, Any], sender_ws: Optional[web.WebSocketResponse] = None):
        """Broadcasts a message to all connected WebSocket clients, optionally skipping the sender."""
        for ws in list(self.websockets): # Iterate over a copy to allow modification during iteration
            if ws != sender_ws:
                try:
                    await self.send_json(ws, message)
                except Exception as e:
                    logger.error(f"Error broadcasting message to {ws.peername}: {e}")

    async def send_json(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Sends a JSON message over a WebSocket connection."""
        await ws.send_json(data)

    def _entity_to_dict(self, entity: CodeEntity) -> Dict[str, Any]:
        """Convert CodeEntity to dictionary for JSON serialization."""
        entity_dict = asdict(entity)

        # Generate entity ID
        entity_dict["id"] = f"{entity.name}_{hash(entity.file_path)}"

        # Remove embedding for API responses (too large)
        if "embedding" in entity_dict:
            entity_dict["has_embedding"] = entity_dict["embedding"] is not None
            del entity_dict["embedding"]

        return entity_dict

    def run(self):
        """Run the API server."""
        logger.info(f"Starting Autodoc API server on {self.host}:{self.port}")
        web.run_app(self.app, host=self.host, port=self.port)


def create_app(graph_config: Optional[GraphConfig] = None) -> web.Application:
    """Create and configure the aiohttp application."""
    server = APIServer(graph_config=graph_config)
    return server.app


if __name__ == "__main__":
    # Run the server directly
    server = APIServer()
    server.run()
