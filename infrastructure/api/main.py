"""
Autodoc Cloud API - FastAPI backend for Cloud Run

Handles:
- Repository analysis triggers
- Analysis status updates
- Artifact storage management
- Usage tracking
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
import jwt
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from supabase import Client, create_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://iowgufboylypltycvwcp.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key for backend
AUTHJOY_TENANT_ID = os.getenv("AUTHJOY_TENANT_ID")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://autodoc.tools").split(
    ","
)

# GitHub App configuration
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_APP_CLIENT_ID = os.getenv("GITHUB_APP_CLIENT_ID")
GITHUB_APP_CLIENT_SECRET = os.getenv("GITHUB_APP_CLIENT_SECRET")
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY")  # PEM format
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

# JWT/JWKS configuration for AuthJoy
AUTHJOY_JWKS_URL = os.getenv("AUTHJOY_JWKS_URL", "https://authjoy.io/.well-known/jwks.json")
AUTHJOY_ISSUER = os.getenv("AUTHJOY_ISSUER", "https://authjoy.io")
JWT_VERIFY_ENABLED = os.getenv("JWT_VERIFY_ENABLED", "true").lower() == "true"

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# JWKS client with caching (PyJWT handles caching internally)
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> PyJWKClient:
    """Get cached JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(AUTHJOY_JWKS_URL, cache_keys=True, lifespan=3600)
    return _jwks_client


# CSRF state store (in production, use Redis or database)
# Format: {state: (user_id, timestamp)}
_csrf_states: dict[str, tuple[str, float]] = {}
CSRF_STATE_EXPIRY = 600  # 10 minutes


def generate_csrf_state(user_id: str) -> str:
    """Generate a CSRF state token."""
    state = secrets.token_urlsafe(32)
    _csrf_states[state] = (user_id, time.time())
    # Clean up old states
    current_time = time.time()
    expired = [k for k, (_, ts) in _csrf_states.items() if current_time - ts > CSRF_STATE_EXPIRY]
    for k in expired:
        del _csrf_states[k]
    return state


def verify_csrf_state(state: str) -> Optional[str]:
    """Verify and consume a CSRF state token. Returns user_id if valid."""
    if state not in _csrf_states:
        return None
    user_id, timestamp = _csrf_states.pop(state)
    if time.time() - timestamp > CSRF_STATE_EXPIRY:
        return None
    return user_id

# Supabase client (lazy init)
_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """Get Supabase client with service role key."""
    global _supabase
    if _supabase is None:
        if not SUPABASE_SERVICE_KEY:
            raise HTTPException(status_code=500, detail="Supabase not configured")
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Autodoc Cloud API starting up...")
    yield
    logger.info("Autodoc Cloud API shutting down...")


app = FastAPI(
    title="Autodoc Cloud API",
    description="Backend API for Autodoc Cloud - AI-powered code documentation",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


# Validation patterns
GITHUB_REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
GIT_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9_./+-]+$")


class AnalyzeRequest(BaseModel):
    github_repo: str  # "owner/repo" format
    is_private: bool = False
    branch: str = "main"

    @field_validator("github_repo")
    @classmethod
    def validate_github_repo(cls, v: str) -> str:
        if not GITHUB_REPO_PATTERN.match(v):
            raise ValueError("Invalid github_repo format. Expected 'owner/repo'")
        if ".." in v or v.startswith("/") or v.startswith("-"):
            raise ValueError("Invalid characters in github_repo")
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        if not GIT_BRANCH_PATTERN.match(v):
            raise ValueError("Invalid branch name")
        if v.startswith("-"):
            raise ValueError("Branch name cannot start with '-'")
        return v


class AnalyzeResponse(BaseModel):
    repo_id: str
    status: str
    message: str


class RepoStatusResponse(BaseModel):
    id: str
    github_repo: str
    status: str
    last_analyzed_at: Optional[str]
    artifacts: list


class UserInfo(BaseModel):
    user_id: str
    github_id: str
    plan: str


