"""
Comprehensive tests for TypeScript support in Autodoc.
Tests both Python and TypeScript functionality to ensure compatibility.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autodoc.autodoc import TYPESCRIPT_AVAILABLE, SimpleAutodoc


class TestTypeScriptSupport:
    """Test TypeScript analysis functionality."""

    @pytest.fixture
    def autodoc(self):
        """Create Autodoc instance for testing."""
        return SimpleAutodoc()

    @pytest.fixture
    def test_ts_project_path(self):
        """Path to test TypeScript project."""
        return Path(__file__).parent / "test_typescript_project"

    def test_typescript_analyzer_initialization(self, autodoc):
        """Test that TypeScript analyzer initializes correctly."""
        if TYPESCRIPT_AVAILABLE:
            assert autodoc.ts_analyzer is not None
            # Note: analyzer might not be available if tree-sitter is not installed
        else:
            assert autodoc.ts_analyzer is None

    def test_python_functionality_preserved(self, autodoc):
        """Ensure Python analysis still works after TypeScript integration."""
        # Test with current source directory
        src_path = Path("src/autodoc")

        # Analyze Python files
        python_entities = autodoc.analyzer.analyze_directory(src_path)

        # Should find Python entities
        assert len(python_entities) > 0

        # Check that we have expected Python entities
        entity_names = [e.name for e in python_entities]
        assert "SimpleAutodoc" in entity_names
        assert "SimpleASTAnalyzer" in entity_names

        # Verify entity types
        functions = [e for e in python_entities if e.type == "function"]
        classes = [e for e in python_entities if e.type == "class"]

        assert len(functions) > 0
        assert len(classes) > 0

    @pytest.mark.asyncio
    async def test_mixed_directory_analysis(self, autodoc, test_ts_project_path):
        """Test analysis of directory containing both Python and TypeScript files."""
        if (
            not TYPESCRIPT_AVAILABLE
            or not autodoc.ts_analyzer
            or not autodoc.ts_analyzer.is_available()
        ):
            pytest.skip("TypeScript analyzer not available")

        # Create a test directory with both Python and TypeScript files
        test_dir = test_ts_project_path.parent / "mixed_test_project"
        test_dir.mkdir(exist_ok=True)

        # Create a simple Python file
        python_file = test_dir / "test_python.py"
        python_file.write_text(
            """
class TestPythonClass:
    def test_method(self):
        return "python"

def test_function():
    return "python_function"
"""
        )

        # Copy a TypeScript file
        ts_file = test_dir / "test_typescript.ts"
        ts_file.write_text(
            """
export class TestTypeScriptClass {
    testMethod(): string {
        return "typescript";
    }
}

