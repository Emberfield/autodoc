/**
 * Autodoc Node.js SDK
 *
 * AI-powered code intelligence for your JavaScript/TypeScript projects.
 *
 * @example
 * ```typescript
 * import { Autodoc } from 'autodoc-sdk';
 *
 * const autodoc = new Autodoc('/path/to/repo');
 * await autodoc.analyze();
 * const results = await autodoc.search('authentication flow');
 * ```
 */

import { spawn, spawnSync } from 'child_process';
import * as path from 'path';

export interface SearchResult {
  name: string;
  type: string;
  filePath: string;
  lineNumber: number;
  similarity: number;
  docstring?: string;
  code?: string;
  pack?: string;
}

export interface AnalysisResult {
  filesAnalyzed: number;
  totalEntities: number;
  functions: number;
  classes: number;
  methods: number;
  hasEmbeddings: boolean;
}

export interface ImpactResult {
  affectedPacks: string[];
  criticalPacks: string[];
  filesAffected: string[];
  securityImplications: string[];
}

export interface Pack {
  name: string;
  displayName: string;
  description: string;
  files: string[];
  dependencies: string[];
  securityLevel?: 'critical' | 'high' | 'normal';
  tags: string[];
}

export interface SkillExportResult {
  skillName: string;
  skillPath: string;
  filesCreated: string[];
  packName: string;
}

export interface AutodocOptions {
  /** Path to the repository root */
  path: string;
  /** Suppress console output */
  quiet?: boolean;
  /** Python executable to use */
  pythonPath?: string;
}

/**
 * Execute an autodoc CLI command and return the JSON result.
 * Uses spawn (not exec) to prevent shell injection.
 */
async function execAutodoc(
  args: string[],
  options: { cwd?: string; pythonPath?: string } = {}
): Promise<any> {
  const pythonPath = options.pythonPath || 'python3';

  return new Promise((resolve, reject) => {
    // Using spawn with explicit args array prevents shell injection
    const proc = spawn(pythonPath, ['-m', 'autodoc.cli', ...args], {
      cwd: options.cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false, // Explicitly disable shell
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`autodoc exited with code ${code}: ${stderr}`));
        return;
      }

      try {
        // Try to parse as JSON
        const result = JSON.parse(stdout);
        resolve(result);
      } catch {
        // Return raw output if not JSON
        resolve(stdout.trim());
      }
    });

    proc.on('error', (err) => {
      reject(new Error(`Failed to spawn autodoc: ${err.message}`));
    });
  });
}

/**
 * Check if autodoc is installed and available.
 * Uses spawnSync (not execSync) to prevent shell injection.
 */
export function isAutodocInstalled(pythonPath: string = 'python3'): boolean {
  try {
    // Using spawnSync with explicit args array prevents shell injection
    const result = spawnSync(pythonPath, ['-m', 'autodoc.cli', '--help'], {
      stdio: 'pipe',
      shell: false, // Explicitly disable shell
    });
    return result.status === 0;
  } catch {
    return false;
  }
}

/**
 * Main Autodoc SDK class.
 *
 * Provides a clean TypeScript interface to autodoc's code intelligence features.
 */
export class Autodoc {
  private readonly repoPath: string;
  private readonly quiet: boolean;
  private readonly pythonPath: string;

  /**
   * Create a new Autodoc instance.
   *
   * @param options - Configuration options or path string
   */
  constructor(options: AutodocOptions | string) {
    if (typeof options === 'string') {
      this.repoPath = path.resolve(options);
      this.quiet = false;
      this.pythonPath = 'python3';
    } else {
      this.repoPath = path.resolve(options.path);
      this.quiet = options.quiet ?? false;
      this.pythonPath = options.pythonPath ?? 'python3';
    }
  }

  /**
   * Analyze the codebase.
   *
   * @param options - Analysis options
   */
  async analyze(options: {
    incremental?: boolean;
    excludePatterns?: string[];
    save?: boolean;
  } = {}): Promise<AnalysisResult> {
    const args = ['analyze', this.repoPath];

    if (options.save !== false) {
      args.push('--save');
    }

    if (options.incremental) {
      args.push('--incremental');
    }

    if (options.excludePatterns) {
      for (const pattern of options.excludePatterns) {
        args.push('--exclude', pattern);
      }
    }

    // Note: This returns text output, not JSON currently
    // We'd need to enhance the CLI to support JSON output for analyze
    await execAutodoc(args, { cwd: this.repoPath, pythonPath: this.pythonPath });

    // Return a basic result - full implementation would parse CLI output
    return {
      filesAnalyzed: 0,
      totalEntities: 0,
      functions: 0,
      classes: 0,
      methods: 0,
      hasEmbeddings: true,
    };
  }

