# Autodoc Node.js SDK

Node.js/TypeScript SDK for [Autodoc](https://emberfield.github.io/autodoc/) - AI-powered code intelligence.

## Prerequisites

Autodoc must be installed via pip:

```bash
pip install ai-code-autodoc
```

## Installation

```bash
npm install autodoc-sdk
```

## Quick Start

```typescript
import { Autodoc } from 'autodoc-sdk';

// Initialize with your repo path
const autodoc = new Autodoc('/path/to/your/repo');

// Analyze the codebase
await autodoc.analyze();

// Search with natural language
const results = await autodoc.search('user authentication flow');
console.log(results);

// List context packs
const packs = await autodoc.listPacks();

// Analyze impact of changes
const impact = await autodoc.analyzeImpact(['src/auth/login.ts']);
if (impact.criticalPacks.length > 0) {
  console.warn('Critical packs affected:', impact.criticalPacks);
}
```

## API Reference

### `new Autodoc(options)`

Create a new Autodoc instance.

```typescript
// Simple usage
const autodoc = new Autodoc('/path/to/repo');

// With options
const autodoc = new Autodoc({
  path: '/path/to/repo',
  quiet: true,
  pythonPath: '/usr/bin/python3',
});
```

### `autodoc.analyze(options?)`

Analyze the codebase.

```typescript
const result = await autodoc.analyze({
  incremental: true,        // Only analyze changed files
  excludePatterns: ['*.test.ts'],
  save: true,               // Save to cache
});
```

### `autodoc.search(query, options?)`

Search with natural language.

```typescript
const results = await autodoc.search('authentication', {
  limit: 10,
  typeFilter: 'function',
});

// Returns: SearchResult[]
// {
//   name: string;
//   type: string;
//   filePath: string;
//   lineNumber: number;
//   similarity: number;
// }
```

### `autodoc.listPacks(options?)`

List all context packs.

```typescript
const packs = await autodoc.listPacks({
  tag: 'security',
  securityLevel: 'critical',
});
```

### `autodoc.getPack(name)`

Get a specific pack by name.

```typescript
const authPack = await autodoc.getPack('auth');
```

### `autodoc.analyzeImpact(changedFiles)`

Analyze impact of file changes.

```typescript
const impact = await autodoc.analyzeImpact([
  'src/auth/login.ts',
  'src/auth/session.ts',
]);

console.log('Affected packs:', impact.affectedPacks);
console.log('Critical packs:', impact.criticalPacks);
console.log('Security implications:', impact.securityImplications);
```

### `autodoc.queryPack(packName, query, options?)`

Search within a specific pack.

```typescript
const results = await autodoc.queryPack('auth', 'token validation', {
  limit: 5,
});
```

### `autodoc.buildPack(name, options?)`

Build a pack's index.

```typescript
await autodoc.buildPack('auth', {
  withEmbeddings: true,
  withSummary: true,    // Requires LLM API key
  dryRun: false,
});

// Build all packs
await autodoc.buildPack('all');
```

### `autodoc.getPackDependencies(name, options?)`

Get pack dependencies.

```typescript
const deps = await autodoc.getPackDependencies('payments', {
  transitive: true,  // Include transitive dependencies
});
```

### `isAutodocInstalled(pythonPath?)`

Check if autodoc is available.

```typescript
import { isAutodocInstalled } from 'autodoc-sdk';

if (!isAutodocInstalled()) {
  console.error('Please install autodoc: pip install ai-code-autodoc');
}
```

## TypeScript Support

Full TypeScript support with exported types:

```typescript
import {
  Autodoc,
  SearchResult,
  AnalysisResult,
  ImpactResult,
  Pack,
  AutodocOptions,
} from 'autodoc-sdk';
```

## License

MIT
