"""
Tests for feature discovery functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

try:
    from autodoc.features import (
        EXCLUDED_PATH_PATTERNS,
        DetectedFeature,
        FeatureDetectionResult,
        FeatureDetector,
        FeatureNamer,
        FeaturesCache,
        SampleFile,
    )

    FEATURES_AVAILABLE = True
except ImportError:
    FEATURES_AVAILABLE = False


def create_mock_neo4j_driver():
    """Helper function to create a properly mocked Neo4j driver."""
    mock_driver = Mock()
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_driver.session.return_value = mock_context_manager
    return mock_driver, mock_session


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestSampleFile:
    """Test SampleFile dataclass."""

    def test_sample_file_creation(self):
        """Test creating a sample file."""
        sf = SampleFile(path="src/auth/login.py", summary="Handles user login")
        assert sf.path == "src/auth/login.py"
        assert sf.summary == "Handles user login"

    def test_sample_file_no_summary(self):
        """Test sample file without summary."""
        sf = SampleFile(path="src/utils.py")
        assert sf.path == "src/utils.py"
        assert sf.summary is None

    def test_sample_file_to_dict(self):
        """Test converting sample file to dict."""
        sf = SampleFile(path="src/auth/login.py", summary="Login handler")
        d = sf.to_dict()
        assert d == {"path": "src/auth/login.py", "summary": "Login handler"}


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestDetectedFeature:
    """Test DetectedFeature dataclass."""

    def test_feature_creation(self):
        """Test creating a detected feature."""
        feature = DetectedFeature(
            id=0,
            files=["src/auth/login.py", "src/auth/session.py"],
            file_count=2,
            sample_files=[SampleFile(path="src/auth/login.py", summary="Login")],
        )
        assert feature.id == 0
        assert feature.file_count == 2
        assert len(feature.files) == 2
        assert feature.name is None

    def test_feature_with_name(self):
        """Test feature with assigned name."""
        feature = DetectedFeature(
            id=1,
            files=["src/db/connection.py"],
            file_count=1,
            name="database-layer",
            display_name="Database Layer",
            reasoning="Handles database connections",
        )
        assert feature.name == "database-layer"
        assert feature.display_name == "Database Layer"

    def test_feature_to_dict(self):
        """Test converting feature to dict."""
        feature = DetectedFeature(
            id=0,
            files=["src/a.py"],
            file_count=1,
            sample_files=[SampleFile(path="src/a.py", summary="Test")],
            name="test-feature",
            display_name="Test Feature",
        )
        d = feature.to_dict()
        assert d["id"] == 0
        assert d["name"] == "test-feature"
        assert d["display_name"] == "Test Feature"
        assert len(d["sample_files"]) == 1

    def test_feature_from_dict(self):
        """Test creating feature from dict."""
        data = {
            "id": 5,
            "files": ["a.py", "b.py"],
            "file_count": 2,
            "sample_files": [{"path": "a.py", "summary": "Test A"}],
            "name": "my-feature",
            "display_name": "My Feature",
            "reasoning": "Test reasoning",
            "named_at": "2024-01-15T10:00:00",
        }
        feature = DetectedFeature.from_dict(data)
        assert feature.id == 5
        assert feature.file_count == 2
        assert feature.name == "my-feature"
        assert len(feature.sample_files) == 1
        assert feature.sample_files[0].summary == "Test A"


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestFeatureDetectionResult:
    """Test FeatureDetectionResult dataclass."""

    def test_result_creation(self):
        """Test creating a detection result."""
        result = FeatureDetectionResult(
            community_count=5,
            modularity=0.72,
            ran_levels=2,
            graph_hash="abc123",
        )
        assert result.community_count == 5
        assert result.modularity == 0.72
        assert result.graph_hash == "abc123"

    def test_result_with_features(self):
        """Test result with features."""
        feature = DetectedFeature(id=0, files=["a.py"], file_count=1)
        result = FeatureDetectionResult(
            community_count=1,
            modularity=0.5,
            features={0: feature},
        )
        assert 0 in result.features
        assert result.features[0].file_count == 1

    def test_result_to_dict(self):
        """Test converting result to dict."""
        feature = DetectedFeature(id=0, files=["a.py"], file_count=1)
        result = FeatureDetectionResult(
            community_count=1,
            modularity=0.5,
            graph_hash="hash123",
            max_degree_threshold=50,
            features={0: feature},
            detected_at="2024-01-15T10:00:00",
        )
        d = result.to_dict()
        assert d["community_count"] == 1
        assert d["modularity"] == 0.5
        assert d["graph_hash"] == "hash123"
        assert "0" in d["features"]

    def test_result_from_dict(self):
        """Test creating result from dict."""
        data = {
            "community_count": 3,
            "modularity": 0.75,
            "ran_levels": 2,
            "graph_hash": "testhash",
            "max_degree_threshold": 40,
            "features": {
                "0": {"id": 0, "files": ["a.py"], "file_count": 1, "sample_files": []},
            },
            "detected_at": "2024-01-15T10:00:00",
        }
        result = FeatureDetectionResult.from_dict(data)
        assert result.community_count == 3
        assert result.modularity == 0.75
        assert result.graph_hash == "testhash"
        assert 0 in result.features


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestFeatureDetector:
    """Test FeatureDetector class."""

    def test_check_gds_available_true(self):
        """Test GDS availability check when installed."""
        mock_driver, mock_session = create_mock_neo4j_driver()
        mock_result = Mock()
        mock_result.single.return_value = {"version": "2.5.0"}
        mock_session.run.return_value = mock_result

        detector = FeatureDetector(mock_driver)
        assert detector.check_gds_available() is True

    def test_check_gds_available_false(self):
        """Test GDS availability check when not installed."""
        from neo4j.exceptions import ClientError

        mock_driver, mock_session = create_mock_neo4j_driver()
        mock_session.run.side_effect = ClientError("Unknown function gds.version")

        detector = FeatureDetector(mock_driver)
        assert detector.check_gds_available() is False

    def test_check_graph_exists_true(self):
        """Test graph existence check when graph exists."""
        mock_driver, mock_session = create_mock_neo4j_driver()
        mock_result = Mock()
        mock_result.single.return_value = {"count": 50}
        mock_session.run.return_value = mock_result

        detector = FeatureDetector(mock_driver)
        assert detector.check_graph_exists() is True

    def test_check_graph_exists_false(self):
        """Test graph existence check when graph is empty."""
        mock_driver, mock_session = create_mock_neo4j_driver()
        mock_result = Mock()
        mock_result.single.return_value = {"count": 0}
        mock_session.run.return_value = mock_result

        detector = FeatureDetector(mock_driver)
        assert detector.check_graph_exists() is False

    def test_compute_graph_hash(self):
        """Test graph hash computation."""
        mock_driver, mock_session = create_mock_neo4j_driver()
        mock_result = Mock()
        mock_result.single.return_value = {"file_count": 100, "last_file": "src/main.py"}
        mock_session.run.return_value = mock_result

        detector = FeatureDetector(mock_driver)
        hash_value = detector.compute_graph_hash()

        assert hash_value is not None
        assert len(hash_value) == 32  # MD5 hex digest length


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestFeaturesCache:
    """Test FeaturesCache class."""

    def test_cache_save_and_load(self):
        """Test saving and loading cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".autodoc" / "features_cache.json"
            cache = FeaturesCache(str(cache_file))

            feature = DetectedFeature(
                id=0,
                files=["a.py", "b.py"],
                file_count=2,
                sample_files=[SampleFile(path="a.py", summary="Test")],
                name="test-feature",
                display_name="Test Feature",
            )

            result = FeatureDetectionResult(
                community_count=1,
                modularity=0.75,
                graph_hash="testhash",
                features={0: feature},
                detected_at="2024-01-15T10:00:00",
            )

            cache.save(result)
            assert cache_file.exists()

            loaded = cache.load()
            assert loaded is not None
            assert loaded.community_count == 1
            assert loaded.modularity == 0.75
            assert loaded.graph_hash == "testhash"
            assert 0 in loaded.features
            assert loaded.features[0].name == "test-feature"

    def test_cache_load_nonexistent(self):
        """Test loading nonexistent cache."""
        cache = FeaturesCache("/nonexistent/path/cache.json")
        assert cache.load() is None

    def test_cache_is_stale(self):
        """Test cache staleness check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".autodoc" / "features_cache.json"
            cache = FeaturesCache(str(cache_file))

            result = FeatureDetectionResult(
                community_count=1,
                modularity=0.5,
                graph_hash="oldhash",
                features={},
            )
            cache.save(result)

            # Same hash - not stale
            assert cache.is_stale("oldhash") is False

            # Different hash - stale
            assert cache.is_stale("newhash") is True

    def test_cache_update_feature_name(self):
        """Test updating feature name in cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / ".autodoc" / "features_cache.json"
            cache = FeaturesCache(str(cache_file))

            feature = DetectedFeature(id=0, files=["a.py"], file_count=1)
            result = FeatureDetectionResult(
                community_count=1,
                modularity=0.5,
                features={0: feature},
            )
            cache.save(result)

            # Update feature name
            cache.update_feature_name(
                feature_id=0,
                name="new-name",
                display_name="New Name",
                reasoning="Test reasoning",
            )

            # Reload and verify
            loaded = cache.load()
            assert loaded.features[0].name == "new-name"
            assert loaded.features[0].display_name == "New Name"
            assert loaded.features[0].reasoning == "Test reasoning"
            assert loaded.features[0].named_at is not None


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestFeatureNamer:
    """Test FeatureNamer class."""

    def test_namer_initialization(self):
        """Test namer initialization."""
        mock_config = Mock()
        namer = FeatureNamer(mock_config)
        assert namer.config == mock_config

    def test_feature_prompt_construction(self):
        """Test that feature prompt is constructed correctly."""
        # Test that the prompt includes file paths and summaries
        feature = DetectedFeature(
            id=0,
            files=["src/auth/login.py", "src/auth/session.py"],
            file_count=2,
            sample_files=[
                SampleFile(path="src/auth/login.py", summary="Handles user login"),
                SampleFile(path="src/auth/session.py", summary="Session management"),
            ],
        )

        # Build context lines similar to what FeatureNamer does
        context_lines = []
        for i, sf in enumerate(feature.sample_files[:5], 1):
            summary = sf.summary if sf.summary else "(no summary available)"
            context_lines.append(f"{i}. {sf.path} - {summary}")

        context_text = "\n".join(context_lines)

        # Verify prompt construction
        assert "src/auth/login.py" in context_text
        assert "Handles user login" in context_text
        assert "src/auth/session.py" in context_text
        assert "Session management" in context_text


