/**
 * Auto-generated Supabase types
 * Generated from: https://iowgufboylypltycvwcp.supabase.co
 *
 * Note: This includes all tables in the shared Supabase project.
 * Autodoc-specific tables: users, repositories, analysis_artifacts, usage_tracking
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

// Autodoc-specific table types
export interface AutodocUser {
  id: string
  github_id: string
  email: string | null
  display_name: string | null
  avatar_url: string | null
  plan: "free" | "pro" | "team"
  stripe_customer_id: string | null
  created_at: string
  updated_at: string
}

export interface AutodocRepository {
  id: string
  user_id: string
  github_repo: string
  github_installation_id: string | null
  is_private: boolean
  status: "pending" | "analyzing" | "ready" | "failed"
  last_analyzed_at: string | null
  created_at: string
  updated_at: string
}

export interface AutodocAnalysisArtifact {
  id: string
  repo_id: string
  artifact_type: "cache" | "enrichment" | "features" | "graph"
  storage_path: string
  file_size_bytes: number | null
  created_at: string
}

export interface AutodocUsageTracking {
  id: string
  user_id: string
  month: string
  enrichment_count: number
  analyze_count: number
  created_at: string
  updated_at: string
}

// Insert types (for creating new records)
export type AutodocUserInsert = Omit<AutodocUser, "created_at" | "updated_at"> & {
  created_at?: string
  updated_at?: string
}

export type AutodocRepositoryInsert = Omit<AutodocRepository, "id" | "created_at" | "updated_at"> & {
  id?: string
  created_at?: string
  updated_at?: string
}

export type AutodocAnalysisArtifactInsert = Omit<AutodocAnalysisArtifact, "id" | "created_at"> & {
  id?: string
  created_at?: string
}

// Plan limits
export const PLAN_LIMITS = {
  free: {
    private_repos: 0,
    public_repos: 1,
    users: 1,
    enrichment_monthly: 100,
  },
  pro: {
    private_repos: 5,
    public_repos: 10,
    users: 1,
    enrichment_monthly: 1000,
  },
  team: {
    private_repos: 20,
    public_repos: 50,
    users: 5,
    enrichment_monthly: 5000,
  },
} as const

export type PlanType = keyof typeof PLAN_LIMITS
