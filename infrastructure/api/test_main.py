"""
Tests for Autodoc Cloud API

Run with: pytest test_main.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock supabase before importing main
with patch.dict("os.environ", {"SUPABASE_SERVICE_KEY": "test-key"}):
    from main import app, UserInfo, PLAN_LIMITS


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user info."""
    return UserInfo(user_id="user-123", github_id="gh-456", plan="free")


@pytest.fixture
def auth_header():
    """Create mock auth header with a fake JWT."""
    # This is a fake JWT for testing - the API currently doesn't verify signatures
    import jwt
    token = jwt.encode(
        {"sub": "user-123", "github_id": "gh-456", "plan": "free"},
        "secret",  # Doesn't matter since we're not verifying
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_health(self, client):
        """Test root endpoint returns health status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"

    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthDependency:
    """Test authentication dependency."""

    def test_missing_auth_header(self, client):
        """Test request without auth header returns 401."""
        response = client.get("/api/v1/repos")
        assert response.status_code == 422  # FastAPI validation error

    def test_invalid_auth_header(self, client):
        """Test request with invalid auth header returns 401."""
        response = client.get("/api/v1/repos", headers={"Authorization": "Invalid token"})
        assert response.status_code == 401

    def test_malformed_token(self, client):
        """Test request with malformed Bearer token returns 401."""
        response = client.get("/api/v1/repos", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == 401


class TestAnalyzeEndpoint:
    """Test /api/v1/analyze endpoint."""

    @patch("main.get_supabase")
    @patch("main.BackgroundTasks.add_task")
    def test_analyze_new_repo(self, mock_add_task, mock_get_supabase, client, auth_header):
        """Test analyzing a new repository."""
        # Mock Supabase responses
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock select for existing repos (empty - no existing)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        # Mock select for plan limits check
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Mock insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "repo-789"}
        ]

        response = client.post(
            "/api/v1/analyze",
            json={"github_repo": "owner/repo", "is_private": False},
            headers=auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "repo_id" in data

    @patch("main.get_supabase")
    def test_analyze_already_analyzing(self, mock_get_supabase, client, auth_header):
        """Test analyzing a repo that's already being analyzed."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock plan limits check
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Mock existing repo with analyzing status
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "repo-789", "status": "analyzing"}
        ]

        response = client.post(
            "/api/v1/analyze",
            json={"github_repo": "owner/repo"},
            headers=auth_header,
        )

        assert response.status_code == 409
        assert "already being analyzed" in response.json()["detail"]


class TestListReposEndpoint:
    """Test /api/v1/repos endpoint."""

    @patch("main.get_supabase")
    def test_list_empty_repos(self, mock_get_supabase, client, auth_header):
        """Test listing repos when user has none."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/repos", headers=auth_header)

        assert response.status_code == 200
        assert response.json() == []

    @patch("main.get_supabase")
    def test_list_repos_with_data(self, mock_get_supabase, client, auth_header):
        """Test listing repos with existing data."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock repos list
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": "repo-1",
                "github_repo": "owner/repo1",
                "status": "ready",
                "is_private": False,
                "last_analyzed_at": "2024-01-01T00:00:00",
            }
        ]
        # Mock artifacts
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/v1/repos", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["github_repo"] == "owner/repo1"
        assert data[0]["status"] == "ready"


class TestDeleteRepoEndpoint:
    """Test DELETE /api/v1/repos/{repo_id} endpoint."""

    @patch("main.get_supabase")
    def test_delete_own_repo(self, mock_get_supabase, client, auth_header):
        """Test deleting own repository."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"user_id": "user-123"}
        ]

        response = client.delete("/api/v1/repos/repo-123", headers=auth_header)

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @patch("main.get_supabase")
    def test_delete_nonexistent_repo(self, mock_get_supabase, client, auth_header):
        """Test deleting a repo that doesn't exist."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/api/v1/repos/nonexistent", headers=auth_header)

        assert response.status_code == 404

    @patch("main.get_supabase")
    def test_delete_other_users_repo(self, mock_get_supabase, client, auth_header):
        """Test that user cannot delete another user's repo."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"user_id": "other-user"}
        ]

        response = client.delete("/api/v1/repos/repo-123", headers=auth_header)

        assert response.status_code == 403


class TestUsageEndpoint:
    """Test /api/v1/usage endpoint."""

    @patch("main.get_supabase")
    def test_get_usage_no_data(self, mock_get_supabase, client, auth_header):
        """Test getting usage when no tracking data exists."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/v1/usage", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["plan"] == "free"
        assert data["enrichment_used"] == 0
        assert data["enrichment_limit"] == PLAN_LIMITS["free"]["enrichment_monthly"]

    @patch("main.get_supabase")
    def test_get_usage_with_data(self, mock_get_supabase, client, auth_header):
        """Test getting usage with existing tracking data."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"enrichment_count": 50, "analyze_count": 5}
        ]

        response = client.get("/api/v1/usage", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["enrichment_used"] == 50


class TestPlanLimits:
    """Test plan limit enforcement."""

    def test_plan_limits_structure(self):
        """Test that plan limits are correctly defined."""
        assert "free" in PLAN_LIMITS
        assert "pro" in PLAN_LIMITS
        assert "team" in PLAN_LIMITS

        # Free plan should have lowest limits
        assert PLAN_LIMITS["free"]["private_repos"] == 0
        assert PLAN_LIMITS["free"]["public_repos"] == 1

        # Pro should have more
        assert PLAN_LIMITS["pro"]["private_repos"] > PLAN_LIMITS["free"]["private_repos"]
        assert PLAN_LIMITS["pro"]["public_repos"] > PLAN_LIMITS["free"]["public_repos"]

        # Team should have most
        assert PLAN_LIMITS["team"]["private_repos"] > PLAN_LIMITS["pro"]["private_repos"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