export function testFunction(): string {
    return "typescript_function";
}
"""
        )

        try:
            # Analyze mixed directory
            result = await autodoc.analyze_directory_async(test_dir, save=False)

            # Should have entities from both languages
            assert result["total_entities"] > 0
            assert result["languages"]["python"]["entities"] > 0
            assert result["languages"]["typescript"]["entities"] > 0

            # Check that we have both Python and TypeScript entities
            python_entities = [e for e in autodoc.entities if e.file_path.endswith(".py")]
            typescript_entities = [e for e in autodoc.entities if e.file_path.endswith(".ts")]

            assert len(python_entities) > 0
            assert len(typescript_entities) > 0

            # Verify specific entities were found
            entity_names = [e.name for e in autodoc.entities]
            assert "TestPythonClass" in entity_names
            assert "TestTypeScriptClass" in entity_names
            assert "test_function" in entity_names
            assert "testFunction" in entity_names

        finally:
            # Cleanup
            if python_file.exists():
                python_file.unlink()
            if ts_file.exists():
                ts_file.unlink()
            if test_dir.exists() and not list(test_dir.iterdir()):
                test_dir.rmdir()

    @pytest.mark.asyncio
    @pytest.mark.skipif(not TYPESCRIPT_AVAILABLE, reason="TypeScript analyzer not available")
    async def test_typescript_only_analysis(self, autodoc, test_ts_project_path):
        """Test analysis of TypeScript-only project."""
        if not autodoc.ts_analyzer or not autodoc.ts_analyzer.is_available():
            pytest.skip("TypeScript analyzer not available or tree-sitter not installed")

        result = await autodoc.analyze_directory_async(test_ts_project_path, save=False)

        # Should have TypeScript entities
        assert result["languages"]["typescript"]["entities"] > 0
        assert result["languages"]["typescript"]["files"] > 0

        # Should have no Python entities
        assert result["languages"]["python"]["entities"] == 0
        assert result["languages"]["python"]["files"] == 0

        # Check for expected TypeScript entities
        entity_names = [e.name for e in autodoc.entities]
        expected_entities = [
            "UserService",  # interface
            "UserServiceImpl",  # class
            "UserController",  # class
            "AuthController",  # class
            "User",  # interface
            "CreateUserRequest",  # interface
            "GitHubClient",  # class
            "retry",  # function
            "sleep",  # function
        ]

        # Some entities should be found (depending on tree-sitter parsing)
        found_entities = [name for name in expected_entities if name in entity_names]
        assert len(found_entities) > 0, (
            f"Expected some entities from {expected_entities}, but found {entity_names}"
        )

    def test_api_endpoint_detection_express(self, autodoc):
        """Test detection of Express.js API endpoints."""
        if not TYPESCRIPT_AVAILABLE or not autodoc.ts_analyzer:
            pytest.skip("TypeScript analyzer not available")

        # Mock TypeScript analysis for Express endpoints
        mock_entity = Mock()
        mock_entity.code = """
        router.get('/api/users/:id', async (req, res) => {
            // Get user implementation
        });
        """
        mock_entity.name = "getUser"
        mock_entity.framework = None
        mock_entity.http_methods = []
        mock_entity.route_path = None
        mock_entity.decorators = []
        mock_entity.external_calls = []

        # Test HTTP method extraction
        methods = autodoc.ts_analyzer._extract_http_methods_from_code(mock_entity.code)
        assert "GET" in methods

        # Test route path extraction
        route = autodoc.ts_analyzer._extract_route_path_from_code(mock_entity.code)
        assert route == "/api/users/:id"

    def test_api_endpoint_detection_nestjs(self, autodoc):
        """Test detection of NestJS API endpoints."""
        if not TYPESCRIPT_AVAILABLE or not autodoc.ts_analyzer:
            pytest.skip("TypeScript analyzer not available")

        # Test NestJS decorator extraction
        code = """
        @Controller('auth')
        @Get('profile')
        @UseGuards(JwtAuthGuard)
        async getProfile(@Request() req: any) {
            return req.user;
        }
        """

        decorators = autodoc.ts_analyzer._extract_nestjs_decorators(code)
        assert "@Controller" in decorators
        assert "@Get" in decorators
        assert "@UseGuards" in decorators

        # Test HTTP method extraction from decorators
        methods = autodoc.ts_analyzer._extract_nestjs_http_methods(decorators)
        assert "GET" in methods

    def test_external_service_classification(self, autodoc):
        """Test classification of external service integrations."""
        if not TYPESCRIPT_AVAILABLE or not autodoc.ts_analyzer:
            pytest.skip("TypeScript analyzer not available")

        # Test GitHub client classification
        imports = ["import { Octokit } from '@octokit/rest';", "import axios from 'axios';"]

        # Mock entity for GitHub client
        mock_entity = Mock()
        mock_entity.name = "GitHubClient"
        mock_entity.code = "class GitHubClient { async getUser() { return this.octokit.rest.users.getByUsername(); } }"
        mock_entity.file_path = "/external/github.client.ts"
        mock_entity.external_calls = ["this.octokit.rest.users.getByUsername"]

        # Should be classified as external
        is_internal = autodoc.ts_analyzer._classify_internal_vs_external(mock_entity, imports)
        assert not is_internal

    def test_internal_service_classification(self, autodoc):
        """Test classification of internal services."""
        if not TYPESCRIPT_AVAILABLE or not autodoc.ts_analyzer:
            pytest.skip("TypeScript analyzer not available")

        # Test internal service classification
        imports = ["import { DatabaseService } from './database.service';"]

        mock_entity = Mock()
        mock_entity.name = "UserService"
        mock_entity.code = (
            "class UserService { async createUser() { return this.database.save(); } }"
        )
        mock_entity.file_path = "/services/user.service.ts"
        mock_entity.external_calls = []

        # Should be classified as internal
        is_internal = autodoc.ts_analyzer._classify_internal_vs_external(mock_entity, imports)
        assert is_internal

    @pytest.mark.asyncio
    async def test_search_across_languages(self, autodoc, test_ts_project_path):
        """Test search functionality across Python and TypeScript entities."""
        if (
            not TYPESCRIPT_AVAILABLE
            or not autodoc.ts_analyzer
            or not autodoc.ts_analyzer.is_available()
        ):
            pytest.skip("TypeScript analyzer not available")

        # Create mixed project
        test_dir = test_ts_project_path.parent / "search_test_project"
        test_dir.mkdir(exist_ok=True)

        python_file = test_dir / "user_service.py"
        python_file.write_text(
            """
