#!/usr/bin/env python3
"""
Graph database integration for Autodoc using Neo4j.
Visualizes relationships between code entities.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable, ClientError, DatabaseError
from pyvis.network import Network

log = logging.getLogger(__name__)

from .analyzer import CodeEntity
from .autodoc import SimpleAutodoc


@dataclass
class GraphConfig:
    """Configuration for graph database connection"""

    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> "GraphConfig":
        """Load configuration from environment variables"""
        return cls(
            uri=os.getenv("NEO4J_URI", cls.uri),
            username=os.getenv("NEO4J_USERNAME", cls.username),
            password=os.getenv("NEO4J_PASSWORD", cls.password),
            database=os.getenv("NEO4J_DATABASE", cls.database),
        )


class CodeGraphBuilder:
    """Builds a graph representation of code in Neo4j"""

    def __init__(self, config: Optional[GraphConfig] = None):
        self.config = config or GraphConfig.from_env()
        self.driver: Optional[Driver] = None
        self._connect()

    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.uri, auth=(self.config.username, self.config.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            log.info(f"Connected to Neo4j at {self.config.uri}")
        except ServiceUnavailable as e:
            log.warning(f"Neo4j not available at {self.config.uri}: {e}")
            self.driver = None
        except Exception as e:
            log.error(f"Error connecting to Neo4j at {self.config.uri}: {e}")
            self.driver = None

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

    def clear_graph(self):
        """Clear all nodes and relationships"""
        if not self.driver:
            return

        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            log.info("Cleared existing graph data")

    def build_from_autodoc(self, autodoc: SimpleAutodoc):
        """Build graph from analyzed code entities"""
        if not self.driver:
            log.warning("No database connection available")
            return

        # First, clear existing data
        self.clear_graph()

        # Create constraints and indexes
        self._create_indexes()

        # Group entities by file
        files_map = {}
        for entity in autodoc.entities:
            if entity.file_path not in files_map:
                files_map[entity.file_path] = []
            files_map[entity.file_path].append(entity)

        # Create nodes
        with self.driver.session() as session:
            # Create file nodes
            for file_path in files_map:
                self._create_file_node(session, file_path)

            # Create entity nodes and relationships
            for file_path, entities in files_map.items():
                for entity in entities:
                    self._create_entity_node(session, entity)
                    self._create_contains_relationship(session, file_path, entity)

            # Create relationships between entities
            self._create_entity_relationships(session, autodoc)

        log.info(f"Created graph with {len(files_map)} files and {len(autodoc.entities)} entities")

    def _create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE (fn.name, fn.file_path) IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.file_path) IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                except (ClientError, DatabaseError) as e:
                    log.info(f"Note: {e}") # Often means constraint/index already exists

            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.name)",
                "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (m:Module) ON (m.name)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                except (ClientError, DatabaseError) as e:
                    log.info(f"Note: {e}") # Often means constraint/index already exists

    def _create_file_node(self, session, file_path: str):
        """Create a File node"""
        path = Path(file_path)
        module_name = path.stem

        # Determine file type
        file_type = "module"
        if "test" in path.name:
            file_type = "test"
        elif path.name == "__init__.py":
            file_type = "package"
        elif path.name == "setup.py":
            file_type = "setup"

        query = """
        MERGE (f:File {path: $path})
        SET f.name = $name,
            f.module = $module,
            f.type = $type,
            f.directory = $directory
        """

        session.run(
            query,
            path=file_path,
            name=path.name,
            module=module_name,
            type=file_type,
            directory=str(path.parent),
        )

    def _create_entity_node(self, session, entity: CodeEntity):
        """Create a node for a code entity"""
        if entity.type == "function":
            self._create_function_node(session, entity)
        elif entity.type == "class":
            self._create_class_node(session, entity)

    def _create_function_node(self, session, entity: CodeEntity):
        """Create a Function node"""
        # Determine function characteristics
        is_private = entity.name.startswith("_")
        is_test = entity.name.startswith("test_")
        is_async = False  # Would need AST analysis

        query = """
        MERGE (fn:Function {name: $name, file_path: $file_path})
        SET fn.line_number = $line_number,
            fn.docstring = $docstring,
            fn.is_private = $is_private,
            fn.is_test = $is_test,
            fn.is_async = $is_async,
            fn.code_preview = $code
        """

        session.run(
            query,
            name=entity.name,
            file_path=entity.file_path,
            line_number=entity.line_number,
            docstring=entity.docstring or "",
            is_private=is_private,
            is_test=is_test,
            is_async=is_async,
            code=entity.code,
        )

    def _create_class_node(self, session, entity: CodeEntity):
        """Create a Class node"""
        is_private = entity.name.startswith("_")

        query = """
        MERGE (c:Class {name: $name, file_path: $file_path})
        SET c.line_number = $line_number,
            c.docstring = $docstring,
            c.is_private = $is_private,
            c.code_preview = $code
        """

        session.run(
            query,
            name=entity.name,
            file_path=entity.file_path,
            line_number=entity.line_number,
            docstring=entity.docstring or "",
            is_private=is_private,
            code=entity.code,
        )

    def _create_contains_relationship(self, session, file_path: str, entity: CodeEntity):
        """Create CONTAINS relationship between file and entity"""
        if entity.type == "function":
            query = """
            MATCH (f:File {path: $file_path})
            MATCH (fn:Function {name: $name, file_path: $file_path})
            MERGE (f)-[:CONTAINS]->(fn)
            """
        else:  # class
            query = """
            MATCH (f:File {path: $file_path})
            MATCH (c:Class {name: $name, file_path: $file_path})
            MERGE (f)-[:CONTAINS]->(c)
            """

        session.run(query, file_path=file_path, name=entity.name)

    def _create_entity_relationships(self, session, autodoc: SimpleAutodoc):
        """Create relationships between entities (calls, imports, etc.)"""
        # Group entities by file for easier lookup
        entities_by_file = {}
        for entity in autodoc.entities:
            if entity.file_path not in entities_by_file:
                entities_by_file[entity.file_path] = []
            entities_by_file[entity.file_path].append(entity)

        # Analyze imports and create relationships
        for file_path, entities in entities_by_file.items():
            # Get imports for this file
            imports = autodoc._extract_imports(file_path)

            # Create import relationships
            for imp in imports:
                if "import" in imp:
                    # Parse import statement
                    if "from" in imp:
                        # from X import Y
                        parts = imp.split()
                        if len(parts) >= 4:
                            module = parts[1]
                            imported = parts[3]
                            self._create_import_relationship(session, file_path, module, imported)
                    else:
                        # import X
                        parts = imp.split()
                        if len(parts) >= 2:
                            module = parts[1]
                            self._create_import_relationship(session, file_path, module, module)

        # Create method relationships for classes
        for entity in autodoc.entities:
            if entity.type == "class":
                methods = autodoc._get_class_methods_detailed(entity, entity.file_path)
                for method in methods:
                    self._create_method_relationship(session, entity, method)

    def _create_import_relationship(self, session, file_path: str, module: str, imported: str):
        """Create IMPORTS relationship"""
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (m:Module {name: $module})
        MERGE (f)-[:IMPORTS {item: $imported}]->(m)
        """

        try:
            session.run(query, file_path=file_path, module=module, imported=imported)
        except (ClientError, DatabaseError) as e:
            log.error(f"Could not create import relationship: {e}")

    def _create_method_relationship(
        self, session, class_entity: CodeEntity, method_entity: CodeEntity
    ):
        """Create HAS_METHOD relationship between class and method"""
        query = """
        MATCH (c:Class {name: $class_name, file_path: $file_path})
        MATCH (fn:Function {name: $method_name, file_path: $file_path})
        WHERE fn.line_number > c.line_number
        MERGE (c)-[:HAS_METHOD]->(fn)
        """

        try:
            session.run(
                query,
                class_name=class_entity.name,
                method_name=method_entity.name,
                file_path=class_entity.file_path,
            )
        except (ClientError, DatabaseError) as e:
            log.error(f"Could not create method relationship: {e}")


