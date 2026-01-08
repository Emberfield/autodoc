# Autodoc Cloud: Product & Monetization Roadmap

## Executive Summary

**Vision**: Autodoc remains open-source for local use, while Autodoc Cloud provides a hosted service that automatically documents codebases via GitHub integration and serves that intelligence to coding agents (Claude, Cursor, Copilot).

**Business Model**:
| Tier | Price | Repos | Users | Key Features |
|------|-------|-------|-------|--------------|
| Free | $0 | 1 public | 1 | Local dashboard, manual runs |
| Pro | $8/mo | 5 private | 1 | GitHub Actions, hosted dashboard, MCP endpoint |
| Team | $29/mo | 20 private | 5 | Shared workspace, priority enrichment, API access |
| Enterprise | Custom | Unlimited | Unlimited | SSO, SLA, dedicated infrastructure |

**Revenue Targets**:
- Month 3: 100 Pro subscribers ($800 MRR)
- Month 6: 500 Pro + 50 Team ($5,450 MRR)
- Month 12: 2,000 Pro + 200 Team ($21,800 MRR)

---

## What We Have Today

### Assets
- [x] Core autodoc CLI (analyze, search, enrich, features)
- [x] Python SDK + Node.js SDK + npm package
- [x] MCP server deployed at mcp.autodoc.tools (19 tools)
- [x] Next.js dashboard (local file reading)
- [x] Neo4j graph analysis + GDS feature detection
- [x] ChromaDB embeddings for semantic search
- [x] Landing page at autodoc.tools

### Gaps for Monetization
- [ ] User authentication
- [ ] Multi-tenant data storage
- [ ] GitHub App for repo access
- [ ] Billing integration (Stripe)
- [ ] Per-user MCP endpoints
- [ ] Usage tracking & limits
- [ ] Hosted dashboard deployment

---

## Phase 0: Foundation (Weeks 1-2)
*Goal: Validate demand before building*

### 0.1 Landing Page & Waitlist
- [ ] Add pricing section to autodoc.tools
- [ ] Create waitlist signup (email capture)
- [ ] Add "Notify me when Cloud launches" CTA
- [ ] Track signups in simple database (Supabase/Airtable)

### 0.2 Customer Discovery
- [ ] Interview 10 potential customers (devs using AI coding tools)
- [ ] Key questions:
  - How do you currently give context to AI assistants?
  - Would you pay for automatic codebase documentation?
  - What repos would you connect first?
  - Deal-breakers for a hosted service?
- [ ] Document findings in `docs/customer-research.md`

### 0.3 Competitive Analysis
- [ ] Research: Mintlify, Swimm, Sourcegraph, Codiumate
- [ ] Identify differentiation (MCP-first, agent-focused)
- [ ] Price validation against alternatives

**Exit Criteria**: 50+ waitlist signups, 5+ customer interviews showing willingness to pay

**Critique Phase**:
- [ ] Review waitlist conversion rate (target: >10% from landing page visits)
- [ ] Analyze customer interview patterns
- [ ] Pivot if no clear demand signal

---

## Phase 1: MVP Infrastructure (Weeks 3-6)
*Goal: Build minimum viable multi-tenant architecture*

### 1.1 Authentication
- [ ] Add NextAuth.js to dashboard
- [ ] GitHub OAuth provider (get repo access scopes)
- [ ] User table in database (Supabase PostgreSQL)
- [ ] Session management

### 1.2 Database Schema
```sql
-- Core tables
users (id, github_id, email, plan, created_at)
organizations (id, name, owner_id, plan, created_at)
org_members (org_id, user_id, role)
repositories (id, org_id, github_repo, status, last_analyzed)
analysis_runs (id, repo_id, status, entities_count, started_at, completed_at)

-- Usage tracking
usage_events (id, org_id, event_type, metadata, timestamp)
```