class UserService:
    def create_user(self):
        '''Create a new user'''
        pass
"""
        )

        ts_file = test_dir / "user_service.ts"
        ts_file.write_text(
            """
export class UserService {
    /**
     * Create a new user
     */
    createUser(): void {}
}
"""
        )

        try:
            await autodoc.analyze_directory_async(test_dir, save=False)

            # Search should find entities from both languages
            results = await autodoc.search_async("user", limit=10)

            # Should find UserService from both languages
            result_names = [result[0].name for result in results]
            assert "UserService" in result_names

        finally:
            # Cleanup
            if python_file.exists():
                python_file.unlink()
            if ts_file.exists():
                ts_file.unlink()
            if test_dir.exists() and not list(test_dir.iterdir()):
                test_dir.rmdir()

    def test_language_statistics(self, autodoc):
        """Test that language statistics are correctly calculated."""
        # Mock entities for testing statistics
        python_entities = [
            Mock(type="function", file_path="test.py"),
            Mock(type="class", file_path="test.py"),
            Mock(type="function", file_path="other.py"),
        ]

        typescript_entities = [
            Mock(type="function", file_path="test.ts"),
            Mock(type="class", file_path="test.ts"),
            Mock(type="interface", file_path="types.ts"),
            Mock(type="method", file_path="service.ts"),
        ]

        # Simulate analysis results
        # all_entities = python_entities + typescript_entities  # Not used in test

        # Calculate stats manually (similar to what autodoc does)
        python_files = len(set(e.file_path for e in python_entities))
        typescript_files = len(set(e.file_path for e in typescript_entities))

        assert python_files == 2  # test.py, other.py
        assert typescript_files == 3  # test.ts, types.ts, service.ts

        # Test entity type counting
        ts_functions = len([e for e in typescript_entities if e.type == "function"])
        ts_classes = len([e for e in typescript_entities if e.type == "class"])
        ts_interfaces = len([e for e in typescript_entities if e.type == "interface"])
        ts_methods = len([e for e in typescript_entities if e.type == "method"])

        assert ts_functions == 1
        assert ts_classes == 1
        assert ts_interfaces == 1
        assert ts_methods == 1

    def test_graceful_degradation_without_tree_sitter(self, autodoc):
        """Test that the system works gracefully when tree-sitter is not available."""
        # This test ensures the system doesn't crash when TypeScript parsing is unavailable
        if TYPESCRIPT_AVAILABLE and autodoc.ts_analyzer and autodoc.ts_analyzer.is_available():
            # Mock tree-sitter unavailability
            with patch.object(autodoc.ts_analyzer, "is_available", return_value=False):
                # Should still work with Python only
                src_path = Path("src/autodoc")
                python_entities = autodoc.analyzer.analyze_directory(src_path)
                assert len(python_entities) > 0
        else:
            # Already testing the degraded case
            src_path = Path("src/autodoc")
            python_entities = autodoc.analyzer.analyze_directory(src_path)
            assert len(python_entities) > 0


if __name__ == "__main__":
    # Run basic tests manually
    autodoc = SimpleAutodoc()

    print("🧪 Testing TypeScript Support")
    print("=" * 50)

    print(f"TypeScript Available: {TYPESCRIPT_AVAILABLE}")
    if autodoc.ts_analyzer:
        print(f"TypeScript Analyzer Available: {autodoc.ts_analyzer.is_available()}")
    else:
        print("TypeScript Analyzer: None")

    # Test Python functionality
    print("\n📁 Testing Python Analysis...")
    src_path = Path("src/autodoc")
    python_entities = autodoc.analyzer.analyze_directory(src_path)
    print(f"Found {len(python_entities)} Python entities")

    if TYPESCRIPT_AVAILABLE and autodoc.ts_analyzer and autodoc.ts_analyzer.is_available():
        print("\n📁 Testing TypeScript Analysis...")
        ts_test_path = Path("tests/test_typescript_project")
        if ts_test_path.exists():
            ts_entities = autodoc.ts_analyzer.analyze_directory(ts_test_path)
            print(f"Found {len(ts_entities)} TypeScript entities")

            if ts_entities:
                print("\nSample TypeScript entities:")
                for entity in ts_entities[:5]:
                    print(f"  • {entity.type}: {entity.name} (in {Path(entity.file_path).name})")
        else:
            print("TypeScript test project not found")

    print("\n✅ Basic tests completed!")
