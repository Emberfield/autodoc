# Autodoc Cloud: Launch Plan

## Philosophy: Sourcegraph Model

**Open Source = Full Product**
- All features work locally with zero restrictions
- Bring your own API keys for LLM enrichment
- Self-host dashboard, MCP server, everything
- No "crippled free tier" - this builds trust and adoption

**Cloud = Convenience + Collaboration**
- One-click GitHub integration (no CLI setup)
- Managed MCP endpoint (no self-hosting)
- Team sharing & permissions
- We handle the infrastructure

This is the Sourcegraph model: OSS gets you 100% of functionality, paid gets you "we run it for you."

---

## Target Launch: 6 Weeks to First Paying Customer

### Week 1-2: Auth + Database Foundation

**Goal**: User can sign in and see an empty dashboard

#### Day 1-3: AuthJoy Integration
```typescript
// dashboard/src/lib/auth.ts
import { AuthJoy } from '@authjoy/nextjs';

export const auth = new AuthJoy({
  providers: ['github'],
  callbacks: {
    onSignIn: async (user) => {
      // Upsert to Supabase
      await supabase.from('users').upsert({
        id: user.id,
        github_id: user.githubId,
        email: user.email,
        plan: 'free',
      });
    }
  }
});
```

#### Day 4-5: Supabase Setup
```sql
-- Core schema (minimal viable)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  github_id TEXT UNIQUE NOT NULL,
  email TEXT,
  plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'team')),
  stripe_customer_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE repositories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  github_repo TEXT NOT NULL, -- 'owner/repo'
  github_installation_id TEXT,
  status TEXT DEFAULT 'pending',
  last_analyzed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, github_repo)
);

CREATE TABLE analysis_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_id UUID REFERENCES repositories(id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL, -- 'cache', 'enrichment', 'features'
  storage_path TEXT NOT NULL, -- R2 path
  created_at TIMESTAMPTZ DEFAULT now()
);
```

#### Day 6-7: Dashboard Auth Flow
- [ ] Add AuthJoy provider to Next.js app
- [ ] Protected routes (redirect to login if not authed)
- [ ] User menu (avatar, plan badge, sign out)
- [ ] "Connect GitHub" button (placeholder)

**Deliverable**: Can sign in via GitHub, see empty "My Repositories" page

---

### Week 2-3: GitHub App + Repository Connection

**Goal**: User can connect a repo and trigger analysis

#### GitHub App Setup
1. Register GitHub App: `autodoc-cloud`
2. Permissions:
   - `contents: read` (clone repos)
   - `metadata: read` (list repos)
3. Webhook URL: `https://api.autodoc.tools/webhooks/github`
4. Callback URL: `https://app.autodoc.tools/api/github/callback`

#### Installation Flow
```typescript
// User clicks "Connect Repository"
// 1. Redirect to GitHub App installation
// 2. GitHub redirects back with installation_id
// 3. Store installation, fetch accessible repos
// 4. User selects repos to analyze
```

#### API Endpoints (Cloud Run)
```
POST /api/repos              - Add repository
GET  /api/repos              - List user's repos
POST /api/repos/:id/analyze  - Trigger analysis
GET  /api/repos/:id/status   - Analysis status
GET  /api/repos/:id/data     - Get analysis data (signed R2 URL)
```

**Deliverable**: User can connect GitHub, select repo, see it in dashboard

---

### Week 3-4: Analysis Pipeline

**Goal**: Connected repos get analyzed automatically

#### Worker Architecture
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  API Server  │────▶│    Redis     │────▶│   Worker     │
│ (Cloud Run)  │     │   (Upstash)  │     │ (Cloud Run)  │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                          ┌──────▼──────┐
                                          │     R2      │
                                          │  (Storage)  │
                                          └─────────────┘
```

#### Worker Job: `analyze_repo`
```python
async def analyze_repo(repo_id: str, github_repo: str, installation_id: str):
    # 1. Clone repo (using installation token)
    # 2. Run autodoc analyze
    # 3. Upload results to R2
    # 4. Update repository status in Supabase
