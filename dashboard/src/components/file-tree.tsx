"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, File, Folder, Brain } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { FileTreeNode } from "@/lib/data";

interface FileTreeProps {
  node: FileTreeNode;
  level?: number;
}

export function FileTree({ node, level = 0 }: FileTreeProps) {
  const [isOpen, setIsOpen] = useState(level < 2);

  if (node.type === "file") {
    return (
      <div
        className={cn(
          "flex items-center gap-2 py-1 px-2 rounded hover:bg-accent text-sm",
          "cursor-pointer"
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        <File className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <span className="truncate flex-1">{node.name}</span>
        {node.entityCount !== undefined && node.entityCount > 0 && (
          <Badge variant="outline" className="text-xs h-5">
            {node.entityCount}
          </Badge>
        )}
        {node.enrichedCount !== undefined && node.enrichedCount > 0 && (
          <Badge variant="secondary" className="text-xs h-5 gap-1">
            <Brain className="h-3 w-3" />
            {node.enrichedCount}
          </Badge>
        )}
      </div>
    );
  }

  // Skip root node display
  if (node.name === "." && level === 0) {
    return (
      <div className="space-y-0.5">
        {node.children?.map((child) => (
          <FileTree key={child.path} node={child} level={0} />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 py-1 px-2 rounded hover:bg-accent text-sm cursor-pointer"
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
        <Folder
          className={cn(
            "h-4 w-4 flex-shrink-0",
            isOpen ? "text-primary" : "text-muted-foreground"
          )}
        />
        <span className="truncate">{node.name}</span>
      </div>
      {isOpen && node.children && (
        <div className="space-y-0.5">
          {node.children.map((child) => (
            <FileTree key={child.path} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
