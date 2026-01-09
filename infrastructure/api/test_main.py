"""
Tests for Autodoc Cloud API

Run with: pytest test_main.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock environment before importing main
# Disable JWT verification for tests so we can use simple test tokens
with patch.dict("os.environ", {
    "SUPABASE_SERVICE_KEY": "test-key",
    "JWT_VERIFY_ENABLED": "false",  # Disable JWKS verification for tests
}):
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


class TestGitHubAppEndpoints:
    """Test GitHub App integration endpoints."""

    def test_install_redirect_requires_auth(self, client):
        """Test install redirect requires authentication."""
        response = client.get("/api/github/install")
        assert response.status_code == 422  # Missing auth header

    @patch("main.GITHUB_APP_CLIENT_ID", "test-client-id")
    def test_install_redirect_not_configured(self, client, auth_header):
        """Test install redirect fails when GitHub App not configured."""
        with patch("main.GITHUB_APP_CLIENT_ID", None):
            response = client.get("/api/github/install", headers=auth_header)
            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]

    @patch("main.GITHUB_APP_CLIENT_ID", "test-client-id")
    def test_install_redirect_configured(self, client, auth_header):
        """Test install redirect works when configured and includes state."""
        response = client.get("/api/github/install", headers=auth_header, follow_redirects=False)
        assert response.status_code == 307  # Redirect
        location = response.headers.get("location", "")
        assert "github.com/apps" in location
        assert "state=" in location  # CSRF state must be included

    def test_github_callback_invalid_params(self, client):
        """Test callback fails with invalid parameters."""
        response = client.get("/api/github/callback")
        assert response.status_code == 400
        assert "Invalid callback" in response.json()["detail"]

    def test_github_callback_missing_state(self, client):
        """Test callback fails without CSRF state parameter."""
        response = client.get("/api/github/callback?installation_id=12345&setup_action=install")
        assert response.status_code == 400
        assert "Missing state" in response.json()["detail"]

    def test_github_callback_invalid_state(self, client):
        """Test callback fails with invalid CSRF state."""
        response = client.get(
            "/api/github/callback?installation_id=12345&setup_action=install&state=invalid-state"
        )
        assert response.status_code == 400
        assert "Invalid or expired state" in response.json()["detail"]

    @patch("main.get_supabase")
    def test_list_installations_empty(self, mock_get_supabase, client, auth_header):
        """Test listing GitHub installations when user has none."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/github/installations", headers=auth_header)

        assert response.status_code == 200
        assert response.json() == []

    @patch("main.get_supabase")
    def test_list_installations_with_data(self, mock_get_supabase, client, auth_header):
        """Test listing GitHub installations with existing data."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "installation_id": 12345,
                "account_login": "testuser",
                "account_type": "User",
            }
        ]

        response = client.get("/api/github/installations", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["installation_id"] == 12345
        assert data[0]["account_login"] == "testuser"


class TestInstallationHijacking:
    """Test installation hijacking prevention."""

    @patch("main.get_supabase")
    @patch("main.generate_github_app_jwt")
    @patch("httpx.AsyncClient.get")
    def test_link_installation_own_account(
        self, mock_http_get, mock_jwt, mock_get_supabase, client, auth_header
    ):
        """Test user can link installation for their own GitHub account."""
        import asyncio
        from unittest.mock import AsyncMock

        mock_jwt.return_value = "mock-jwt"
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock GitHub API response with user's own account (github_id matches)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "account": {
                "id": "gh-456",  # Matches auth_header github_id
                "login": "testuser",
                "type": "User",
            }
        }

        # Create async mock for httpx
        async def mock_get(*args, **kwargs):
            return mock_response

        mock_http_get.side_effect = mock_get

        response = client.post(
            "/api/github/link-installation?installation_id=12345",
            headers=auth_header,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "linked"

    @patch("main.get_supabase")
    @patch("main.generate_github_app_jwt")
    @patch("httpx.AsyncClient.get")
    def test_link_installation_other_user_blocked(
        self, mock_http_get, mock_jwt, mock_get_supabase, client, auth_header
    ):
        """Test user cannot hijack installation for another user's account."""
        mock_jwt.return_value = "mock-jwt"
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock GitHub API response with different user's account
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "account": {
                "id": "different-user-id",  # Does NOT match auth_header github_id
                "login": "otheruser",
                "type": "User",
            }
        }

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_http_get.side_effect = mock_get

        response = client.post(
            "/api/github/link-installation?installation_id=99999",
            headers=auth_header,
        )

        assert response.status_code == 403
        assert "don't own this GitHub account" in response.json()["detail"]


class TestGitHubWebhook:
    """Test GitHub webhook handler."""

    @patch("main.GITHUB_WEBHOOK_SECRET", "test-secret")
    @patch("main.get_supabase")
    def test_webhook_installation_deleted(self, mock_get_supabase, client):
        """Test webhook handles installation deletion."""
        import hashlib
        import hmac

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        payload = b'{"action": "deleted", "installation": {"id": 12345}}'
        signature = "sha256=" + hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-GitHub-Event": "installation",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("main.GITHUB_WEBHOOK_SECRET", "test-secret")
    @patch("main.get_supabase")
    def test_webhook_push_event(self, mock_get_supabase, client):
        """Test webhook handles push events."""
        import hashlib
        import hmac

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        # Mock finding a tracked repo
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        payload = b'{"ref": "refs/heads/main", "repository": {"full_name": "owner/repo", "default_branch": "main"}}'
        signature = "sha256=" + hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch("main.GITHUB_WEBHOOK_SECRET", None)
    def test_webhook_rejected_without_secret_configured(self, client):
        """Test webhook is rejected when secret not configured."""
        response = client.post(
            "/webhooks/github",
            json={"action": "test"},
            headers={"X-GitHub-Event": "installation"},
        )

        assert response.status_code == 401

    @patch("main.GITHUB_WEBHOOK_SECRET", "test-secret")
    def test_webhook_invalid_signature(self, client):
        """Test webhook rejects invalid signature."""
        response = client.post(
            "/webhooks/github",
            json={"action": "test"},
            headers={
                "X-GitHub-Event": "installation",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )

        assert response.status_code == 401
        assert "Invalid webhook signature" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
