# Famely Neuslettr — Roadmap & Version Plan

## Version History

| Version | Name | Status | Date | Description |
|---------|------|--------|------|-------------|
| v0.1.0 | POC | Done | 2026-04-08 | Proof of concept, single-file pipeline |
| v1.0.0 | Phase 1 Core | **Current** | 2026-04-09 | Full modular pipeline, mock mode, local dev |
| v1.1.0 | Phase 1 Live | **Next** | 2026-04-13 (Sun) | First real newsletter — home server + FTP + email |
| v1.2.0 | Phase 1 WhatsApp | Planned | TBD | WhatsApp distribution via Twilio |
| v1.3.0 | Phase 1 Feedback | Planned | TBD | Webhook live, submissions + survey active |
| v2.0.0 | Phase 2 Dashboard | LOD100 | TBD | Web dashboard on home server |
| v2.1.0 | Phase 2 Analytics | LOD100 | TBD | Reading patterns, auto-learning |
| v3.0.0 | Phase 3 Managed | LOD100 | TBD | Migration to Claude Managed Agents |

---

## v1.0.0 — Phase 1 Core (CURRENT)

**Status:** Built, tested in mock mode, ready for deployment.

**Modules:**
- M1 Profiles: Config loader (family.json, sources.json, settings.json)
- M2 Scanner: RSS (xml.etree), web (BS4), YouTube RSS
- M3 Normalizer: Dedup → score → curate → AI generate → build NEO → archive
- M4 Renderer: Jinja2 → HTML (Style 4 light clean, mobile-first)
- M5 Distributor: FTP upload + WhatsApp/Email send + survey
- M6 Feedback: Webhook (stdlib http.server) for submissions + survey
- Orchestrator: CLI (daily-build, daily-send, daily-survey, health-check)
- DB: SQLite with 7 tables + indexes
- Token Tracker: Wraps Claude API, logs usage + cost

**Acceptance:** Full mock pipeline passes. All LOD400 acceptance criteria met in mock mode.

---

## v1.1.0 — Phase 1 Live (TARGET: Sunday April 13)

**Goal:** First real newsletter sent to the family.

**Deployment checklist:**
1. Clone repo to home server
2. Create .env with real credentials (Anthropic, FTP, SMTP)
3. pip install requirements
4. Run health-check
5. Run daily-build (real RSS, real Claude API)
6. Verify HTML quality
7. Run daily-send (real FTP upload + email)
8. Set up cron for daily automation

**Distribution:** Email only (v1.1.0). WhatsApp deferred to v1.2.0.

**What's NOT in v1.1.0:**
- WhatsApp send (needs Twilio setup)
- Webhook server (needs port forwarding / tunnel)
- Survey send (needs WhatsApp or separate email flow)

---

## v1.2.0 — WhatsApp Integration

**Scope:** Add Twilio WhatsApp as primary channel.

**Tasks:**
- Register Twilio account + WhatsApp Business
- Configure message templates
- Test send flow
- Switch primary_channel to whatsapp in settings.json
- Add survey send via WhatsApp at 21:00

---

## v1.3.0 — Feedback Loop

**Scope:** Live webhook for family submissions + survey responses.

**Tasks:**
- Set up webhook on home server (port 8443)
- Configure ngrok / Cloudflare tunnel for Twilio callback
- Test submission flow end-to-end
- Test survey response collection
- Verify mandatory publish rule works

---

## v2.0.0 — Phase 2: Dashboard (LOD100)

**Intent:** Web-based dashboard for managing the newsletter system.

**Capabilities (LOD100 level):**
- View past editions and content
- Manage family profiles and sources
- Token usage and cost tracking charts
- Submission moderation queue
- Analytics: which content gets read/discussed
- Runs on home server (NOT nimrod.bio — static only)

**Technology:** FastAPI backend + simple frontend (React or HTML/HTMX).

**LOD progression:** LOD100 → LOD200 after v1.3.0 stabilizes.

---

## v3.0.0 — Phase 3: Claude Managed Agents Migration (LOD100)

**Intent:** Migrate the daily pipeline from home server to Claude Managed Agents infrastructure.

**Rationale:**
- Eliminates dependency on home server uptime
- Built-in web search replaces RSS scraping infrastructure
- Automatic error recovery + checkpointing
- Persistent sessions with audit trail
- Agent SDK simplifies orchestration code

**Architecture vision (LOD100):**
```
Current:  Home Server (cron) → Python pipeline → Claude API → FTP → WhatsApp
Future:   Scheduled Managed Agent → Built-in tools → FTP → WhatsApp
```

**What the Managed Agent would do:**
1. Web search for fresh content per family member interests
2. Score and curate using Claude's reasoning (no separate scoring code)
3. Generate summaries, headlines, puzzle, greeting in single session
4. Render HTML using code execution tool
5. FTP upload via bash tool (if outbound network allowed)
6. Send notifications via WhatsApp/email

**Key questions to resolve (LOD200):**
- Does Managed Agents support outbound network (FTP, SMTP, Twilio API)?
- Can we schedule Managed Agent runs on a cron-like schedule?
- What's the real cost vs home server? (estimated: ~$0.15/day = $4.50/month)
- How to handle webhook for incoming submissions? (separate always-on service?)
- Can MCP servers be attached for FTP/WhatsApp integration?

**Migration strategy:**
1. POC: Run daily-build as Managed Agent, compare output quality
2. Validate: Outbound network, FTP upload, cost analysis
3. Gradual: Move build → send → survey one at a time
4. Cutover: Decommission home server cron, keep webhook separate

**Estimated timeline:** After v2.0.0 stabilizes, ~Q3 2026.

**Cost projection:**
| Component | Home Server | Managed Agent |
|-----------|-------------|---------------|
| Runtime | $0 (own HW) | ~$0.01/day ($0.08/hr × ~8min) |
| Tokens | ~$0.10/day | ~$0.10/day (same) |
| Web search | N/A | ~$0.02/day (20 searches) |
| Total/month | ~$3 tokens | ~$4 tokens+runtime+search |

**Decision gate:** v3.0.0 moves to LOD200 only after successful POC proving outbound network support and cost alignment.

---

## Release Process

1. Every version gets a git tag: `v1.0.0`, `v1.1.0`, etc.
2. Each version has an LOD document if scope is complex (LOD200+ for v2.0.0, v3.0.0)
3. Deployment to home server = manual pull + restart
4. First newsletter target: **Sunday, April 13, 2026**