class CodeGraphQuery:
    """Query and analyze the code graph"""

    def __init__(self, config: Optional[GraphConfig] = None):
        self.config = config or GraphConfig.from_env()
        self.driver: Optional[Driver] = None
        self._connect()

    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.uri, auth=(self.config.username, self.config.password)
            )
        except (ServiceUnavailable, Exception) as e:
            log.warning(f"Neo4j not available at {self.config.uri}: {e}")
            self.driver = None

    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()

    def find_entry_points(self) -> List[Dict[str, Any]]:
        """Find all entry points (main functions, CLI commands)"""
        if not self.driver:
            return []

        query = """
        MATCH (fn:Function)
        WHERE fn.name = 'main' OR fn.name CONTAINS 'cli'
        RETURN fn.name as name, fn.file_path as file, fn.docstring as description
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]

    def find_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage"""
        if not self.driver:
            return {}

        queries = {
            "total_functions": "MATCH (fn:Function) WHERE NOT fn.is_test RETURN count(fn) as count",
            "total_tests": "MATCH (fn:Function) WHERE fn.is_test RETURN count(fn) as count",
            "tested_modules": """
                MATCH (f:File)-[:CONTAINS]->(fn:Function)
                WHERE fn.is_test
                RETURN DISTINCT f.module as module
            """,
        }

        results = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query)
                if key == "tested_modules":
                    results[key] = [r["module"] for r in result]
                else:
                    results[key] = result.single()["count"]

        return results

    def find_dependencies(self, entity_name: str) -> Dict[str, List[str]]:
        """Find what an entity depends on and what depends on it"""
        if not self.driver:
            return {"depends_on": [], "depended_by": []}

        queries = {
            "depends_on": """
                MATCH (e {name: $name})-[:CALLS|IMPORTS|USES]->(dep)
                RETURN DISTINCT dep.name as name, labels(dep)[0] as type
            """,
            "depended_by": """
                MATCH (dep)-[:CALLS|IMPORTS|USES]->(e {name: $name})
                RETURN DISTINCT dep.name as name, labels(dep)[0] as type
            """,
        }

        results = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                result = session.run(query, name=entity_name)
                results[key] = [dict(r) for r in result]

        return results

    def find_code_patterns(self) -> Dict[str, Any]:
        """Identify common code patterns"""
        if not self.driver:
            return {}

        patterns = {}

        with self.driver.session() as session:
            # Singleton pattern
            result = session.run(
                """
                MATCH (c:Class)
                WHERE c.name CONTAINS 'Singleton' OR c.docstring CONTAINS 'singleton'
                RETURN c.name as name, c.file_path as file
            """
            )
            patterns["singletons"] = [dict(r) for r in result]

            # Factory pattern
            result = session.run(
                """
                MATCH (e)
                WHERE (e:Class OR e:Function) AND 
                      (e.name CONTAINS 'Factory' OR e.name CONTAINS 'create_')
                RETURN e.name as name, labels(e)[0] as type
            """
            )
            patterns["factories"] = [dict(r) for r in result]

            # API endpoints
            result = session.run(
                """
                MATCH (fn:Function)
                WHERE fn.name CONTAINS 'route' OR fn.name CONTAINS 'endpoint' OR
                      fn.file_path CONTAINS 'api' OR fn.file_path CONTAINS 'views'
                RETURN fn.name as name, fn.file_path as file
            """
            )
            patterns["api_endpoints"] = [dict(r) for r in result]

        return patterns

    def get_module_complexity(self) -> List[Dict[str, Any]]:
        """Calculate complexity metrics for each module"""
        if not self.driver:
            return []

        query = """
        MATCH (f:File)
        OPTIONAL MATCH (f)-[:CONTAINS]->(e)
        WITH f, count(e) as entity_count,
             sum(CASE WHEN e:Function THEN 1 ELSE 0 END) as function_count,
             sum(CASE WHEN e:Class THEN 1 ELSE 0 END) as class_count
        MATCH (f)-[:IMPORTS]->(m:Module)
        WITH f, entity_count, function_count, class_count, count(m) as import_count
        RETURN f.name as file,
               f.module as module,
               entity_count,
               function_count,
               class_count,
               import_count,
               (entity_count + import_count * 0.5) as complexity_score
        ORDER BY complexity_score DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [dict(r) for r in result]


class CodeGraphVisualizer:
    """Visualize the code graph"""

    def __init__(self, query: CodeGraphQuery):
        self.query = query

    def create_interactive_graph(self, output_file: str = "code_graph.html"):
        """Create an interactive graph visualization using pyvis"""
        if not self.query.driver:
            log.warning("No database connection available")
            return

        # Create network
        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
        net.barnes_hut()

        with self.query.driver.session() as session:
            # Get all nodes and relationships
            result = session.run(
                """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT 500
            """
            )

            nodes_added = set()

            for record in result:
                # Add source node
                n = record["n"]
                n_id = f"{n.labels}_{n.get('name', 'unknown')}"

                if n_id not in nodes_added:
                    nodes_added.add(n_id)

                    # Determine node properties based on type
                    if "File" in n.labels:
                        color = "#4CAF50"
                        shape = "box"
                        size = 30
                    elif "Class" in n.labels:
                        color = "#2196F3"
                        shape = "diamond"
                        size = 25
                    elif "Function" in n.labels:
                        color = "#FF9800" if not n.get("is_test", False) else "#9C27B0"
                        shape = "dot"
                        size = 20
                    elif "Module" in n.labels:
                        color = "#F44336"
                        shape = "square"
                        size = 20
                    else:
                        color = "#757575"
                        shape = "dot"
                        size = 15

                    net.add_node(
                        n_id,
                        label=n.get("name", "unknown"),
                        color=color,
                        shape=shape,
                        size=size,
                        title=n.get("docstring", ""),
                    )

                # Add target node and edge if they exist
                if record["m"] and record["r"]:
                    m = record["m"]
                    m_id = f"{m.labels}_{m.get('name', 'unknown')}"

                    if m_id not in nodes_added:
                        nodes_added.add(m_id)

                        # Add target node with appropriate styling
                        if "Module" in m.labels:
                            net.add_node(
                                m_id,
                                label=m.get("name", "unknown"),
                                color="#F44336",
                                shape="square",
                                size=20,
                            )
                        else:
                            net.add_node(m_id, label=m.get("name", "unknown"))

                    # Add edge
                    edge_type = record["r"].type
                    edge_color = {
                        "CONTAINS": "#4CAF50",
                        "IMPORTS": "#F44336",
                        "HAS_METHOD": "#2196F3",
                        "CALLS": "#FF9800",
                    }.get(edge_type, "#757575")

                    net.add_edge(n_id, m_id, title=edge_type, color=edge_color)

        # Set physics options
        net.set_options(
            """
        var options = {
          "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4
          },
          "edges": {
            "smooth": {
              "type": "continuous"
            }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 95,
              "springConstant": 0.04,
              "damping": 0.09
            }
          }
        }
        """
        )

        net.save_graph(output_file)
        log.info(f"Interactive graph saved to {output_file}")

    def create_module_dependency_graph(self, output_file: str = "module_dependencies.png"):
        """Create a module dependency graph"""
        if not self.query.driver:
            log.warning("No database connection available")
            return

        # Create directed graph
        G = nx.DiGraph()

        with self.query.driver.session() as session:
            # Get module dependencies
            result = session.run(
                """
                MATCH (f1:File)-[:IMPORTS]->(m:Module)
                RETURN DISTINCT f1.module as source, m.name as target
            """
            )

            for record in result:
                G.add_edge(record["source"], record["target"])

        # Create visualization
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=2, iterations=50)

        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color="lightblue", node_size=3000, alpha=0.9)

        # Draw edges
        nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, arrowsize=20, alpha=0.6)

        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

        plt.title("Module Dependencies", fontsize=16)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        log.info(f"Module dependency graph saved to {output_file}")

    def create_complexity_heatmap(self, output_file: str = "complexity_heatmap.html"):
        """Create a complexity heatmap using plotly"""
        complexity_data = self.query.get_module_complexity()

        if not complexity_data:
            log.warning("No complexity data available")
            return

        # Prepare data
        modules = [d["module"] for d in complexity_data]
        complexity_scores = [d["complexity_score"] for d in complexity_data]
        entity_counts = [d["entity_count"] for d in complexity_data]

        # Create heatmap
        fig = go.Figure()

        # Add bar chart for complexity
        fig.add_trace(
            go.Bar(
                x=modules, y=complexity_scores, name="Complexity Score", marker_color="indianred"
            )
        )

        # Add scatter for entity count
        fig.add_trace(
            go.Scatter(
                x=modules,
                y=entity_counts,
                mode="markers",
                name="Entity Count",
                marker=dict(size=15, color="lightblue"),
                yaxis="y2",
            )
        )

        # Update layout
        fig.update_layout(
            title="Module Complexity Analysis",
            xaxis_title="Module",
            yaxis_title="Complexity Score",
            yaxis2=dict(title="Entity Count", overlaying="y", side="right"),
            hovermode="x unified",
            template="plotly_dark",
        )

        # Save
        fig.write_html(output_file)
        log.info(f"Complexity heatmap saved to {output_file}")


def main():
    """Example usage of the graph functionality"""
    # Load autodoc cache
    autodoc = SimpleAutodoc()
    autodoc.load("autodoc_cache.json")

    if not autodoc.entities:
        log.warning("No autodoc cache found. Run 'autodoc analyze' first.")
        return

    # Build graph
    log.info("Building code graph...")
    builder = CodeGraphBuilder()
    builder.build_from_autodoc(autodoc)
    builder.close()

    # Query graph
    log.info(
Querying graph...")
    query = CodeGraphQuery()

    # Find entry points
    entry_points = query.find_entry_points()
    if entry_points:
        log.info("\nEntry Points:")
        for ep in entry_points:
            log.info(f"  - {ep['name']} in {ep['file']}")

    # Check test coverage
    coverage = query.find_test_coverage()
    if coverage:
        log.info("\nTest Coverage:")
        log.info(f"  - Total functions: {coverage.get('total_functions', 0)}")
        log.info(f"  - Total tests: {coverage.get('total_tests', 0)}")
        log.info(f"  - Tested modules: {len(coverage.get('tested_modules', []))}")

    # Find patterns
    patterns = query.find_code_patterns()
    if patterns:
        log.info("\nCode Patterns:")
        for pattern_type, instances in patterns.items():
            if instances:
                log.info(f"  {pattern_type}:")
                for instance in instances[:3]:
                    log.info(f"    - {instance['name']}")

    # Create visualizations
    log.info(
Creating visualizations...")
    visualizer = CodeGraphVisualizer(query)
    visualizer.create_interactive_graph()
    visualizer.create_module_dependency_graph()
    visualizer.create_complexity_heatmap()

    query.close()

    log.info("\nDone! Check the generated visualization files.")


if __name__ == "__main__":
    main()
