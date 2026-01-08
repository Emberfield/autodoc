"use client";

import Link from "next/link";
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
} from "lucide-react";

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

export function Sidebar() {
  const pathname = usePathname();

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
      </nav>

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
