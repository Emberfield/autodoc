"use client";

import { SignIn } from "@authjoyio/react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isCloudMode } from "@/lib/auth";

export default function SignInPage() {
  const router = useRouter();

  // If not in cloud mode, redirect to home
  if (!isCloudMode()) {
    router.replace("/");
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-8">
        {/* Logo */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-2">
            <span className="text-4xl">📄</span>
            <span className="text-2xl font-bold">Autodoc</span>
          </Link>
          <p className="mt-2 text-sm text-muted-foreground">
            AI-powered code documentation
          </p>
        </div>

        {/* Sign In Form */}
        <SignIn
          socialProviders={["github"]}
          showSignUpLink={false}
          title="Sign in to Autodoc"
          subtitle="Connect your GitHub account to get started"
          redirectUrl="/"
          onSuccess={() => {
            router.push("/");
          }}
          className="bg-card border border-border rounded-lg p-6"
        />

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          By signing in, you agree to our{" "}
          <a href="https://autodoc.tools/terms" className="text-primary hover:underline">
            Terms of Service
          </a>{" "}
          and{" "}
          <a href="https://autodoc.tools/privacy" className="text-primary hover:underline">
            Privacy Policy
          </a>
        </p>
      </div>
    </div>
  );
}
