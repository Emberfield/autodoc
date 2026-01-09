"use client";

import { AuthJoyProvider, useAuth } from "@authjoyio/react";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authConfig, isCloudMode } from "@/lib/auth";
import { getSupabaseClient, DbRepository, PLAN_LIMITS } from "@/lib/supabase";
import { autodocApi } from "@/lib/api";

/**
 * Plan limits type (union of all plan types)
 */
type PlanLimits = (typeof PLAN_LIMITS)[keyof typeof PLAN_LIMITS];

/**
 * Extended user context with Supabase data
 */
interface AutodocUser {
  // AuthJoy user data
  id: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  // Supabase data
  plan: "free" | "pro" | "team";
  repositories: DbRepository[];
  // Computed
  limits: PlanLimits;
  canAddPrivateRepo: boolean;
  canAddPublicRepo: boolean;
}

interface AutodocContextValue {
  user: AutodocUser | null;
  loading: boolean;
  isCloudMode: boolean;
  signIn: () => void;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AutodocContext = createContext<AutodocContextValue | null>(null);

/**
 * Hook to access Autodoc user context
 */
export function useAutodoc() {
  const context = useContext(AutodocContext);
  if (!context) {
    throw new Error("useAutodoc must be used within AutodocProvider");
  }
  return context;
}

/**
 * Inner provider that has access to AuthJoy context
 */
function AutodocInnerProvider({ children }: { children: ReactNode }) {
  const { user: authUser, signOut: authSignOut, loading: authLoading, getIdToken } = useAuth();
  const [autodocUser, setAutodocUser] = useState<AutodocUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Set up API client token provider
  useEffect(() => {
    autodocApi.setTokenProvider(async () => {
      if (!authUser) return null;
      try {
        return await getIdToken();
      } catch {
        return null;
      }
    });
  }, [authUser, getIdToken]);

  // Sync user to Supabase and load full profile
  useEffect(() => {
    async function syncUser() {
      if (!authUser) {
        setAutodocUser(null);
        setLoading(false);
        return;
      }

      try {
        // Upsert user to Supabase
        const supabase = getSupabaseClient();
        const { data: dbUser, error: upsertError } = await supabase
          .from("users")
          .upsert(
            {
              id: authUser.uid,
              github_id: authUser.providerData?.[0]?.uid || authUser.uid,
              email: authUser.email,
              display_name: authUser.displayName,
              avatar_url: authUser.photoURL,
            },
            { onConflict: "id" }
          )
          .select()
          .single();

        if (upsertError) {
          console.error("Failed to sync user:", upsertError);
        }

        // Load repositories
        const { data: repos } = await supabase
          .from("repositories")
          .select("*")
          .eq("user_id", authUser.uid);

        const plan = (dbUser?.plan || "free") as "free" | "pro" | "team";
        const limits = PLAN_LIMITS[plan];
        const privateCount = repos?.filter((r) => r.is_private).length || 0;
        const publicCount = repos?.filter((r) => !r.is_private).length || 0;

        setAutodocUser({
          id: authUser.uid,
          email: authUser.email,
          displayName: authUser.displayName,
          photoURL: authUser.photoURL,
          plan,
          repositories: repos || [],
          limits,
          canAddPrivateRepo: privateCount < limits.private_repos,
          canAddPublicRepo: publicCount < limits.public_repos,
        });
      } catch (error) {
        console.error("Error syncing user:", error);
      } finally {
        setLoading(false);
      }
    }

    if (!authLoading) {
      syncUser();
    }
  }, [authUser, authLoading]);

  const refreshUser = async () => {
    if (!authUser) return;
    setLoading(true);
    const supabase = getSupabaseClient();
    // Re-trigger the effect
    const { data: repos } = await supabase
      .from("repositories")
      .select("*")
      .eq("user_id", authUser.uid);

    const { data: dbUser } = await supabase
      .from("users")
      .select("*")
      .eq("id", authUser.uid)
      .single();

    const plan = (dbUser?.plan || "free") as "free" | "pro" | "team";
    const limits = PLAN_LIMITS[plan];
    const privateCount = repos?.filter((r) => r.is_private).length || 0;
    const publicCount = repos?.filter((r) => !r.is_private).length || 0;

    setAutodocUser({
      id: authUser.uid,
      email: authUser.email,
      displayName: authUser.displayName,
      photoURL: authUser.photoURL,
      plan,
      repositories: repos || [],
      limits,
      canAddPrivateRepo: privateCount < limits.private_repos,
      canAddPublicRepo: publicCount < limits.public_repos,
    });
    setLoading(false);
  };

  const signIn = () => {
    // Redirect to sign-in page
    window.location.href = "/sign-in";
  };

  const signOut = async () => {
    await authSignOut();
    setAutodocUser(null);
  };

  const getAccessToken = async (): Promise<string | null> => {
    if (!authUser) return null;
    try {
      return await getIdToken();
    } catch {
      return null;
    }
  };

  return (
    <AutodocContext.Provider
      value={{
        user: autodocUser,
        loading: loading || authLoading,
        isCloudMode: isCloudMode(),
        signIn,
        signOut,
        refreshUser,
        getAccessToken,
      }}
    >
      {children}
    </AutodocContext.Provider>
  );
}

/**
 * Main provider component
 */
export function AutodocProvider({ children }: { children: ReactNode }) {
  // If not in cloud mode, just render children without auth
  if (!isCloudMode()) {
    return (
      <AutodocContext.Provider
        value={{
          user: null,
          loading: false,
          isCloudMode: false,
          signIn: () => {},
          signOut: async () => {},
          refreshUser: async () => {},
          getAccessToken: async () => null,
        }}
      >
        {children}
      </AutodocContext.Provider>
    );
  }

  return (
    <AuthJoyProvider config={authConfig} fallback={<LoadingScreen />}>
      <AutodocInnerProvider>{children}</AutodocInnerProvider>
    </AuthJoyProvider>
  );
}

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-pulse text-muted-foreground">Loading...</div>
    </div>
  );
}
