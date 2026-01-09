"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FolderTree,
  Code2,
  Package,
  Sparkles,
  Search,
  BookOpen,
  LogOut,
  LogIn,
  Crown,
  Star,
  User,
  GitBranch,
} from "lucide-react";
import { useAutodoc } from "@/components/providers";

// Primary navigation - what users care about most
const primaryNav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/features", label: "Features", icon: Sparkles },
  { href: "/architecture", label: "How It Works", icon: BookOpen },
];

// Secondary navigation - browsing and searching
const browseNav = [
  { href: "/entities", label: "Entities", icon: Code2 },
  { href: "/files", label: "Files", icon: FolderTree },
  { href: "/packs", label: "Packs", icon: Package },
  { href: "/search", label: "Search", icon: Search },
];

// Cloud-only navigation
const cloudNav = [
  { href: "/repositories", label: "Repositories", icon: GitBranch },
];

function PlanBadge({ plan }: { plan: "free" | "pro" | "team" }) {
  const badges = {
    free: { label: "Free", icon: User, className: "text-muted-foreground" },
    pro: { label: "Pro", icon: Star, className: "text-yellow-500" },
    team: { label: "Team", icon: Crown, className: "text-purple-500" },
  };
  const badge = badges[plan];
  const Icon = badge.icon;
  return (
    <span className={cn("flex items-center gap-1 text-xs", badge.className)}>
      <Icon className="h-3 w-3" />
      {badge.label}
    </span>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, isCloudMode, signIn, signOut } = useAutodoc();

  const NavItem = ({ item }: { item: typeof primaryNav[0] }) => {
    const isActive = pathname === item.href;
    const Icon = item.icon;
    return (
      <li>
        <Link
          href={item.href}
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
            isActive
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <Icon className="h-4 w-4" />
          {item.label}
        </Link>
      </li>
    );
  };

  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span className="text-2xl">📄</span>
          Autodoc
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          Code Intelligence Dashboard
        </p>
      </div>

      <nav className="flex-1 p-2 space-y-4">
        {/* Primary Navigation */}
        <div>
          <ul className="space-y-1">
            {primaryNav.map((item) => (
              <NavItem key={item.href} item={item} />
            ))}
          </ul>
        </div>

        {/* Browse Section */}
        <div>
          <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Browse
          </p>
          <ul className="space-y-1">
            {browseNav.map((item) => (
              <NavItem key={item.href} item={item} />
            ))}
          </ul>
        </div>

        {/* Cloud Section - only in cloud mode */}
        {isCloudMode && (
          <div>
            <p className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Cloud
            </p>
            <ul className="space-y-1">
              {cloudNav.map((item) => (
                <NavItem key={item.href} item={item} />
              ))}
            </ul>
          </div>
        )}
      </nav>

      {/* User Section */}
      {isCloudMode && (
        <div className="p-4 border-t border-border">
          {loading ? (
            <div className="animate-pulse h-10 bg-muted rounded" />
          ) : user ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                {user.photoURL ? (
                  <Image
                    src={user.photoURL}
                    alt={user.displayName || "User"}
                    width={32}
                    height={32}
                    className="rounded-full"
                    unoptimized
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                    <User className="h-4 w-4" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {user.displayName || user.email || "User"}
                  </p>
                  <PlanBadge plan={user.plan} />
                </div>
              </div>
              <button
                onClick={signOut}
                className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
              >
                <LogOut className="h-3 w-3" />
                Sign out
              </button>
            </div>
          ) : (
            <button
              onClick={signIn}
              className="flex items-center gap-2 text-sm text-primary hover:underline w-full"
            >
              <LogIn className="h-4 w-4" />
              Sign in with GitHub
            </button>
          )}
        </div>
      )}

      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted-foreground">
          Powered by{" "}
          <a
            href="https://autodoc.tools"
            className="text-primary hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            autodoc.tools
          </a>
        </p>
      </div>
    </aside>
  );
}