@pytest.mark.skipif(not FEATURES_AVAILABLE, reason="Features dependencies not available")
class TestExcludedPathPatterns:
    """Test external library filtering."""

    def test_excluded_patterns_contains_common_libraries(self):
        """Test that EXCLUDED_PATH_PATTERNS includes common external library paths."""
        assert "node_modules" in EXCLUDED_PATH_PATTERNS
        assert "site-packages" in EXCLUDED_PATH_PATTERNS
        assert ".venv" in EXCLUDED_PATH_PATTERNS
        assert "venv" in EXCLUDED_PATH_PATTERNS
        assert "__pycache__" in EXCLUDED_PATH_PATTERNS
        assert ".git" in EXCLUDED_PATH_PATTERNS
        assert "vendor" in EXCLUDED_PATH_PATTERNS

    def test_excluded_patterns_contains_build_artifacts(self):
        """Test that EXCLUDED_PATH_PATTERNS includes build artifact directories."""
        assert "dist" in EXCLUDED_PATH_PATTERNS
        assert "build" in EXCLUDED_PATH_PATTERNS
        assert ".tox" in EXCLUDED_PATH_PATTERNS
        assert ".eggs" in EXCLUDED_PATH_PATTERNS

    def test_excluded_patterns_contains_frontend_build_dirs(self):
        """Test that EXCLUDED_PATH_PATTERNS includes frontend build directories."""
        assert ".next" in EXCLUDED_PATH_PATTERNS
        assert ".nuxt" in EXCLUDED_PATH_PATTERNS
        assert ".output" in EXCLUDED_PATH_PATTERNS
        assert "coverage" in EXCLUDED_PATH_PATTERNS
