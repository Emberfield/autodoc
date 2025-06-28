"""
Local graph visualization without Neo4j dependency.
Creates visualizations directly from autodoc entities.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

try:
    import matplotlib.pyplot as plt  # noqa: F401
    import networkx as nx  # noqa: F401
    import plotly.graph_objects as go  # noqa: F401
    from pyvis.network import Network

    GRAPH_DEPS_AVAILABLE = True
except ImportError:
    GRAPH_DEPS_AVAILABLE = False


class LocalCodeGraph:
    """Create code graphs directly from autodoc entities without Neo4j"""

    def __init__(self, entities_file: str = "autodoc_cache.json"):
        self.entities_file = entities_file
        self.entities = []
        self.load_entities()

    def load_entities(self):
        """Load entities from autodoc cache"""
        try:
            with open(self.entities_file, "r") as f:
                data = json.load(f)
                self.entities = data.get("entities", [])
            log.info(f"Loaded {len(self.entities)} entities from {self.entities_file}")
        except FileNotFoundError:
            log.error(f"Cache file {self.entities_file} not found. Run 'make analyze' first.")
            self.entities = []

    def create_file_dependency_graph(self, output_file: str = "file_dependencies.html"):
        """Create an interactive file dependency graph"""
        if not GRAPH_DEPS_AVAILABLE:
            log.warning("Graph dependencies not available. Run 'make setup-graph'")
            return

        if not self.entities:
            log.warning("No entities loaded")
            return

        # Group entities by file
        files = defaultdict(lambda: {"functions": [], "classes": []})
        for entity in self.entities:
            file_path = entity["file_path"]
            if entity["type"] == "function":
                files[file_path]["functions"].append(entity["name"])
            elif entity["type"] == "class":
                files[file_path]["classes"].append(entity["name"])

        # Create network
        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
        net.barnes_hut()

        # Add file nodes
        for file_path, content in files.items():
            file_name = Path(file_path).name
            total_entities = len(content["functions"]) + len(content["classes"])

            # Determine node color based on file type
            if "test" in file_path.lower():
                color = "#9C27B0"  # Purple for tests
            elif file_path.endswith(".py"):
                color = "#4CAF50"  # Green for Python files
            else:
                color = "#757575"  # Gray for others

            # Node size based on entity count
            size = min(50, 20 + total_entities * 2)

            tooltip = f"""
            File: {file_path}
            Functions: {len(content["functions"])}
            Classes: {len(content["classes"])}
            Total entities: {total_entities}
            """

            net.add_node(file_path, label=file_name, color=color, size=size, title=tooltip.strip())

        # Add simple directory relationships
        directories = set()
        for file_path in files.keys():
            parent = str(Path(file_path).parent)
            if parent != "." and parent not in directories:
                directories.add(parent)
                net.add_node(
                    parent,
                    label=Path(parent).name or parent,
                    color="#FFC107",  # Yellow for directories
                    size=30,
                    shape="box",
                )

                # Connect files to their directories
                if parent in [str(Path(fp).parent) for fp in files.keys()]:
                    for fp in files.keys():
                        if str(Path(fp).parent) == parent:
                            net.add_edge(parent, fp, color="#FFC107", width=1)

        # Save the graph
        net.save_graph(output_file)
        log.info(f"File dependency graph saved to {output_file}")
        return output_file

    def create_entity_network(self, output_file: str = "entity_network.html"):
        """Create a network of code entities"""
        if not GRAPH_DEPS_AVAILABLE:
            log.warning("Graph dependencies not available. Run 'make setup-graph'")
            return

        if not self.entities:
            log.warning("No entities loaded")
            return

        net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white")
        net.barnes_hut()

        # Add entity nodes
        for entity in self.entities:
            if entity["type"] in ["function", "class"]:
                # Determine node properties
                if entity["type"] == "function":
                    color = "#FF9800"  # Orange for functions
                    if entity["name"].startswith("test_"):
                        color = "#9C27B0"  # Purple for tests
                    shape = "dot"
                elif entity["type"] == "class":
                    color = "#2196F3"  # Blue for classes
                    if entity["name"].startswith("Test"):
                        color = "#673AB7"  # Dark purple for test classes
                    shape = "diamond"

                # Node size based on name length and whether it has docstring
                base_size = 15
                if entity.get("docstring"):
                    base_size += 5
                if entity["name"].startswith("_"):
                    base_size -= 3  # Smaller for private entities

                tooltip = f"""
                Type: {entity["type"]}
                Name: {entity["name"]}
                File: {Path(entity["file_path"]).name}
                Line: {entity["line_number"]}
                """
                if entity.get("docstring"):
                    tooltip += f"\nDescription: {entity['docstring'][:100]}..."

                net.add_node(
                    f"{entity['file_path']}:{entity['name']}",
                    label=entity["name"],
                    color=color,
                    size=base_size,
                    shape=shape,
                    title=tooltip.strip(),
                )

        # Add file groupings (simplified)
        file_groups = defaultdict(list)
        for entity in self.entities:
            if entity["type"] in ["function", "class"]:
                file_groups[entity["file_path"]].append(f"{entity['file_path']}:{entity['name']}")

        # Connect entities within the same file
        for file_path, entity_nodes in file_groups.items():
            if len(entity_nodes) > 1:
                # Create a simple clustering by connecting entities in the same file
                for i, node1 in enumerate(entity_nodes):
                    for node2 in entity_nodes[i + 1 : i + 3]:  # Limit connections to avoid clutter
                        net.add_edge(node1, node2, color="#666666", width=1, alpha=0.3)

        net.save_graph(output_file)
        log.info(f"Entity network saved to {output_file}")
        return output_file

    def create_module_stats(self):
        """Print module statistics"""
        if not self.entities:
            log.warning("No entities loaded")
            return

        # Group by file
        files = defaultdict(lambda: {"functions": 0, "classes": 0, "test_functions": 0})

        for entity in self.entities:
            file_path = entity["file_path"]
            if entity["type"] == "function":
                if entity["name"].startswith("test_"):
                    files[file_path]["test_functions"] += 1
                else:
                    files[file_path]["functions"] += 1
            elif entity["type"] == "class":
                files[file_path]["classes"] += 1

        log.info("\n📊 Module Statistics:")
        log.info("=" * 50)

        # Sort by total entities
        sorted_files = sorted(
            files.items(),
            key=lambda x: x[1]["functions"] + x[1]["classes"] + x[1]["test_functions"],
            reverse=True,
        )

        for file_path, stats in sorted_files[:10]:  # Top 10
            total = stats["functions"] + stats["classes"] + stats["test_functions"]
            file_name = Path(file_path).name
            log.info(
                f"📁 {file_name:25} | Functions: {stats['functions']:3} | Classes: {stats['classes']:2} | Tests: {stats['test_functions']:3} | Total: {total:3}"
            )

        # Summary stats
        total_files = len(files)
        total_functions = sum(f["functions"] for f in files.values())
        total_classes = sum(f["classes"] for f in files.values())
        total_tests = sum(f["test_functions"] for f in files.values())

        log.info("\n📈 Summary:")
        log.info(f"   Total files: {total_files}")
        log.info(f"   Total functions: {total_functions}")
        log.info(f"   Total classes: {total_classes}")
        log.info(f"   Total test functions: {total_tests}")
        log.info(
            f"   Average entities per file: {(total_functions + total_classes + total_tests) / total_files:.1f}"
        )

        return {
            "total_files": total_files,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_tests": total_tests,
        }


def main():
    """Run local graph visualization"""
    log.info("🎨 Creating local code graphs (no Neo4j required)...")

    graph = LocalCodeGraph()

    if not graph.entities:
        log.warning("No entities found. Make sure to run 'make analyze' first.")
        return

    # Create visualizations
    files_created = []

    if GRAPH_DEPS_AVAILABLE:
        try:
            file1 = graph.create_file_dependency_graph()
            if file1:
                files_created.append(file1)

            file2 = graph.create_entity_network()
            if file2:
                files_created.append(file2)
        except Exception as e:
            log.error(f"Error creating visualizations: {e}")
    else:
        log.warning("⚠️  Graph visualization dependencies not available.")
        log.warning("   Run 'make setup-graph' to install them.")

    # Always show stats
    graph.create_module_stats()

    if files_created:
        log.info(f"\n✅ Created {len(files_created)} visualization files:")
        for file in files_created:
            log.info(f"   📄 {file}")
        log.info("\nOpen these HTML files in your browser to view the interactive graphs!")


if __name__ == "__main__":
    main()
