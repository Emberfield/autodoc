import fs from "fs";
import path from "path";

// Types for autodoc data structures
export interface CodeEntity {
  name: string;
  type: "function" | "class" | "method";
  file_path: string;
  line_number: number;
  end_line?: number;
  docstring?: string;
  signature?: string;
  decorators?: string[];
  parent_class?: string;
  parameters?: Array<{ name: string; type?: string; default?: string }>;
  return_type?: string;
}

export interface AnalysisCache {
  entities: CodeEntity[];
  files_analyzed: number;
  timestamp: string;
}

export interface EnrichmentData {
  [key: string]: {
    summary?: string;
    description?: string;
    parameters?: Array<{ name: string; description: string }>;
    returns?: string;
    examples?: string[];
    enriched_at?: string;
  };
}

export interface ContextPack {
  name: string;
  display_name: string;
  description?: string;
  files: string[];
  security_level?: string;
}

export interface AutodocConfig {
  context_packs?: ContextPack[];
  llm?: {
    provider: string;
    model: string;
  };
  embeddings?: {
    provider: string;
  };
}

export interface DetectedFeature {
  id: number;
  name?: string;
  display_name?: string;
  files: string[];
  file_count: number;
  reasoning?: string;
  sample_files?: Array<{ path: string; summary?: string }>;
}

export interface FeaturesCache {
  community_count: number;
  modularity: number;
  features: Record<string, DetectedFeature>;
  detected_at?: string;
}

// Data loading functions
export function getProjectRoot(): string {
  // Look for .autodoc.yaml or autodoc_cache.json to find project root
  let dir = process.cwd();
  while (dir !== "/") {
    if (
      fs.existsSync(path.join(dir, ".autodoc.yaml")) ||
      fs.existsSync(path.join(dir, "autodoc_cache.json"))
    ) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return process.cwd();
}

export function loadAnalysisCache(projectRoot?: string): AnalysisCache | null {
  const root = projectRoot || getProjectRoot();
  const cachePath = path.join(root, "autodoc_cache.json");

  if (!fs.existsSync(cachePath)) {
    return null;
  }

  try {
    const data = fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function loadEnrichmentCache(
  projectRoot?: string
): EnrichmentData | null {
  const root = projectRoot || getProjectRoot();
  const cachePath = path.join(root, "autodoc_enrichment_cache.json");

  if (!fs.existsSync(cachePath)) {
    return null;
  }

  try {
    const data = fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(data);
  } catch {
    return null;
  }
}

export function loadConfig(projectRoot?: string): AutodocConfig | null {
  const root = projectRoot || getProjectRoot();
  const configPath = path.join(root, ".autodoc.yaml");

  if (!fs.existsSync(configPath)) {
    return null;
  }

  try {
    const yaml = require("yaml");
    const data = fs.readFileSync(configPath, "utf-8");
    return yaml.parse(data);
  } catch {
    return null;
  }
}

export function loadFeaturesCache(projectRoot?: string): FeaturesCache | null {
  const root = projectRoot || getProjectRoot();
  const cachePath = path.join(root, ".autodoc", "features_cache.json");

  if (!fs.existsSync(cachePath)) {
    return null;
  }

  try {
    const data = fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(data);
  } catch {
    return null;
  }
}

// Aggregate data for dashboard
export interface DashboardData {
  projectRoot: string;
  analysis: AnalysisCache | null;
  enrichment: EnrichmentData | null;
  config: AutodocConfig | null;
  features: FeaturesCache | null;
  stats: {
    totalEntities: number;
    totalFiles: number;
    enrichedCount: number;
    packCount: number;
    featureCount: number;
  };
}

export function loadDashboardData(projectRoot?: string): DashboardData {
  const root = projectRoot || getProjectRoot();
  const analysis = loadAnalysisCache(root);
  const enrichment = loadEnrichmentCache(root);
  const config = loadConfig(root);
  const features = loadFeaturesCache(root);

  const uniqueFiles = new Set(analysis?.entities?.map((e) => e.file_path) || []);

  return {
    projectRoot: root,
    analysis,
    enrichment,
    config,
    features,
    stats: {
      totalEntities: analysis?.entities?.length || 0,
      totalFiles: uniqueFiles.size,
      enrichedCount: Object.keys(enrichment || {}).length,
      packCount: config?.context_packs?.length || 0,
      featureCount: Object.keys(features?.features || {}).length,
    },
  };
}

// Build file tree structure
export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileTreeNode[];
  entityCount?: number;
  enrichedCount?: number;
}

export function buildFileTree(
  entities: CodeEntity[],
  enrichment: EnrichmentData | null
): FileTreeNode {
  const root: FileTreeNode = {
    name: ".",
    path: ".",
    type: "directory",
    children: [],
  };

  const pathMap = new Map<string, FileTreeNode>();
  pathMap.set(".", root);

  // Group entities by file
  const fileEntities = new Map<string, CodeEntity[]>();
  for (const entity of entities) {
    const existing = fileEntities.get(entity.file_path) || [];
    existing.push(entity);
    fileEntities.set(entity.file_path, existing);
  }

  // Build tree structure
  for (const filePath of fileEntities.keys()) {
    const parts = filePath.split("/").filter(Boolean);
    let currentPath = ".";
    let currentNode = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const newPath = currentPath === "." ? part : `${currentPath}/${part}`;
      const isFile = i === parts.length - 1;

      let node = pathMap.get(newPath);
      if (!node) {
        const entities = fileEntities.get(filePath) || [];
        const enrichedKeys = Object.keys(enrichment || {});
        const enrichedCount = entities.filter((e) =>
          enrichedKeys.some((k) => k.includes(e.name))
        ).length;

        node = {
          name: part,
          path: newPath,
          type: isFile ? "file" : "directory",
          children: isFile ? undefined : [],
          entityCount: isFile ? entities.length : undefined,
          enrichedCount: isFile ? enrichedCount : undefined,
        };
        pathMap.set(newPath, node);
        currentNode.children = currentNode.children || [];
        currentNode.children.push(node);
      }

      currentPath = newPath;
      currentNode = node;
    }
  }

  // Sort children alphabetically, directories first
  const sortChildren = (node: FileTreeNode) => {
    if (node.children) {
      node.children.sort((a, b) => {
        if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      node.children.forEach(sortChildren);
    }
  };
  sortChildren(root);

  return root;
}
