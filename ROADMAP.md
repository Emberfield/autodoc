# Autodoc Product Roadmap

## Overview

Two major initiatives to drive adoption and monetization:
1. **Example App** - Showcase autodoc capabilities on a real-world codebase
2. **Dashboard UI** - Visual explorer for code intelligence with SaaS potential

---

## 1. Example App (Demo Showcase)

**Goal**: A compelling demo that shows autodoc analyzing a popular open-source project, demonstrating all features end-to-end.

### Phase 1: Core Demo Setup
- [ ] Select target repo (e.g., FastAPI, Flask, or a medium-sized TypeScript project)
- [ ] Create `examples/` directory with demo scripts
- [ ] Document step-by-step demo walkthrough
- [ ] Record terminal session as asciinema/GIF for README

### Phase 2: Pre-computed Results
- [ ] Run full analysis pipeline on target repo
- [ ] Export enriched data (JSON, comprehensive_docs.md)
- [ ] Generate context packs with summaries
- [ ] Run feature detection and naming
- [ ] Host pre-computed results for instant exploration

### Phase 3: Interactive Demo
- [ ] Create demo script that runs commands with explanations
- [ ] Add `--demo` flag to CLI for guided walkthrough
- [ ] Include sample queries showing semantic search
- [ ] Show MCP integration with AI assistant

---

## 2. Dashboard UI (Code Intelligence Explorer)

**Goal**: A web-based UI for exploring analyzed codebases with search, visualization, and AI-powered insights.

### Business Model
- **Free tier**: Local-only, self-hosted dashboard
- **Pro tier ($9-19/mo)**: Cloud-hosted, team sharing, persistent storage
- **Team tier ($49/mo)**: Multiple repos, API access, integrations

### Phase 1: Local Dashboard MVP
- [ ] Create `dashboard/` directory with React/Next.js app
- [ ] Read from local `.autodoc/` cache files
- [ ] Basic views:
  - [ ] File tree with enrichment status indicators
  - [ ] Entity list (functions, classes) with search
  - [ ] Entity detail view with AI-generated docs
  - [ ] Pack overview with file groupings

### Phase 2: Search & Navigation
- [ ] Full-text search across entities
- [ ] Semantic search integration (ChromaDB)
- [ ] Click-through from search results to source
- [ ] Breadcrumb navigation (pack → file → entity)
- [ ] Keyboard shortcuts for power users

### Phase 3: Visualizations
- [ ] Dependency graph (files/modules)
- [ ] Feature clusters visualization (from GDS detection)
- [ ] Call hierarchy explorer
- [ ] Import/export relationships
- [ ] Pack coverage heatmap

### Phase 4: AI Features
- [ ] "Explain this code" button per entity
- [ ] "Find similar code" using embeddings
- [ ] "Suggest refactoring" for complex functions
- [ ] Chat interface for codebase Q&A
- [ ] Impact analysis visualization

### Phase 5: Cloud & Monetization
- [ ] User authentication (GitHub OAuth)
- [ ] Cloud storage for analysis results
- [ ] Team workspaces with shared access
- [ ] Webhook integration (analyze on push)
- [ ] Usage analytics and billing (Stripe)
- [ ] API for programmatic access

### Phase 6: Integrations
- [ ] VS Code extension (sidebar panel)
- [ ] GitHub App (PR comments with insights)
- [ ] Slack bot for codebase queries
- [ ] Export to Notion/Confluence

---

## Technical Stack Recommendations

### Dashboard Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **State**: Zustand or Jotai
- **Graphs**: D3.js or react-force-graph
- **Search**: Fuse.js (client) or Meilisearch (server)

### Dashboard Backend (Cloud tier)
- **API**: FastAPI or Hono
- **Database**: PostgreSQL + pgvector
- **Auth**: Clerk or NextAuth
- **Storage**: S3/R2 for analysis artifacts
- **Queue**: Redis + BullMQ for async jobs

---

## Priority & Timeline Suggestions

| Initiative | Effort | Impact | Priority |
|------------|--------|--------|----------|
| Example App Phase 1 | Low | High | P0 - Do first |
| Dashboard Phase 1 | Medium | High | P1 |
| Example App Phase 2-3 | Low | Medium | P1 |
| Dashboard Phase 2-3 | Medium | High | P2 |
| Dashboard Phase 4-5 | High | High | P3 |
| Dashboard Phase 6 | High | Medium | P4 |

---

## Success Metrics

### Example App
- README demo GIF views
- GitHub stars growth rate
- "I tried autodoc because of the demo" feedback

### Dashboard
- Free tier signups
- Free → Pro conversion rate
- Monthly recurring revenue (MRR)
- Weekly active users (WAU)
- Repos analyzed per user