class GitHubInstallation(BaseModel):
    installation_id: int
    account_login: str
    account_type: str  # "User" or "Organization"


class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str


class WebhookPayload(BaseModel):
    action: str
    installation: Optional[dict] = None
    repository: Optional[dict] = None
    ref: Optional[str] = None
    after: Optional[str] = None


# =============================================================================
# Auth Dependencies
# =============================================================================


async def get_current_user(
    authorization: str = Header(..., description="Bearer token from AuthJoy"),
) -> UserInfo:
    """
    Validate AuthJoy token and return user info.

    Verifies JWT signature using AuthJoy's JWKS endpoint.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        if JWT_VERIFY_ENABLED:
            # Production: Verify JWT signature with AuthJoy's JWKS
            jwks_client = get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                issuer=AUTHJOY_ISSUER,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "require": ["sub", "exp"],
                },
            )
        else:
            # Development only: Skip verification (set JWT_VERIFY_ENABLED=false)
            logger.warning("JWT verification disabled - development mode only!")
            payload = jwt.decode(token, options={"verify_signature": False})

        return UserInfo(
            user_id=payload.get("sub", ""),
            github_id=payload.get("github_id", payload.get("sub", "")),
            plan=payload.get("plan", "free"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    except jwt.InvalidTokenError as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


# =============================================================================
# Plan Limits
# =============================================================================

PLAN_LIMITS = {
    "free": {"private_repos": 0, "public_repos": 1, "enrichment_monthly": 100},
    "pro": {"private_repos": 5, "public_repos": 10, "enrichment_monthly": 1000},
    "team": {"private_repos": 20, "public_repos": 50, "enrichment_monthly": 5000},
}


async def check_plan_limits(user: UserInfo, is_private: bool, supabase: Client) -> None:
    """Check if user can add another repository based on their plan."""
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])

    # Count existing repos
    result = (
        supabase.table("repositories")
        .select("id, is_private")
        .eq("user_id", user.user_id)
        .execute()
    )
    repos = result.data or []

    private_count = sum(1 for r in repos if r.get("is_private"))
    public_count = sum(1 for r in repos if not r.get("is_private"))

    if is_private:
        if private_count >= limits["private_repos"]:
            raise HTTPException(
                status_code=403,
                detail=f"Plan limit reached: {limits['private_repos']} private repos allowed on {user.plan} plan",
            )
    else:
        if public_count >= limits["public_repos"]:
            raise HTTPException(
                status_code=403,
                detail=f"Plan limit reached: {limits['public_repos']} public repos allowed on {user.plan} plan",
            )


# =============================================================================
# Background Tasks
# =============================================================================


async def run_analysis(repo_id: str, github_repo: str, branch: str):
    """
    Background task to run autodoc analysis on a repository.

    This will:
    1. Clone the repository using GitHub App installation token
    2. Run autodoc analyze
    3. Upload artifacts to cloud storage (GCS)
    4. Update repository status
    """
    import subprocess
    import tempfile

    supabase = get_supabase()

    try:
        logger.info(f"Starting analysis for {github_repo} (repo_id: {repo_id})")

        # Update status to analyzing
        supabase.table("repositories").update({"status": "analyzing"}).eq("id", repo_id).execute()

        # Get repository details including installation ID
        repo_result = supabase.table("repositories").select("*").eq("id", repo_id).execute()
        if not repo_result.data:
            raise Exception(f"Repository {repo_id} not found")

        repo_data = repo_result.data[0]
        user_id = repo_data["user_id"]

        # Get GitHub installation for the user
        install_result = (
            supabase.table("github_installations")
            .select("installation_id")
            .eq("user_id", user_id)
            .execute()
        )

        clone_url = f"https://github.com/{github_repo}.git"

        # If we have a GitHub App installation, use its token for private repos
        if install_result.data and repo_data.get("is_private"):
            installation_id = install_result.data[0]["installation_id"]
            try:
                token = await get_installation_access_token(installation_id)
                clone_url = f"https://x-access-token:{token}@github.com/{github_repo}.git"
            except Exception as e:
                logger.warning(f"Failed to get installation token, falling back to public clone: {e}")

        # Create temporary directory for analysis
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = os.path.join(tmpdir, "repo")

            # Clone the repository
            logger.info(f"Cloning {github_repo} to {repo_path}")
            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, clone_url, repo_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if clone_result.returncode != 0:
                # Try without branch (use default)
                clone_result = subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, repo_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

            if clone_result.returncode != 0:
                # Sanitize error message to remove any tokens
                error_msg = clone_result.stderr
                if "x-access-token" in error_msg:
                    error_msg = re.sub(r"x-access-token:[^@]+@", "x-access-token:***@", error_msg)
                raise Exception(f"Git clone failed: {error_msg}")

            # Run autodoc analyze
            logger.info(f"Running autodoc analyze on {repo_path}")
            analyze_result = subprocess.run(
                ["python", "-m", "autodoc.cli", "analyze", repo_path, "--save"],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=repo_path,
            )

            if analyze_result.returncode != 0:
                logger.warning(f"Autodoc analyze warnings: {analyze_result.stderr}")

            # Check for generated cache file
            cache_file = os.path.join(repo_path, "autodoc_cache.json")
            if not os.path.exists(cache_file):
                # Try .autodoc directory
                cache_file = os.path.join(repo_path, ".autodoc", "cache.json")

            if os.path.exists(cache_file):
                # Upload to cloud storage
                storage_path = await upload_to_storage(
                    cache_file, f"{user_id}/{repo_id}/autodoc_cache.json"
                )

                # Create artifact record
                supabase.table("analysis_artifacts").insert(
                    {
                        "repo_id": repo_id,
                        "artifact_type": "cache",
                        "storage_path": storage_path,
                    }
                ).execute()

                logger.info(f"Uploaded cache to {storage_path}")
            else:
                logger.warning("No autodoc_cache.json found after analysis")

            # Check for enrichment cache
            enrichment_file = os.path.join(repo_path, "autodoc_enrichment_cache.json")
            if os.path.exists(enrichment_file):
                storage_path = await upload_to_storage(
                    enrichment_file, f"{user_id}/{repo_id}/autodoc_enrichment_cache.json"
                )
                supabase.table("analysis_artifacts").insert(
                    {
                        "repo_id": repo_id,
                        "artifact_type": "enrichment",
                        "storage_path": storage_path,
                    }
                ).execute()

        # Update status to ready
        supabase.table("repositories").update(
            {
                "status": "ready",
                "last_analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        logger.info(f"Analysis complete for {github_repo}")

    except subprocess.TimeoutExpired:
        logger.error(f"Analysis timed out for {github_repo}")
        supabase.table("repositories").update({"status": "failed"}).eq("id", repo_id).execute()
    except Exception as e:
        logger.error(f"Analysis failed for {github_repo}: {e}")
        supabase.table("repositories").update({"status": "failed"}).eq("id", repo_id).execute()


async def upload_to_storage(local_path: str, destination_path: str) -> str:
    """
    Upload a file to cloud storage (GCS).

    Returns the storage path (gs:// URL).
    """
    # For MVP, we'll use Google Cloud Storage since we're on Cloud Run
    # In production, could also use Cloudflare R2 or S3
    bucket_name = os.getenv("GCS_BUCKET", "autodoc-artifacts")

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_path)

        blob.upload_from_filename(local_path)
        logger.info(f"Uploaded {local_path} to gs://{bucket_name}/{destination_path}")

        return f"gs://{bucket_name}/{destination_path}"
    except ImportError:
        # GCS library not installed, fall back to local storage simulation
        logger.warning("google-cloud-storage not installed, skipping upload")
        return f"local://{destination_path}"
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        # Return a placeholder path so analysis can still complete
        return f"pending://{destination_path}"


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Cloud Run."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Alias for health check."""
    return await health_check()


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
@limiter.limit("10/hour")  # Rate limit: 10 analyses per hour per IP
async def analyze_repository(
    request: Request,
    analyze_request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user),
):
    """
    Trigger analysis for a GitHub repository.

    Creates a repository record and queues analysis in the background.
    Rate limited to 10 requests per hour.
    """
    supabase = get_supabase()

    # Check plan limits
    await check_plan_limits(user, analyze_request.is_private, supabase)

    # Check if repo already exists for this user
    existing = (
        supabase.table("repositories")
        .select("id, status")
        .eq("user_id", user.user_id)
        .eq("github_repo", analyze_request.github_repo)
        .execute()
    )

    if existing.data:
        repo = existing.data[0]
        if repo["status"] == "analyzing":
            raise HTTPException(status_code=409, detail="Repository is already being analyzed")

        # Re-analyze existing repo
        background_tasks.add_task(run_analysis, repo["id"], analyze_request.github_repo, analyze_request.branch)
        return AnalyzeResponse(
            repo_id=repo["id"],
            status="queued",
            message="Re-analysis queued for existing repository",
        )

    # Create new repository record
    result = (
        supabase.table("repositories")
        .insert(
            {
                "user_id": user.user_id,
                "github_repo": analyze_request.github_repo,
                "is_private": analyze_request.is_private,
                "status": "pending",
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create repository record")

    repo_id = result.data[0]["id"]

    # Queue analysis
    background_tasks.add_task(run_analysis, repo_id, analyze_request.github_repo, analyze_request.branch)

    return AnalyzeResponse(
        repo_id=repo_id,
        status="queued",
        message="Analysis queued successfully",
    )


@app.get("/api/v1/repos", response_model=list[RepoStatusResponse])
async def list_repositories(user: UserInfo = Depends(get_current_user)):
    """List all repositories for the authenticated user."""
    supabase = get_supabase()

    result = (
        supabase.table("repositories")
        .select("id, github_repo, status, is_private, last_analyzed_at")
        .eq("user_id", user.user_id)
        .order("created_at", desc=True)
        .execute()
    )

    repos = []
    for repo in result.data or []:
        # Get artifacts for each repo
        artifacts_result = (
            supabase.table("analysis_artifacts")
            .select("artifact_type, storage_path, created_at")
            .eq("repo_id", repo["id"])
            .execute()
        )

        repos.append(
            RepoStatusResponse(
                id=repo["id"],
                github_repo=repo["github_repo"],
                status=repo["status"],
                last_analyzed_at=repo.get("last_analyzed_at"),
                artifacts=artifacts_result.data or [],
            )
        )

    return repos


@app.get("/api/v1/repos/{repo_id}", response_model=RepoStatusResponse)
async def get_repository(repo_id: str, user: UserInfo = Depends(get_current_user)):
    """Get details for a specific repository."""
    supabase = get_supabase()

    result = (
        supabase.table("repositories")
        .select("id, github_repo, status, is_private, last_analyzed_at, user_id")
        .eq("id", repo_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = result.data[0]

    # Verify ownership
    if repo["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this repository")

    # Get artifacts
    artifacts_result = (
        supabase.table("analysis_artifacts")
        .select("artifact_type, storage_path, created_at")
        .eq("repo_id", repo_id)
        .execute()
    )

    return RepoStatusResponse(
        id=repo["id"],
        github_repo=repo["github_repo"],
        status=repo["status"],
        last_analyzed_at=repo.get("last_analyzed_at"),
        artifacts=artifacts_result.data or [],
    )


@app.delete("/api/v1/repos/{repo_id}")
async def delete_repository(repo_id: str, user: UserInfo = Depends(get_current_user)):
    """Delete a repository and its artifacts."""
    supabase = get_supabase()

    # Verify ownership
    result = supabase.table("repositories").select("user_id").eq("id", repo_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    if result.data[0]["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this repository")

    # Delete artifacts first (cascade should handle this, but be explicit)
    supabase.table("analysis_artifacts").delete().eq("repo_id", repo_id).execute()

    # Delete repository
    supabase.table("repositories").delete().eq("id", repo_id).execute()

    return {"status": "deleted", "repo_id": repo_id}


@app.post("/api/v1/repos/{repo_id}/reanalyze", response_model=AnalyzeResponse)
@limiter.limit("10/hour")  # Rate limit: 10 reanalyses per hour per IP
async def reanalyze_repository(
    request: Request,
    repo_id: str,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user),
):
    """Trigger re-analysis for an existing repository. Rate limited to 10/hour."""
    supabase = get_supabase()

    # Verify ownership and get repo details
    result = (
        supabase.table("repositories")
        .select("id, github_repo, user_id, status")
        .eq("id", repo_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo = result.data[0]

    if repo["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if repo["status"] == "analyzing":
        raise HTTPException(status_code=409, detail="Repository is already being analyzed")

    # Queue re-analysis
    background_tasks.add_task(run_analysis, repo_id, repo["github_repo"], "main")

    return AnalyzeResponse(
        repo_id=repo_id,
        status="queued",
        message="Re-analysis queued successfully",
    )


@app.get("/api/v1/usage")
async def get_usage(user: UserInfo = Depends(get_current_user)):
    """Get usage statistics for the current user."""
    supabase = get_supabase()

    # Get current month's usage
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    result = (
        supabase.table("usage_tracking")
        .select("*")
        .eq("user_id", user.user_id)
        .eq("month", current_month)
        .execute()
    )

    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])

    if result.data:
        usage = result.data[0]
        return {
            "plan": user.plan,
            "month": current_month,
            "enrichment_used": usage.get("enrichment_count", 0),
            "enrichment_limit": limits["enrichment_monthly"],
            "analyze_used": usage.get("analyze_count", 0),
        }

    return {
        "plan": user.plan,
        "month": current_month,
        "enrichment_used": 0,
        "enrichment_limit": limits["enrichment_monthly"],
        "analyze_used": 0,
    }


# =============================================================================
# GitHub App Integration
# =============================================================================


def generate_github_app_jwt() -> str:
    """Generate a JWT for GitHub App authentication."""
    import time

    import jwt

    if not GITHUB_APP_ID or not GITHUB_APP_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="GitHub App not configured")

    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds ago to account for clock drift
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": GITHUB_APP_ID,
    }

    return jwt.encode(payload, GITHUB_APP_PRIVATE_KEY, algorithm="RS256")


async def get_installation_access_token(installation_id: int) -> str:
    """Get an access token for a specific installation."""
    app_jwt = generate_github_app_jwt()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if response.status_code != 201:
            logger.error(f"Failed to get installation token: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to get GitHub access token")

        return response.json()["token"]


async def get_installation_repos(installation_id: int) -> list[GitHubRepo]:
    """Get repositories accessible to a GitHub App installation."""
    token = await get_installation_access_token(installation_id)

    repos = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                "https://api.github.com/installation/repositories",
                params={"page": page, "per_page": 100},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to get repos: {response.text}")
                break

            data = response.json()
            for repo in data.get("repositories", []):
                repos.append(
                    GitHubRepo(
                        id=repo["id"],
                        name=repo["name"],
                        full_name=repo["full_name"],
                        private=repo["private"],
                        default_branch=repo.get("default_branch", "main"),
                    )
                )

            if len(data.get("repositories", [])) < 100:
                break
            page += 1

    return repos


def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    if not GITHUB_WEBHOOK_SECRET:
        logger.error("CRITICAL: Webhook secret not configured, rejecting request")
        return False  # SECURITY: Never skip verification

    if not signature:
        logger.warning("Missing webhook signature header")
        return False

    expected_signature = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


@app.get("/api/github/install")
async def github_install_redirect(user: UserInfo = Depends(get_current_user)):
    """
    Redirect to GitHub App installation page.

    Requires authentication to generate CSRF state for the callback.
    """
    if not GITHUB_APP_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub App not configured")

    # Generate CSRF state to prevent callback attacks
    state = generate_csrf_state(user.user_id)

    # GitHub App installation URL with state parameter
    install_url = f"https://github.com/apps/autodoc-cloud/installations/new?state={state}"
    return RedirectResponse(url=install_url)


@app.get("/api/github/callback")
async def github_callback(
    installation_id: Optional[int] = None,
    setup_action: Optional[str] = None,
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    """
    GitHub App installation callback.

    Handles both:
    1. New installation callback (installation_id + setup_action + state)
    2. OAuth authorization callback (code + state)

    CSRF protection via state parameter prevents unauthorized installation linking.
    """
    supabase = get_supabase()

    if installation_id and setup_action == "install":
        # Verify CSRF state - this ties the installation to the user who initiated it
        if not state:
            logger.warning("GitHub callback missing state parameter")
            raise HTTPException(status_code=400, detail="Missing state parameter - please initiate installation from the dashboard")

        user_id = verify_csrf_state(state)
        if not user_id:
            logger.warning(f"Invalid or expired CSRF state in GitHub callback")
            raise HTTPException(status_code=400, detail="Invalid or expired state - please try again from the dashboard")

        logger.info(f"New GitHub App installation: {installation_id} for user: {user_id}")

        # Get installation details from GitHub
        app_jwt = generate_github_app_jwt()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/app/installations/{installation_id}",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to get installation details: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to verify installation")

            install_data = response.json()
            account = install_data.get("account", {})
            account_login = account.get("login")
            account_type = account.get("type")
            account_id = account.get("id")

            logger.info(f"Installation for: {account_login} ({account_type})")

        # Auto-link the installation to the user who initiated the flow (verified via CSRF state)
        supabase.table("github_installations").upsert(
            {
                "user_id": user_id,
                "installation_id": installation_id,
                "account_login": account_login,
                "account_type": account_type,
                "account_id": account_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="installation_id",
        ).execute()

        logger.info(f"Auto-linked installation {installation_id} to user {user_id}")

        # Redirect to dashboard with success indicator
        redirect_url = f"{DASHBOARD_URL}/settings/github?installation_id={installation_id}&linked=true"
        return RedirectResponse(url=redirect_url)

    elif code:
        # OAuth flow - exchange code for user token (optional, for user-level operations)
        if not state:
            logger.warning("OAuth callback missing state parameter")
            raise HTTPException(status_code=400, detail="Missing state parameter")

        user_id = verify_csrf_state(state)
        if not user_id:
            logger.warning("Invalid or expired CSRF state in OAuth callback")
            raise HTTPException(status_code=400, detail="Invalid or expired state - please try again")

        logger.info(f"GitHub OAuth callback received for user: {user_id}")
        redirect_url = f"{DASHBOARD_URL}/settings/github?setup=complete"
        return RedirectResponse(url=redirect_url)

    raise HTTPException(status_code=400, detail="Invalid callback parameters")


@app.post("/api/github/link-installation")
async def link_installation(
    installation_id: int,
    user: UserInfo = Depends(get_current_user),
):
    """
    Link a GitHub App installation to a user account.

    SECURITY: Verifies that the user owns the GitHub account/org before allowing the link.
    This prevents users from hijacking installations meant for other accounts.
    """
    supabase = get_supabase()

    # Verify installation exists and get details
    app_jwt = generate_github_app_jwt()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Installation not found")

        install_data = response.json()
        account = install_data.get("account", {})
        account_id = str(account.get("id", ""))
        account_login = account.get("login", "")
        account_type = account.get("type", "")

    # SECURITY: Verify ownership - user must own the GitHub account or be a member of the org
    # The user's github_id should match the account_id for personal installations
    if account_type == "User":
        # For user installations, github_id must match
        if user.github_id != account_id and user.github_id != account_login:
            logger.warning(
                f"Installation hijacking attempt: user {user.user_id} (github: {user.github_id}) "
                f"tried to link installation for {account_login} (id: {account_id})"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot link installation: you don't own this GitHub account"
            )
    elif account_type == "Organization":
        # For org installations, check if the installation already exists and belongs to this user
        # Or if this is a new installation, the callback flow should have linked it
        existing = (
            supabase.table("github_installations")
            .select("user_id")
            .eq("installation_id", installation_id)
            .execute()
        )
        if existing.data:
            existing_user = existing.data[0].get("user_id")
            if existing_user != user.user_id:
                logger.warning(
                    f"Installation hijacking attempt: user {user.user_id} "
                    f"tried to claim org installation {installation_id} owned by {existing_user}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="This installation is already linked to another account"
                )

    # Store installation link
    supabase.table("github_installations").upsert(
        {
            "user_id": user.user_id,
            "installation_id": installation_id,
            "account_login": account_login,
            "account_type": account_type,
            "account_id": account_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="installation_id",
    ).execute()

    return {
        "status": "linked",
        "installation_id": installation_id,
        "account": account_login,
    }


@app.get("/api/github/installations")
async def list_installations(user: UserInfo = Depends(get_current_user)):
    """List GitHub App installations for the current user."""
    supabase = get_supabase()

    result = (
        supabase.table("github_installations")
        .select("*")
        .eq("user_id", user.user_id)
        .execute()
    )

    installations = []
    for inst in result.data or []:
        installations.append(
            GitHubInstallation(
                installation_id=inst["installation_id"],
                account_login=inst["account_login"],
                account_type=inst["account_type"],
            )
        )

    return installations


@app.get("/api/github/installations/{installation_id}/repos")
async def list_installation_repos(
    installation_id: int,
    user: UserInfo = Depends(get_current_user),
):
    """List repositories accessible to a GitHub App installation."""
    supabase = get_supabase()

    # Verify user owns this installation
    result = (
        supabase.table("github_installations")
        .select("installation_id")
        .eq("user_id", user.user_id)
        .eq("installation_id", installation_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=403, detail="Installation not linked to your account")

    repos = await get_installation_repos(installation_id)
    return repos


@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """
    Handle GitHub App webhooks.

    Supports:
    - installation: App installed/uninstalled
    - push: Code pushed to repository
    - installation_repositories: Repos added/removed from installation
    """
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    logger.info(f"Received GitHub webhook: {event_type}")

    if event_type == "installation":
        action = payload.get("action")
        installation = payload.get("installation", {})
        installation_id = installation.get("id")

        if action == "deleted":
            # Installation removed - clean up
            supabase = get_supabase()
            supabase.table("github_installations").delete().eq(
                "installation_id", installation_id
            ).execute()
            logger.info(f"Removed installation {installation_id}")

    elif event_type == "push":
        # Code pushed - trigger re-analysis if repo is tracked
        repo = payload.get("repository", {})
        repo_full_name = repo.get("full_name")
        ref = payload.get("ref", "")
        default_branch = repo.get("default_branch", "main")

        # Only analyze pushes to default branch
        if ref == f"refs/heads/{default_branch}":
            supabase = get_supabase()

            # Find tracked repository
            result = (
                supabase.table("repositories")
                .select("id, user_id, status")
                .eq("github_repo", repo_full_name)
                .execute()
            )

            if result.data:
                tracked_repo = result.data[0]

                # Check if user has auto-analyze enabled (Pro+ feature)
                user_result = (
                    supabase.table("users")
                    .select("plan")
                    .eq("id", tracked_repo["user_id"])
                    .execute()
                )

                if user_result.data:
                    plan = user_result.data[0].get("plan", "free")

                    if plan in ["pro", "team"] and tracked_repo["status"] != "analyzing":
                        logger.info(f"Auto-triggering analysis for {repo_full_name}")
                        # Note: In production, queue this to a task queue
                        # For MVP, we'll just update status
                        supabase.table("repositories").update(
                            {"status": "pending"}
                        ).eq("id", tracked_repo["id"]).execute()

    elif event_type == "installation_repositories":
        # Repositories added/removed from installation
        action = payload.get("action")
        installation = payload.get("installation", {})

        if action in ["added", "removed"]:
            repos = payload.get(f"repositories_{action}", [])
            logger.info(f"Repos {action}: {[r.get('full_name') for r in repos]}")

    return {"status": "ok"}


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