```

#### Storage Structure (R2)
```
/{user_id}/{repo_id}/
  ├── autodoc_cache.json
  ├── autodoc_enrichment_cache.json (if enriched)
  └── features_cache.json (if detected)
```

**Deliverable**: Repo analysis runs in background, results stored in R2

---

### Week 4-5: Dashboard Data Display

**Goal**: Dashboard shows analysis results from cloud

#### Cloud Mode Detection
```typescript
// dashboard/src/lib/data.ts
export function loadDashboardData(repoId?: string) {
  if (typeof window !== 'undefined' && repoId) {
    // Cloud mode: fetch from API
    return fetchCloudData(repoId);
  }
  // Local mode: read from filesystem (existing code)
  return loadLocalData();
}
```

#### Repository Dashboard
- [ ] Repo selector dropdown (when user has multiple)
- [ ] Analysis status banner (analyzing, complete, failed)
- [ ] Re-analyze button
- [ ] Last analyzed timestamp
- [ ] All existing dashboard features work with cloud data

#### Quick Wins
- [ ] "Share" button (generates public read-only link)
- [ ] "Download" button (export analysis JSON)

**Deliverable**: Full dashboard works with cloud-stored data

---

### Week 5-6: MCP Endpoint + Billing

**Goal**: Users get personal MCP endpoint, can upgrade to Pro

#### Per-User MCP Endpoint
```
https://mcp.autodoc.tools/u/{user_id}
Authorization: Bearer {api_key}
```

Each user's MCP endpoint:
- Only sees their connected repos
- `search` searches across all their repos
- `pack_query` queries specific repo

#### API Key Management
```sql
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL, -- bcrypt hash
  name TEXT DEFAULT 'Default',
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Dashboard settings page:
- [ ] Generate API key
- [ ] Copy MCP endpoint URL
- [ ] Integration instructions (Claude, Cursor)

#### Stripe Billing (Minimal)
```typescript
// Products
const PRODUCTS = {
  pro: {
    price_id: 'price_xxx',
    limits: { private_repos: 5, public_repos: 10 }
  },
  team: {
    price_id: 'price_yyy',
    limits: { private_repos: 20, public_repos: 50, users: 5 }
  }
};

// Upgrade flow
// 1. User clicks "Upgrade to Pro"
// 2. Redirect to Stripe Checkout
// 3. Webhook updates user.plan in Supabase
// 4. User returns to dashboard with Pro badge
```

#### Plan Enforcement
```typescript
async function canAddRepo(userId: string, isPrivate: boolean) {
  const user = await getUser(userId);
  const repos = await getUserRepos(userId);
  const limits = PLAN_LIMITS[user.plan];

  const privateCount = repos.filter(r => r.is_private).length;
  const publicCount = repos.filter(r => !r.is_private).length;

  if (isPrivate && privateCount >= limits.private_repos) {
    return { allowed: false, reason: 'upgrade_required' };
  }
  // ...
}
```

**Deliverable**: Users can upgrade, get MCP endpoint, use with AI tools

---

## Launch Checklist

### Infrastructure
- [ ] Supabase project created
- [ ] Cloudflare R2 bucket created
- [ ] Redis (Upstash) provisioned
- [ ] Cloud Run worker deployed
- [ ] GitHub App registered
- [ ] Stripe account + products created
- [ ] Custom domains configured:
  - `app.autodoc.tools` → Dashboard (Vercel)
  - `api.autodoc.tools` → API (Cloud Run)
  - `mcp.autodoc.tools` → MCP Server (Cloud Run)

### AuthJoy Setup
- [ ] Create AuthJoy project for autodoc-cloud
- [ ] Configure GitHub OAuth provider
- [ ] Set up callback URLs
- [ ] Test sign-in flow

### Dashboard Updates
- [ ] AuthJoy integration
- [ ] Repository management UI
- [ ] Cloud data fetching
- [ ] Settings page (API keys, billing)
- [ ] Upgrade prompts

