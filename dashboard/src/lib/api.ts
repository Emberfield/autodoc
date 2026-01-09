/**
 * Autodoc Cloud API Client
 *
 * Client for interacting with the Cloud Run backend API.
 */

const API_URL = process.env.NEXT_PUBLIC_AUTODOC_API_URL || "http://localhost:8080";

export interface AnalyzeRequest {
  github_repo: string;
  is_private?: boolean;
  branch?: string;
}

export interface AnalyzeResponse {
  repo_id: string;
  status: string;
  message: string;
}

export interface RepoStatus {
  id: string;
  github_repo: string;
  status: "pending" | "analyzing" | "ready" | "failed";
  last_analyzed_at: string | null;
  artifacts: Array<{
    artifact_type: string;
    storage_path: string;
    created_at: string;
  }>;
}

export interface UsageStats {
  plan: string;
  month: string;
  enrichment_used: number;
  enrichment_limit: number;
  analyze_used: number;
}

class AutodocApiClient {
  private baseUrl: string;
  private getToken: (() => Promise<string | null>) | null = null;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Set the token provider function (called from AuthJoy context)
   */
  setTokenProvider(getToken: () => Promise<string | null>) {
    this.getToken = getToken;
  }

  private async getAuthHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (this.getToken) {
      const token = await this.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const headers = await this.getAuthHeaders();

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string; version: string }> {
    return this.request("GET", "/health");
  }

  /**
   * Trigger analysis for a repository
   */
  async analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
    return this.request("POST", "/api/v1/analyze", request);
  }

  /**
   * List all repositories for the current user
   */
  async listRepos(): Promise<RepoStatus[]> {
    return this.request("GET", "/api/v1/repos");
  }

  /**
   * Get status of a specific repository
   */
  async getRepo(repoId: string): Promise<RepoStatus> {
    return this.request("GET", `/api/v1/repos/${repoId}`);
  }

  /**
   * Delete a repository
   */
  async deleteRepo(repoId: string): Promise<void> {
    return this.request("DELETE", `/api/v1/repos/${repoId}`);
  }

  /**
   * Trigger re-analysis for a repository
   */
  async reanalyze(repoId: string): Promise<AnalyzeResponse> {
    return this.request("POST", `/api/v1/repos/${repoId}/reanalyze`);
  }

  /**
   * Get usage statistics
   */
  async getUsage(): Promise<UsageStats> {
    return this.request("GET", "/api/v1/usage");
  }
}

// Export singleton instance
export const autodocApi = new AutodocApiClient();

// Export class for testing
export { AutodocApiClient };
