"""
Autodoc Cloud API - FastAPI backend for Cloud Run

Handles:
- Repository analysis triggers
- Analysis status updates
- Artifact storage management
- Usage tracking
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


class AnalyzeRequest(BaseModel):
    github_repo: str  # "owner/repo" format
    is_private: bool = False
    branch: str = "main"


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


# =============================================================================
# Auth Dependencies
# =============================================================================


async def get_current_user(
    authorization: str = Header(..., description="Bearer token from AuthJoy"),
) -> UserInfo:
    """
    Validate AuthJoy token and return user info.

    In production, this should verify the JWT with AuthJoy's public keys.
    For MVP, we trust the token and extract claims.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]  # Remove "Bearer " prefix

    # TODO: Verify JWT signature with AuthJoy public keys
    # For now, decode without verification (MVP only!)
    try:
        import jwt

        # Decode without verification - ONLY for development!
        # In production, verify with AuthJoy's JWKS
        payload = jwt.decode(token, options={"verify_signature": False})

        return UserInfo(
            user_id=payload.get("sub", ""),
            github_id=payload.get("github_id", payload.get("sub", "")),
            plan=payload.get("plan", "free"),
        )
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


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
    1. Clone the repository
    2. Run autodoc analyze
    3. Upload artifacts to cloud storage
    4. Update repository status
    """
    supabase = get_supabase()

    try:
        logger.info(f"Starting analysis for {github_repo} (repo_id: {repo_id})")

        # Update status to analyzing
        supabase.table("repositories").update({"status": "analyzing"}).eq("id", repo_id).execute()

        # TODO: Implement actual analysis
        # 1. Clone repo using GitHub API/token
        # 2. Run: autodoc analyze ./repo --save
        # 3. Upload autodoc_cache.json to GCS/R2
        # 4. Create analysis_artifact record

        # For now, simulate analysis
        import asyncio

        await asyncio.sleep(5)  # Simulate work

        # Update status to ready
        supabase.table("repositories").update(
            {
                "status": "ready",
                "last_analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        logger.info(f"Analysis complete for {github_repo}")

    except Exception as e:
        logger.error(f"Analysis failed for {github_repo}: {e}")
        supabase.table("repositories").update({"status": "failed"}).eq("id", repo_id).execute()


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
async def analyze_repository(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user),
):
    """
    Trigger analysis for a GitHub repository.

    Creates a repository record and queues analysis in the background.
    """
    supabase = get_supabase()

    # Check plan limits
    await check_plan_limits(user, request.is_private, supabase)

    # Check if repo already exists for this user
    existing = (
        supabase.table("repositories")
        .select("id, status")
        .eq("user_id", user.user_id)
        .eq("github_repo", request.github_repo)
        .execute()
    )

    if existing.data:
        repo = existing.data[0]
        if repo["status"] == "analyzing":
            raise HTTPException(status_code=409, detail="Repository is already being analyzed")

        # Re-analyze existing repo
        background_tasks.add_task(run_analysis, repo["id"], request.github_repo, request.branch)
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
                "github_repo": request.github_repo,
                "is_private": request.is_private,
                "status": "pending",
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create repository record")

    repo_id = result.data[0]["id"]

    # Queue analysis
    background_tasks.add_task(run_analysis, repo_id, request.github_repo, request.branch)

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
async def reanalyze_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user),
):
    """Trigger re-analysis for an existing repository."""
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
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
