# MANDATE — Famely Neuslettr: Post-Test Bug Fixes + /agents/ Migration
**Date:** 2026-04-10 (v2 — supersedes MANDATE_COWORK_BUGFIX_2026-04-10.md)
**From:** Team 100 (Architecture) via Nimrod
**To:** Cowork Development Team
**Priority:** Critical — Target launch: Sunday, April 13, 2026
**Type:** Bug Fix + FTP Path Change

---

## 1. Good News

The server test flight was successful:
- **5/5 family emails delivered**
- Build: 92 items fetched, 10 selected, 34KB HTML, $0.049 token cost
- Claude API, SMTP, and FTP all working

---

## 2. Remaining Bugs (from server test flight)

### BUG-1: DISTRIBUTION FAILED status despite emails sent [HIGH]

**Module:** `src/m5_distributor.py`
**Issue:** Log shows "DISTRIBUTION FAILED" even though all 5 emails were sent. The status logic likely counts FTP failure (which is a separate issue) as overall failure.
**Fix:** Separate email success from FTP success in the status reporting. If all emails sent OK, email distribution = success regardless of FTP.

### BUG-2: FTP Path — Migrate to /agents/newsletter/ [CRITICAL]

**Architecture decision by Nimrod:** All projects upload to `/agents/` directory on nimrod.bio.

**Current:** FTP uploads to `/newsletter/` (blocked by WordPress 404)
**New:** Upload to `/agents/newsletter/`

**Canonical public URL (MUST be used in all editions):**
```
https://www.nimrod.bio/agents/newsletter/YYYY-MM-DD/index.html
```

**Verified working example:**
```
https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html → HTTP 200, 37KB
```

**CRITICAL LESSON:** The first test flight uploaded to `/newsletter/` (old path) which returned 404 because WordPress intercepted it. The `.htaccess` with `RewriteEngine Off` ONLY exists in `/agents/`. Any path outside `/agents/` will be blocked by WordPress.

**Requirement:** The canonical URL path `/agents/newsletter/YYYY-MM-DD/index.html` MUST be hardcoded or derived from `WP_FTP_ROOT` env var. It must NEVER be assembled from a different base path. Every edition, every email link, every log entry must use this exact pattern.

**New environment variables (already configured on server .env):**
```
WP_FTP_HOST=ftp.s887.upress.link
WP_FTP_USER=AgentsRoot@nimrod.bio
WP_FTP_PASS=<configured on server, not in git>
WP_FTP_ROOT=/agents/newsletter/
```