### Testing
- [ ] End-to-end: Sign up → Connect → Analyze → View → MCP
- [ ] Billing: Upgrade → Checkout → Plan updated
- [ ] Limits: Free user blocked at repo limit
- [ ] MCP: Claude can query user's repos

---

## Pricing (Final)

| Feature | Free | Pro ($8/mo) | Team ($29/mo) |
|---------|------|-------------|---------------|
| Public repos | 1 | 10 | 50 |
| Private repos | 0 | 5 | 20 |
| Users | 1 | 1 | 5 |
| Hosted dashboard | ✓ | ✓ | ✓ |
| Personal MCP endpoint | ✗ | ✓ | ✓ |
| Auto-analyze on push | ✗ | ✓ | ✓ |
| AI enrichment | ✗ | 500/mo | 2000/mo |
| Team workspace | ✗ | ✗ | ✓ |
| Priority support | ✗ | ✗ | ✓ |

**Note**: Free tier still valuable - hosted dashboard with 1 public repo. Enough to try, not enough for serious use.

---

## Open Source Parity

To ensure OSS remains fully functional:

| Feature | OSS (Local) | Cloud |
|---------|-------------|-------|
| Analyze codebase | `autodoc analyze` | GitHub integration |
| Search code | `autodoc search` | Dashboard + MCP |
| Enrich with AI | `autodoc enrich` (BYOK) | Included (metered) |
| Feature detection | `autodoc features detect` | Automatic |
| Dashboard | `cd dashboard && npm run dev` | app.autodoc.tools |
| MCP server | `autodoc mcp-server` | mcp.autodoc.tools/u/{id} |
| Multi-repo | Manual per-repo | One dashboard |
| Teams | N/A (single user) | Shared workspace |

The only things Cloud adds:
1. **Convenience** - No CLI, no self-hosting
2. **Collaboration** - Teams, sharing
3. **Integration** - GitHub webhooks, API keys

---

## Week-by-Week Milestones

| Week | Milestone | Success Metric |
|------|-----------|----------------|
| 1 | Auth working | Can sign in via GitHub |
| 2 | GitHub App live | Can install and select repos |
| 3 | Analysis pipeline | Repos analyzed in background |
| 4 | Dashboard cloud mode | View analysis in hosted dashboard |
| 5 | MCP endpoints | Claude can query via MCP |
| 6 | Billing live | First Pro subscription |

---

## Post-Launch (Weeks 7-12)

### Week 7-8: GitHub Action
- Publish `autodoc-ai/autodoc-action` to marketplace
- Users can trigger analysis from their CI
- Lower our infrastructure costs

### Week 9-10: Team Features
- Organization creation
- Member invites
- Shared MCP endpoint

### Week 11-12: Growth
- Referral program
- Public repo showcase
- Documentation + tutorials

---

## Cost Estimates (Monthly)

| Service | Free Tier | At 100 Users | At 1000 Users |
|---------|-----------|--------------|---------------|
| Supabase | $0 | $25 | $75 |
| Upstash Redis | $0 | $10 | $50 |
| Cloudflare R2 | $0 | $5 | $30 |
| Cloud Run | $0* | $50 | $200 |
| AuthJoy | ? | ? | ? |
| Stripe fees | 2.9%+30¢ | ~$25 | ~$250 |
| **Total** | ~$0 | ~$115 | ~$605 |

*Cloud Run free tier: 2M requests/month

At 100 Pro users ($800 MRR), costs are ~$115, margin is ~85%.
At 1000 Pro users ($8000 MRR), costs are ~$605, margin is ~92%.

---

## Action Items: Starting Tomorrow

1. **Create Supabase project** - 15 min
2. **Set up R2 bucket** - 10 min
3. **Register GitHub App** - 30 min
4. **Set up AuthJoy project** - 20 min
5. **Add auth to dashboard** - 2 hours
6. **Deploy API skeleton to Cloud Run** - 1 hour

First day target: Authenticated dashboard deployed to `app.autodoc.tools`
