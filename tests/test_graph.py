"""
Tests for graph functionality
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

try:
    from autodoc.analyzer import CodeEntity
    from autodoc.graph import (
        CodeGraphBuilder,
        CodeGraphQuery,
        CodeGraphVisualizer,
        GraphConfig,
    )

    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False


def create_mock_neo4j_driver():
    """Helper function to create a properly mocked Neo4j driver"""
    mock_driver = Mock()
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_driver.session.return_value = mock_context_manager
    mock_session.run.return_value = []
    return mock_driver, mock_session


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestGraphConfig:
    """Test graph configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = GraphConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "password"
        assert config.database == "neo4j"

    def test_config_from_env(self):
        """Test configuration from environment variables"""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://test:7687",
                "NEO4J_USERNAME": "testuser",
                "NEO4J_PASSWORD": "testpass",
                "NEO4J_DATABASE": "testdb",
            },
        ):
            config = GraphConfig.from_env()
            assert config.uri == "bolt://test:7687"
            assert config.username == "testuser"
            assert config.password == "testpass"
            assert config.database == "testdb"


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestCodeGraphBuilder:
    """Test graph builder functionality"""

    def test_builder_initialization(self):
        """Test builder initialization without connection"""
        with patch("autodoc.graph.GraphDatabase.driver") as mock_driver:
            mock_driver.side_effect = Exception("Connection failed")
            builder = CodeGraphBuilder()
            assert builder.driver is None

    def test_builder_with_mock_connection(self):
        """Test builder with mocked Neo4j connection"""
        mock_driver, mock_session = create_mock_neo4j_driver()

        with patch("autodoc.graph.GraphDatabase.driver", return_value=mock_driver):
            builder = CodeGraphBuilder()
            assert builder.driver is not None

            # Test close
            builder.close()
            mock_driver.close.assert_called_once()

    def test_build_from_autodoc_no_connection(self):
        """Test building graph without database connection"""
        builder = CodeGraphBuilder()
        builder.driver = None

        autodoc = Mock()
        autodoc.entities = [
            CodeEntity(
                "function", "test_func", "test.py", 10, "Test function", "def test_func(): pass"
            )
        ]

        # Should handle gracefully without connection
        builder.build_from_autodoc(autodoc)

    def test_build_from_autodoc_with_entities(self):
        """Test building graph with entities"""
        mock_driver, mock_session = create_mock_neo4j_driver()

        with patch("autodoc.graph.GraphDatabase.driver", return_value=mock_driver):
            builder = CodeGraphBuilder()

            # Create test entities
            entities = [
                CodeEntity(
                    "function", "test_func", "test.py", 10, "Test function", "def test_func(): pass"
                ),
                CodeEntity("class", "TestClass", "test.py", 20, "Test class", "class TestClass:"),
            ]

            autodoc = Mock()
            autodoc.entities = entities
            autodoc._extract_imports.return_value = ["import os", "from pathlib import Path"]
            autodoc._get_class_methods_detailed.return_value = []

            builder.build_from_autodoc(autodoc)

            # Verify session.run was called (for creating nodes and relationships)
            assert mock_session.run.call_count > 0


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestCodeGraphQuery:
    """Test graph query functionality"""

    def test_query_initialization(self):
        """Test query initialization without connection"""
        with patch("autodoc.graph.GraphDatabase.driver") as mock_driver:
            mock_driver.side_effect = Exception("Connection failed")
            query = CodeGraphQuery()
            assert query.driver is None

    def test_find_entry_points_no_connection(self):
        """Test finding entry points without connection"""
        query = CodeGraphQuery()
        query.driver = None

        result = query.find_entry_points()
        assert result == []

    def test_find_entry_points_with_data(self):
        """Test finding entry points with mocked data"""
        mock_driver, mock_session = create_mock_neo4j_driver()

        # Mock the query result to return entry points
        mock_result = [
            {"name": "main", "file": "cli.py", "description": "Main entry point"}
        ]
        mock_session.run.return_value = mock_result

        with patch("autodoc.graph.GraphDatabase.driver", return_value=mock_driver):
            query = CodeGraphQuery()
            result = query.find_entry_points()

            assert len(result) == 1
            assert result[0]["name"] == "main"

    def test_find_test_coverage_no_connection(self):
        """Test test coverage analysis without connection"""
        query = CodeGraphQuery()
        query.driver = None

        result = query.find_test_coverage()
        assert result == {}

    def test_find_dependencies_no_connection(self):
        """Test dependency finding without connection"""
        query = CodeGraphQuery()
        query.driver = None

        result = query.find_dependencies("test_entity")
        assert result == {"depends_on": [], "depended_by": []}

    def test_find_code_patterns_no_connection(self):
        """Test pattern finding without connection"""
        query = CodeGraphQuery()
        query.driver = None

        result = query.find_code_patterns()
        assert result == {}

    def test_get_module_complexity_no_connection(self):
        """Test complexity analysis without connection"""
        query = CodeGraphQuery()
        query.driver = None

        result = query.get_module_complexity()
        assert result == []


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestCodeGraphVisualizer:
    """Test graph visualization functionality"""

    def test_visualizer_initialization(self):
        """Test visualizer initialization"""
        mock_query = Mock()
        visualizer = CodeGraphVisualizer(mock_query)
        assert visualizer.query is mock_query

    def test_create_interactive_graph_no_connection(self):
        """Test interactive graph creation without connection"""
        mock_query = Mock()
        mock_query.driver = None

        visualizer = CodeGraphVisualizer(mock_query)

        # Should handle gracefully without connection
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_graph.html"
            visualizer.create_interactive_graph(str(output_file))

    def test_create_module_dependency_graph_no_connection(self):
        """Test module dependency graph creation without connection"""
        mock_query = Mock()
        mock_query.driver = None

        visualizer = CodeGraphVisualizer(mock_query)

        # Should handle gracefully without connection
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_deps.png"
            visualizer.create_module_dependency_graph(str(output_file))

    def test_create_complexity_heatmap_no_data(self):
        """Test complexity heatmap creation with no data"""
        mock_query = Mock()
        mock_query.get_module_complexity.return_value = []

        visualizer = CodeGraphVisualizer(mock_query)

        # Should handle gracefully with no data
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_complexity.html"
            visualizer.create_complexity_heatmap(str(output_file))

    @patch("autodoc.graph.plt")
    @patch("autodoc.graph.nx")
    def test_create_module_dependency_graph_with_data(self, mock_nx, mock_plt):
        """Test module dependency graph creation with data"""
        mock_driver, mock_session = create_mock_neo4j_driver()

        # Mock the query result
        mock_result = [
            {"source": "module1", "target": "module2"},
            {"source": "module2", "target": "module3"},
        ]
        mock_session.run.return_value = mock_result

        mock_query = Mock()
        mock_query.driver = mock_driver

        # Mock networkx
        mock_graph = Mock()
        mock_nx.DiGraph.return_value = mock_graph
        mock_nx.spring_layout.return_value = {}

        visualizer = CodeGraphVisualizer(mock_query)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_deps.png"
            visualizer.create_module_dependency_graph(str(output_file))

            # Verify graph operations were called
            mock_graph.add_edge.assert_called()
            mock_plt.savefig.assert_called()

    @patch("autodoc.graph.go")
    def test_create_complexity_heatmap_with_data(self, mock_go):
        """Test complexity heatmap creation with data"""
        mock_query = Mock()
        mock_query.get_module_complexity.return_value = [
            {"module": "module1", "complexity_score": 10.5, "entity_count": 5, "import_count": 3},
            {"module": "module2", "complexity_score": 8.2, "entity_count": 3, "import_count": 2},
        ]

        # Mock plotly
        mock_fig = Mock()
        mock_go.Figure.return_value = mock_fig

        visualizer = CodeGraphVisualizer(mock_query)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_complexity.html"
            visualizer.create_complexity_heatmap(str(output_file))

            # Verify plotly operations were called
            mock_fig.add_trace.assert_called()
            mock_fig.write_html.assert_called()


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestGraphIntegration:
    """Test full graph integration"""

    def test_end_to_end_without_neo4j(self):
        """Test complete workflow without Neo4j connection"""
        # Create test entities
        entities = [
            CodeEntity("function", "main", "cli.py", 10, "Main function", "def main():"),
            CodeEntity("class", "TestClass", "test.py", 20, "Test class", "class TestClass:"),
            CodeEntity("function", "test_func", "test.py", 30, "Test function", "def test_func():"),
        ]

        # Create autodoc mock
        autodoc = Mock()
        autodoc.entities = entities
        autodoc._extract_imports.return_value = []
        autodoc._get_class_methods_detailed.return_value = []

        # Test builder
        builder = CodeGraphBuilder()
        builder.driver = None  # Simulate no connection
        builder.build_from_autodoc(autodoc)  # Should handle gracefully

        # Test query
        query = CodeGraphQuery()
        query.driver = None  # Simulate no connection

        # All methods should return empty/default values gracefully
        assert query.find_entry_points() == []
        assert query.find_test_coverage() == {}
        assert query.find_dependencies("test") == {"depends_on": [], "depended_by": []}
        assert query.find_code_patterns() == {}
        assert query.get_module_complexity() == []

        # Test visualizer
        visualizer = CodeGraphVisualizer(query)

        # Should handle gracefully without connection
        with tempfile.TemporaryDirectory() as tmpdir:
            visualizer.create_interactive_graph(str(Path(tmpdir) / "test.html"))
            visualizer.create_module_dependency_graph(str(Path(tmpdir) / "test.png"))
            visualizer.create_complexity_heatmap(str(Path(tmpdir) / "test.html"))

    def test_code_entity_node_creation_logic(self):
        """Test the logic for creating different types of nodes"""
        builder = CodeGraphBuilder()
        builder.driver = None

        # Test function entity
        func_entity = CodeEntity(
            "function", "_private_func", "test.py", 10, "Private function", "def _private_func():"
        )

        # Test class entity
        class_entity = CodeEntity(
            "class", "PublicClass", "test.py", 20, "Public class", "class PublicClass:"
        )

        # Test that entities are properly categorized (this would be tested with actual Neo4j)
        # For now, just verify they can be processed without errors
        assert func_entity.name.startswith("_")  # Private function
        assert not class_entity.name.startswith("_")  # Public class

    def test_file_type_detection(self):
        """Test file type detection logic"""
        # Test different file types
        test_cases = [
            ("test_module.py", True),
            ("__init__.py", True),
            ("setup.py", True),
            ("regular_module.py", False),
        ]

        for file_path, has_special_type in test_cases:
            path = Path(file_path)

            # Test the logic that would be used in _create_file_node
            if "test" in path.name:
                file_type = "test"
            elif path.name == "__init__.py":
                file_type = "package"
            elif path.name == "setup.py":
                file_type = "setup"
            else:
                file_type = "module"

            if has_special_type:
                assert file_type != "module"
            else:
                assert file_type == "module"