**Code changes required:**
1. Update M5 distributor to use `WP_FTP_*` vars for FTP connection
2. Upload path: `{WP_FTP_ROOT}/YYYY-MM-DD/index.html`
3. Public URL in emails: `https://www.nimrod.bio/agents/newsletter/YYYY-MM-DD/index.html`
4. **FTP TLS session reuse required** — standard `FTP_TLS` fails with `425`. Must use session reuse (see BUG-4 fix below or server team's working implementation)

**Validation after each build:** After FTP upload, verify with HTTP GET that the URL returns 200. Log the result. If 404 — the path is wrong.

### BUG-3: Greeting still raw markdown [MEDIUM]

**Module:** `src/m4_renderer.py`
**Issue:** AI-generated greetings still show `# שלום` and `**bold**` as raw text.
**Fix:** Convert markdown to HTML before template insertion. `markdown` package is already in requirements.

### BUG-4: FTP auto-MKD [LOW]

**Module:** `src/m5_distributor.py`
**Issue:** FTP fails on first upload to new date directory.
**Fix:** Add `ftp.mkd()` with try/except before upload.

### BUG-5: 5 broken RSS sources [LOW]

**File:** `config/sources.json`
**Fix:** Update or remove: Anthropic Blog (404), Dezeen (XML error), Mindful.org, Nature Chemistry, MathPickle (all 0 items).

---

## 3. Server Environment

| Key | Value |
|-----|-------|
| Hostname | waldhomeserver |
| IP (Tailscale) | 100.125.98.56 |
| User | nimrodw |
| Project path | /data/projects/famely-neusletter |
| Python venv | /data/projects/famely-neusletter/venv |
| Git remote | git@github.com:WaldNimrod/famely-neuslettr.git |

**Installed & working:** Python 3.12, Claude API ($0.049/build), SMTP (agent@nimrod.bio), FTP (ftp.s887.upress.link)

---

## 4. How to Deploy & Test on Server

After pushing fixes to GitHub, communicate with the server agent:

### Write a deploy message:
```bash
cat > /tmp/deploy-msg.md << 'EOF'
# Agent Communication Message
---
id: MSG-YYYYMMDD-NNN
from: mac
to: server
date: YYYY-MM-DD HH:MM
type: task
priority: high
expects_response: true
---

## Subject
Famely Neuslettr: Pull latest and test

## Body
1. cd /data/projects/famely-neusletter && git pull
2. source venv/bin/activate && pip install -r requirements.txt
3. python -m src.orchestrator daily-build
4. python -m src.orchestrator daily-send
5. Verify: emails received + FTP upload to /agents/newsletter/ successful
6. Check: https://www.nimrod.bio/agents/newsletter/YYYY-MM-DD/index.html returns 200
7. Report results
EOF

scp /tmp/deploy-msg.md nimrodw@10.100.102.2:~/agent_comm/inbox/
```

### Server Agent Protocol
- **Inbox:** `nimrodw@10.100.102.2:~/agent_comm/inbox/` — push via SCP
- **Outbox:** `nimrodw@10.100.102.2:~/agent_comm/outbox/` — pull via SCP
- **Command on server:** `/mail` to check inbox
- **Format:** MSG-YYYYMMDD-NNN.md with YAML frontmatter

---

## 5. Definition of Done

- [ ] BUG-1: Distribution status reflects email success correctly
- [ ] BUG-2: FTP uploads to `/agents/newsletter/` path
- [ ] BUG-3: Markdown converted to HTML in greetings
- [ ] BUG-4: FTP auto-creates directories
- [ ] BUG-5: Broken sources updated/removed
- [ ] All fixes pushed to GitHub
- [ ] Server agent confirms: build + send + FTP all working
- [ ] Public URL `nimrod.bio/agents/newsletter/YYYY-MM-DD/index.html` returns 200
- [ ] **Cron enabled on server** (after all above confirmed)
- [ ] **First live newsletter: Sunday, April 13, 2026, 09:00 IST**

---

---

## 6. Reporting Back to Server Team

After pushing fixes, the server team (Team 61) needs to pull and test. You can communicate directly:

**Method:** Write a message file and push via SCP:
```bash
# Create message
cat > /tmp/MSG-famely-deploy.md << 'EOF'
# Agent Communication Message
---
id: MSG-YYYYMMDD-NNN
from: mac
to: server
type: task
priority: high
expects_response: true
---

## Subject
Famely Neuslettr: Pull latest and full test

## Body
Fixes pushed. Please:
1. cd /data/projects/famely-neusletter && git pull
2. source venv/bin/activate && pip install -r requirements.txt
3. python -m src.orchestrator health-check
4. python -m src.orchestrator daily-build
5. python -m src.orchestrator daily-send
6. Verify: curl -s -o /dev/null -w "%{http_code}" https://www.nimrod.bio/agents/newsletter/$(date +%Y-%m-%d)/index.html
7. Report: email delivery status + FTP upload status + public URL status
EOF

# Push to server
scp /tmp/MSG-famely-deploy.md nimrodw@10.100.102.2:~/agent_comm/inbox/
```

**Or tell Nimrod** and he will relay to the server agent via `/send`.

The server agent checks inbox with `/mail` and will execute + report back.

---

*Mandate v2.1 issued by Team 100 via Nimrod | 2026-04-10*
*Supersedes: MANDATE_COWORK_BUGFIX_2026-04-10.md*