  /**
   * Search the codebase with natural language.
   *
   * @param query - Search query
   * @param options - Search options
   */
  async search(
    query: string,
    options: {
      limit?: number;
      typeFilter?: string;
      pack?: string;
    } = {}
  ): Promise<SearchResult[]> {
    const args = ['search', query, '--json'];

    if (options.limit) {
      args.push('--limit', options.limit.toString());
    }

    if (options.typeFilter) {
      args.push('--type', options.typeFilter);
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (!Array.isArray(result)) {
      return [];
    }

    return result.map((r: any) => ({
      name: r.entity?.name || r.name,
      type: r.entity?.type || r.type,
      filePath: r.entity?.file_path || r.file_path,
      lineNumber: r.entity?.line_number || r.line_number,
      similarity: r.similarity || 0,
      docstring: r.entity?.docstring || r.docstring,
      code: r.entity?.code || r.code,
    }));
  }

  /**
   * List all context packs.
   *
   * @param options - Filter options
   */
  async listPacks(options: {
    tag?: string;
    securityLevel?: string;
  } = {}): Promise<Pack[]> {
    const args = ['pack', 'list', '--json'];

    if (options.tag) {
      args.push('--tag', options.tag);
    }

    if (options.securityLevel) {
      args.push('--security', options.securityLevel);
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (!result.packs || !Array.isArray(result.packs)) {
      return [];
    }

    return result.packs.map((p: any) => ({
      name: p.name,
      displayName: p.display_name,
      description: p.description,
      files: p.files || [],
      dependencies: p.dependencies || [],
      securityLevel: p.security_level,
      tags: p.tags || [],
    }));
  }

  /**
   * Get a specific context pack.
   *
   * @param name - Pack name
   */
  async getPack(name: string): Promise<Pack | null> {
    const args = ['pack', 'info', name, '--json'];

    try {
      const result = await execAutodoc(args, {
        cwd: this.repoPath,
        pythonPath: this.pythonPath,
      });

      if (!result || result.error) {
        return null;
      }

      return {
        name: result.name,
        displayName: result.display_name,
        description: result.description,
        files: result.files || [],
        dependencies: result.dependencies || [],
        securityLevel: result.security_level,
        tags: result.tags || [],
      };
    } catch {
      return null;
    }
  }

  /**
   * Analyze the impact of file changes.
   *
   * @param changedFiles - List of changed file paths
   */
  async analyzeImpact(changedFiles: string[]): Promise<ImpactResult> {
    const args = ['impact', ...changedFiles, '--json'];

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    return {
      affectedPacks: result.affected_packs || [],
      criticalPacks: result.critical_packs || [],
      filesAffected: changedFiles,
      securityImplications: result.security_implications || [],
    };
  }

  /**
   * Search within a specific pack.
   *
   * @param packName - Pack name
   * @param query - Search query
   * @param options - Search options
   */
  async queryPack(
    packName: string,
    query: string,
    options: { limit?: number } = {}
  ): Promise<SearchResult[]> {
    const args = ['pack', 'query', packName, query, '--json'];

    if (options.limit) {
      args.push('--limit', options.limit.toString());
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (!result.results || !Array.isArray(result.results)) {
      return [];
    }

    return result.results.map((r: any) => ({
      name: r.name,
      type: r.type,
      filePath: r.file_path,
      lineNumber: r.line_number,
      similarity: r.similarity || 0,
      pack: packName,
    }));
  }

  /**
   * Build a context pack's index.
   *
   * @param name - Pack name (or 'all' for all packs)
   * @param options - Build options
   */
  async buildPack(
    name: string,
    options: {
      withEmbeddings?: boolean;
      withSummary?: boolean;
      dryRun?: boolean;
    } = {}
  ): Promise<void> {
    const args = ['pack', 'build'];

    if (name === 'all') {
      args.push('--all');
    } else {
      args.push(name);
    }

    if (options.withEmbeddings !== false) {
      args.push('--embeddings');
    }

    if (options.withSummary) {
      args.push('--summary');
    }

    if (options.dryRun) {
      args.push('--dry-run');
    }

    await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });
  }

  /**
   * Get pack dependencies.
   *
   * @param name - Pack name
   * @param options - Options
   */
  async getPackDependencies(
    name: string,
    options: { transitive?: boolean } = {}
  ): Promise<string[]> {
    const args = ['pack', 'deps', name, '--json'];

    if (options.transitive) {
      args.push('--transitive');
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (options.transitive) {
      return result.transitive_dependencies || [];
    }

    return result.direct_dependencies || [];
  }

  /**
   * Get pack status (indexing state).
   */
  async getPackStatus(): Promise<Record<string, any>> {
    const args = ['pack', 'status', '--json'];

    return execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });
  }

  /**
   * Export a context pack as a SKILL.md file.
   *
   * SKILL.md files are discoverable by Claude Code, OpenAI Codex,
   * and other AI assistants.
   *
   * @param name - Pack name to export
   * @param options - Export options
   */
  async exportSkill(
    name: string,
    options: {
      format?: 'claude' | 'codex';
      includeReference?: boolean;
      outputDir?: string;
    } = {}
  ): Promise<SkillExportResult> {
    const args = ['pack', 'export-skill', name, '--json'];

    if (options.format) {
      args.push('--format', options.format);
    }

    if (options.includeReference) {
      args.push('--include-reference');
    }

    if (options.outputDir) {
      args.push('--output', options.outputDir);
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (result.errors && result.errors.length > 0) {
      throw new Error(result.errors[0].error);
    }

    const success = result.success?.[0];
    if (!success) {
      throw new Error('Failed to export skill');
    }

    return {
      skillName: success.skill_name,
      skillPath: success.files_created?.[0] || '',
      filesCreated: success.files_created || [],
      packName: success.pack,
    };
  }

  /**
   * Export all context packs as SKILL.md files.
   *
   * @param options - Export options
   */
  async exportAllSkills(
    options: {
      format?: 'claude' | 'codex';
      includeReference?: boolean;
      outputDir?: string;
    } = {}
  ): Promise<SkillExportResult[]> {
    const args = ['pack', 'export-skill', '--all', '--json'];

    if (options.format) {
      args.push('--format', options.format);
    }

    if (options.includeReference) {
      args.push('--include-reference');
    }

    if (options.outputDir) {
      args.push('--output', options.outputDir);
    }

    const result = await execAutodoc(args, {
      cwd: this.repoPath,
      pythonPath: this.pythonPath,
    });

    if (!result.success || !Array.isArray(result.success)) {
      return [];
    }

    return result.success.map((s: any) => ({
      skillName: s.skill_name,
      skillPath: s.files_created?.[0] || '',
      filesCreated: s.files_created || [],
      packName: s.pack,
    }));
  }
}

// Default export
export default Autodoc;
