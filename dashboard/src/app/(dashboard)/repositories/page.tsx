"use client";

import { useState } from "react";
import { useAutodoc } from "@/components/providers";
import { PLAN_LIMITS } from "@/lib/supabase";
import { autodocApi } from "@/lib/api";
import {
  Plus,
  GitBranch,
  RefreshCw,
  ExternalLink,
  Trash2,
  Lock,
  Unlock,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react";

const statusConfig = {
  pending: { icon: Clock, label: "Pending", className: "text-yellow-500" },
  analyzing: { icon: Loader2, label: "Analyzing", className: "text-blue-500 animate-spin" },
  ready: { icon: CheckCircle, label: "Ready", className: "text-green-500" },
  failed: { icon: AlertCircle, label: "Failed", className: "text-red-500" },
};

export default function RepositoriesPage() {
  const { user, loading, isCloudMode, signIn, refreshUser } = useAutodoc();
  const [isAddingRepo, setIsAddingRepo] = useState(false);
  const [newRepoUrl, setNewRepoUrl] = useState("");
  const [addingError, setAddingError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Not in cloud mode - show self-hosted message
  if (!isCloudMode) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4">Repositories</h1>
        <div className="bg-card border border-border rounded-lg p-8 text-center">
          <GitBranch className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">Self-Hosted Mode</h2>
          <p className="text-muted-foreground max-w-md mx-auto">
            Repository management is only available in Autodoc Cloud. In self-hosted mode,
            run <code className="bg-muted px-1 rounded">autodoc analyze</code> directly on your codebase.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not logged in
  if (!user) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold mb-4">Repositories</h1>
        <div className="bg-card border border-border rounded-lg p-8 text-center">
          <GitBranch className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">Sign In Required</h2>
          <p className="text-muted-foreground mb-4">
            Sign in with GitHub to manage your repositories.
          </p>
          <button
            onClick={signIn}
            className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors"
          >
            Sign in with GitHub
          </button>
        </div>
      </div>
    );
  }

  const limits = PLAN_LIMITS[user.plan];
  const privateCount = user.repositories.filter((r) => r.is_private).length;
  const publicCount = user.repositories.filter((r) => !r.is_private).length;

  const handleAddRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingError(null);
    setIsSubmitting(true);

    try {
      // Parse repo URL to extract owner/repo
      const match = newRepoUrl.match(/github\.com[/:]([^/]+)\/([^/\s.]+)/);
      if (!match) {
        setAddingError("Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)");
        setIsSubmitting(false);
        return;
      }

      const [, owner, repo] = match;
      const githubRepo = `${owner}/${repo.replace(/\.git$/, "")}`;

      // Check if already exists
      if (user.repositories.some((r) => r.github_repo === githubRepo)) {
        setAddingError("This repository is already added");
        setIsSubmitting(false);
        return;
      }

      // Call API to add and analyze repo
      await autodocApi.analyze({
        github_repo: githubRepo,
        is_private: false, // TODO: detect from GitHub API
      });

      // Success - refresh user data and close form
      await refreshUser();
      setNewRepoUrl("");
      setIsAddingRepo(false);
    } catch (err) {
      console.error("Error adding repository:", err);
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setAddingError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteRepo = async (repoId: string) => {
    if (!confirm("Are you sure you want to remove this repository?")) return;

    try {
      await autodocApi.deleteRepo(repoId);
      await refreshUser();
    } catch (err) {
      console.error("Error deleting repository:", err);
    }
  };

  const handleReanalyze = async (repoId: string) => {
    try {
      await autodocApi.reanalyze(repoId);
      await refreshUser();
    } catch (err) {
      console.error("Error triggering reanalysis:", err);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Repositories</h1>
          <p className="text-muted-foreground">
            {user.repositories.length} of {limits.public_repos + limits.private_repos} repos used
          </p>
        </div>
        <button
          onClick={() => setIsAddingRepo(true)}
          disabled={!user.canAddPublicRepo && !user.canAddPrivateRepo}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4" />
          Add Repository
        </button>
      </div>

      {/* Add Repository Form */}
      {isAddingRepo && (
        <form onSubmit={handleAddRepo} className="bg-card border border-border rounded-lg p-4 mb-6">
          <h3 className="font-medium mb-3">Add a GitHub Repository</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={newRepoUrl}
              onChange={(e) => setNewRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              autoFocus
            />
            <button
              type="submit"
              disabled={isSubmitting || !newRepoUrl.trim()}
              className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAddingRepo(false);
                setNewRepoUrl("");
                setAddingError(null);
              }}
              className="text-muted-foreground hover:text-foreground px-4 py-2"
            >
              Cancel
            </button>
          </div>
          {addingError && (
            <p className="text-red-500 text-sm mt-2">{addingError}</p>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            Public repos: {publicCount}/{limits.public_repos} | Private repos: {privateCount}/{limits.private_repos}
          </p>
        </form>
      )}

      {/* Repository List */}
      {user.repositories.length === 0 ? (
        <div className="bg-card border border-border rounded-lg p-8 text-center">
          <GitBranch className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">No Repositories Yet</h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-4">
            Add your first GitHub repository to start generating AI-powered documentation.
          </p>
          <button
            onClick={() => setIsAddingRepo(true)}
            className="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors"
          >
            Add Your First Repository
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {user.repositories.map((repo) => {
            const StatusIcon = statusConfig[repo.status].icon;
            return (
              <div
                key={repo.id}
                className="bg-card border border-border rounded-lg p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    {repo.is_private ? (
                      <Lock className="h-4 w-4 text-yellow-500" />
                    ) : (
                      <Unlock className="h-4 w-4 text-muted-foreground" />
                    )}
                    <a
                      href={`https://github.com/${repo.github_repo}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium hover:text-primary flex items-center gap-1"
                    >
                      {repo.github_repo}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  <div className={`flex items-center gap-1 text-sm ${statusConfig[repo.status].className}`}>
                    <StatusIcon className="h-4 w-4" />
                    {statusConfig[repo.status].label}
                  </div>
                  {repo.last_analyzed_at && (
                    <span className="text-xs text-muted-foreground">
                      Last analyzed: {new Date(repo.last_analyzed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReanalyze(repo.id)}
                    className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                    title="Re-analyze"
                  >
                    <RefreshCw className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteRepo(repo.id)}
                    className="p-2 text-muted-foreground hover:text-red-500 transition-colors"
                    title="Remove"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Plan Upgrade CTA */}
      {(!user.canAddPublicRepo || !user.canAddPrivateRepo) && (
        <div className="mt-8 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-lg p-6">
          <h3 className="font-semibold mb-2">Need More Repositories?</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {user.plan === "free"
              ? "Upgrade to Pro for 5 private repos and 10 public repos."
              : "Upgrade to Team for 20 private repos and 50 public repos."}
          </p>
          <a
            href="/pricing"
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:bg-primary/90 transition-colors text-sm"
          >
            View Plans
          </a>
        </div>
      )}
    </div>
  );
}