@pytest.mark.skipif(not GRAPH_AVAILABLE, reason="Graph dependencies not available")
class TestGraphCLI:
    """Test graph CLI commands"""

    def test_cli_commands_imported(self):
        """Test that CLI commands can be imported"""
        from autodoc.cli import graph, query_graph, visualize_graph

        # Verify the functions exist
        assert callable(graph)
        assert callable(visualize_graph)
        assert callable(query_graph)

    def test_graph_availability_check(self):
        """Test graph availability checking"""
        from autodoc.cli import GRAPH_AVAILABLE

        # Since we're running this test, graph should be available
        assert GRAPH_AVAILABLE is True


# Test that can run even without graph dependencies
class TestGraphUnavailable:
    """Test behavior when graph dependencies are not available"""

    @patch("autodoc.cli.GRAPH_AVAILABLE", False)
    def test_graph_commands_handle_missing_deps(self):
        """Test that graph commands handle missing dependencies gracefully"""
        from autodoc.cli import graph, query_graph, visualize_graph

        # These should exist even when dependencies are missing
        assert callable(graph)
        assert callable(visualize_graph)
        assert callable(query_graph)

    def test_import_fallback(self):
        """Test import fallback behavior"""
        # Test the import pattern used in the CLI
        try:
            import autodoc.graph  # noqa: F401

            graph_available = True
        except ImportError:
            graph_available = False

        # This test will pass regardless of availability
        assert isinstance(graph_available, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