### 1.3 GitHub App
- [ ] Register GitHub App (autodoc-cloud)
- [ ] Permissions: contents:read, metadata:read
- [ ] Installation flow (select repos)
- [ ] Webhook handler for push events
- [ ] Store installation tokens securely

### 1.4 Object Storage
- [ ] Cloudflare R2 bucket for analysis artifacts
- [ ] Structure: `/{org_id}/{repo_id}/{run_id}/`
- [ ] Files: autodoc_cache.json, enrichment_cache.json, features_cache.json
- [ ] Signed URLs for dashboard access

### 1.5 Background Jobs
- [ ] Redis + BullMQ for job queue
- [ ] Job types:
  - `analyze_repo`: Clone, analyze, store results
  - `enrich_entities`: LLM enrichment (rate-limited)
  - `detect_features`: Run GDS feature detection
- [ ] Worker deployment (Cloud Run Jobs or Fly.io)

**Architecture Diagram**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   GitHub    │────▶│  Webhooks   │────▶│  Job Queue  │
│    App      │     │  (Cloud Run)│     │   (Redis)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐     ┌──────▼──────┐
│  Dashboard  │◀───▶│   API       │◀───▶│   Workers   │
│  (Vercel)   │     │ (Cloud Run) │     │ (Cloud Run) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                           │                    │
                    ┌──────▼──────┐     ┌──────▼──────┐
                    │  Supabase   │     │     R2      │
                    │ (Postgres)  │     │  (Storage)  │
                    └─────────────┘     └─────────────┘
```

**Exit Criteria**:
- Can authenticate user via GitHub
- Can analyze a connected repo and store results
- Dashboard shows results from cloud storage

**Critique Phase**:
- [ ] Security review: Are tokens stored securely?
- [ ] Load test: Can we handle 100 concurrent analysis jobs?
- [ ] Cost analysis: What's the per-repo infrastructure cost?

---

## Phase 2: Hosted Dashboard (Weeks 7-9)
*Goal: Production-ready dashboard with cloud data*

### 2.1 Dashboard Cloud Mode
- [ ] Detect cloud vs local mode based on auth
- [ ] Fetch data from API instead of local files
- [ ] Repository selector dropdown
- [ ] Real-time analysis status indicators

### 2.2 Repository Management UI
- [ ] List connected repositories
- [ ] Connect/disconnect repos
- [ ] Manual "Analyze Now" button
- [ ] Analysis history with timestamps
- [ ] Delete repository data

### 2.3 Dashboard Deployment
- [ ] Deploy to Vercel (or Cloudflare Pages)
- [ ] Custom domain: app.autodoc.tools
- [ ] Environment-based configuration
- [ ] Error tracking (Sentry)

### 2.4 Plan Enforcement
- [ ] Check repo limits before connecting
- [ ] Show upgrade prompts when hitting limits
- [ ] Graceful degradation for free tier

**Exit Criteria**:
- User can sign in, connect repo, see analysis in hosted dashboard
- Free tier limited to 1 public repo

**Critique Phase**:
- [ ] UX review: Is the onboarding flow <2 minutes?
- [ ] Performance: Dashboard loads in <2s?
- [ ] Mobile responsive check

---

## Phase 3: GitHub Actions Integration (Weeks 10-12)
*Goal: Automatic analysis on every push*

### 3.1 GitHub Action
Create `autodoc-ai/autodoc-action`:
```yaml
# .github/workflows/autodoc.yml
name: Autodoc Analysis
on: [push]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: autodoc-ai/autodoc-action@v1
        with:
          api-key: ${{ secrets.AUTODOC_API_KEY }}
          # Uploads results to Autodoc Cloud
