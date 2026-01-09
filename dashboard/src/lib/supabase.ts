import { createClient, SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase client for Autodoc Cloud
 *
 * Environment variables:
 * - NEXT_PUBLIC_SUPABASE_URL: Your Supabase project URL
 * - NEXT_PUBLIC_SUPABASE_ANON_KEY: Your Supabase anon key
 */
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Create client lazily to avoid build-time errors when env vars aren't set
let _supabase: SupabaseClient | null = null;

export function getSupabaseClient(): SupabaseClient {
  if (!_supabase) {
    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error("Supabase environment variables not configured");
    }
    _supabase = createClient(supabaseUrl, supabaseAnonKey);
  }
  return _supabase;
}

// Export for backwards compatibility (will throw if env vars missing)
export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : (null as unknown as SupabaseClient);

/**
 * Database types for Autodoc Cloud
 */
export interface DbUser {
  id: string;
  github_id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  plan: "free" | "pro" | "team";
  stripe_customer_id: string | null;
  created_at: string;
}

export interface DbRepository {
  id: string;
  user_id: string;
  github_repo: string; // 'owner/repo'
  github_installation_id: string | null;
  is_private: boolean;
  status: "pending" | "analyzing" | "ready" | "failed";
  last_analyzed_at: string | null;
  created_at: string;
}

export interface DbAnalysisArtifact {
  id: string;
  repo_id: string;
  artifact_type: "cache" | "enrichment" | "features";
  storage_path: string;
  created_at: string;
}

/**
 * Plan limits configuration
 */
export const PLAN_LIMITS = {
  free: { private_repos: 0, public_repos: 1, users: 1, enrichment_monthly: 100 },
  pro: { private_repos: 5, public_repos: 10, users: 1, enrichment_monthly: 1000 },
  team: { private_repos: 20, public_repos: 50, users: 5, enrichment_monthly: 5000 },
} as const;