```

### 3.2 API Key Management
- [ ] Generate API keys per organization
- [ ] API key UI in dashboard settings
- [ ] Rate limiting by API key
- [ ] Key rotation support

### 3.3 Webhook vs Action Trade-offs
| Approach | Pros | Cons |
|----------|------|------|
| GitHub Action | User controls, no server cost | Requires setup, uses user's minutes |
| Webhook | Automatic, seamless | Server cost, clone overhead |

Decision: **Support both**, recommend Action for cost control

### 3.4 Incremental Analysis
- [ ] Store file hashes per analysis run
- [ ] Only re-analyze changed files
- [ ] 10x faster for typical PRs

**Exit Criteria**:
- GitHub Action published to marketplace
- Action successfully uploads results to cloud
- Dashboard shows results from Action run

**Critique Phase**:
- [ ] Test Action in 5 different repo structures
- [ ] Measure Action execution time (target: <5min for 10k LOC)
- [ ] Security audit: Can Action leak secrets?

---

## Phase 4: Per-User MCP Endpoints (Weeks 13-15)
*Goal: Each user gets their own MCP endpoint for AI assistants*

### 4.1 Authenticated MCP
- [ ] Generate unique MCP endpoint per user: `mcp.autodoc.tools/u/{user_id}`
- [ ] Bearer token authentication
- [ ] Endpoint serves only user's repos

### 4.2 MCP Tool Scoping
- [ ] `search` - searches across all user's repos
- [ ] `pack_query` - queries specific repo's packs
- [ ] `analyze_impact` - cross-repo impact analysis

### 4.3 Agent Integration Docs
- [ ] Claude Desktop configuration guide
- [ ] Claude Code configuration guide
- [ ] Cursor integration guide
- [ ] Windsurf integration guide

### 4.4 Context Injection
- [ ] MCP tool: `get_repo_context(repo, query)`
- [ ] Returns relevant code snippets for AI prompts
- [ ] Respects enrichment (summaries, examples)

**Exit Criteria**:
- User can add their MCP endpoint to Claude
- Claude can search user's repos via MCP
- Works with at least 2 AI coding tools

**Critique Phase**:
- [ ] Test with real AI coding sessions
- [ ] Measure context quality vs raw code
- [ ] Latency: MCP responses <500ms?

---

## Phase 5: Billing & Monetization (Weeks 16-18)
*Goal: Accept payments, enforce limits*

### 5.1 Stripe Integration
- [ ] Stripe account setup
- [ ] Products: Pro ($8/mo), Team ($29/mo)
- [ ] Checkout flow for upgrades
- [ ] Customer portal for billing management
- [ ] Webhook handler for subscription events

### 5.2 Plan Enforcement
```python
PLAN_LIMITS = {
    "free": {"private_repos": 0, "public_repos": 1, "users": 1, "enrichment_monthly": 100},
    "pro": {"private_repos": 5, "public_repos": 10, "users": 1, "enrichment_monthly": 1000},
    "team": {"private_repos": 20, "public_repos": 50, "users": 5, "enrichment_monthly": 5000},
}
```

### 5.3 Usage Metering
- [ ] Track: repos connected, entities analyzed, enrichments used
- [ ] Usage dashboard in settings
- [ ] Warning emails at 80% usage
- [ ] Hard limits with upgrade prompts

### 5.4 Trial Experience
- [ ] 14-day Pro trial for new signups
- [ ] No credit card required
- [ ] Convert trial → paid flow

**Exit Criteria**:
- User can upgrade to Pro and pay
- Limits enforced correctly
- Billing history visible

**Critique Phase**:
- [ ] Test all billing edge cases (cancel, refund, failed payment)
- [ ] Verify webhook reliability
- [ ] Check subscription state consistency

---

## Phase 6: Team Features (Weeks 19-22)
*Goal: Multi-user organizations*

### 6.1 Organization Management
- [ ] Create organization
- [ ] Invite members (by email or GitHub)
- [ ] Role-based access (admin, member)
- [ ] Transfer repo ownership

### 6.2 Shared Workspace
- [ ] All org members see same repos
- [ ] Shared MCP endpoint for org
- [ ] Activity feed (who analyzed what)

### 6.3 Team Billing
- [ ] Per-seat billing for Team plan
- [ ] Org owner manages billing
- [ ] Seat add/remove proration

**Exit Criteria**:
- 3-person team can share a workspace
- Single MCP endpoint serves team context

**Critique Phase**:
- [ ] Permission model review
- [ ] Test with actual team (internal dogfooding)
- [ ] Edge cases: What if owner leaves?

---

## Phase 7: Polish & Scale (Weeks 23-26)
*Goal: Production hardening, growth optimization*

### 7.1 Reliability
- [ ] Uptime monitoring (Better Stack)
- [ ] Alerting for failures
- [ ] Automated recovery for stuck jobs
- [ ] Database backups

### 7.2 Performance
- [ ] CDN for dashboard assets
- [ ] Database query optimization
- [ ] Caching layer for frequent queries
- [ ] Background job prioritization (paid users first)

### 7.3 Growth Features
- [ ] Referral program (1 month free for referrals)
- [ ] Public repo showcase (opt-in)
- [ ] "Powered by Autodoc" badge
- [ ] GitHub marketplace listing

### 7.4 Analytics
- [ ] Product analytics (PostHog/Mixpanel)
- [ ] Funnel: Signup → Connect → Analyze → MCP → Upgrade
- [ ] Cohort retention analysis
- [ ] Feature usage tracking

**Exit Criteria**:
- 99.5% uptime over 2 weeks
- Clear understanding of conversion funnel
- Automated operations (minimal manual intervention)

---

## Technical Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Supabase (Postgres) | Auth + DB + Realtime in one, generous free tier |
| Storage | Cloudflare R2 | Cheap, S3-compatible, no egress fees |
| Hosting | Vercel (dashboard) + Cloud Run (API) | Already using Cloud Run, Vercel is fast for Next.js |
| Queue | Redis + BullMQ | Simple, proven, good observability |
| Payments | Stripe | Industry standard, great docs |
| Auth | NextAuth.js + GitHub | Users already have GitHub accounts |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Low conversion rate | Medium | High | Validate with waitlist, offer generous free tier |
| GitHub API rate limits | Medium | Medium | Cache aggressively, use GitHub App tokens |
| LLM costs for enrichment | Medium | Medium | Batch processing, use cheaper models for Pro |
| Competitor launches similar | Medium | Low | Move fast, focus on MCP differentiation |
| Security breach | Low | Critical | Security audit Phase 1, SOC2 later |

---

## Success Metrics by Phase

| Phase | Key Metric | Target |
|-------|------------|--------|
| 0 | Waitlist signups | 50 |
| 1 | Repos analyzed (internal) | 10 |
| 2 | Beta users onboarded | 20 |
| 3 | Action installs | 50 |
| 4 | Daily MCP queries | 100 |
| 5 | Paying customers | 50 |
| 6 | Team accounts | 10 |
| 7 | MRR | $5,000 |

---

## Open Questions

1. **Enrichment costs**: Should enrichment be a separate metered feature, or included in plans?
2. **Self-hosted enterprise**: Do we offer a self-hosted version for enterprises?
3. **Public repo analysis**: Should we pre-analyze popular OSS repos as a showcase?
4. **Privacy**: How do we handle code that users might not want processed by LLMs?

---

## Appendix: Open Source vs Cloud

| Feature | Open Source (Free) | Cloud (Paid) |
|---------|-------------------|--------------|
| Local analysis | Yes | Yes |
| Local dashboard | Yes | Yes |
| Hosted dashboard | No | Yes |
| GitHub integration | Manual | Automatic |
| MCP endpoint | Self-hosted | Managed |
| Multi-repo | Manual setup | One-click |
| Team sharing | DIY | Built-in |
| Enrichment | Bring your own API key | Included (metered) |

This ensures the open-source project remains valuable while Cloud adds convenience and collaboration that justify the subscription.
