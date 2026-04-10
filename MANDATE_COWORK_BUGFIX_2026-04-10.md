# MANDATE — Famely Neuslettr Bug Fixes & Server Deployment Prep
**Date:** 2026-04-10
**From:** Team 100 (Architecture) via Nimrod
**To:** Cowork Development Team
**Priority:** Critical — Target launch: Sunday, April 13, 2026
**Type:** Bug Fix + Server Integration

---

## 1. Project Status

Famely Neuslettr is deployed on **waldhomeserver** and can build newsletters successfully. However, several bugs prevent email distribution, which blocks the launch.

The project was tested end-to-end on the server with real RSS feeds and Claude API. Core pipeline works: scan (139 items) → normalize → render (10.9KB HTML) → but distribution fails.

---

## 2. Bugs To Fix (ordered by priority)

### BUG-1: Missing Email Addresses in family.json [BLOCKER]

**File:** `config/family.json`
**Issue:** All 5 family members have `"email": null` and placeholder phone numbers (`+972_NIMROD_PHONE`).
**Impact:** Email distribution (M5) fails completely. No newsletters can be sent.

**Fix:** Nimrod must provide real email addresses. Update each member:
```json
{
  "name": "...",
  "email": "real@email.com",
  "phone": "+972XXXXXXXXX"
}
```

**Note:** This requires Nimrod's input — the development team cannot guess contact info.

---

### BUG-2: items_selected Counter Shows 0 [MEDIUM]

**File:** `src/m3_normalizer.py`
**Issue:** Build log and DB show `items_selected: 0` but the HTML contains real curated content. The NEO (Newsletter Edition Object) counter is not being updated after item selection.
**Expected:** Counter should reflect the actual number of items included in the edition.

**Fix:** In M3, after selecting/scoring items, update the `items_selected` field on the NEO before returning.

---

### BUG-3: AI Text Rendered as Raw Markdown [MEDIUM]

**File:** `src/m4_renderer.py` and/or `templates/newsletter.html.j2`
**Issue:** Claude API returns markdown formatting (`# שלום`, `**bold**`). The renderer inserts this as-is into HTML, so headings and bold text appear as raw markdown characters.
**Expected:** Markdown should be converted to HTML before insertion.

**Fix options:**
- A) Add `markdown` library: `pip install markdown` + `markdown.markdown(text)` before inserting into template
- B) Add a Jinja2 filter: `{{ greeting | markdown }}` 
- C) Instruct Claude API to return HTML instead of markdown in the prompt

**Recommended:** Option A — cleanest separation of concerns.

---

### BUG-4: Broken RSS Sources (5 of 17) [LOW]

**File:** `config/sources.json`
**Issue:** 5 sources fail to scan:
| Source | Error |
|--------|-------|
| Anthropic Blog | 404 — URL may have changed |
| Dezeen | XML parse error |
| Mindful.org | 0 items returned |
| Nature Chemistry | 0 items returned |
| MathPickle | 0 items returned |

**Fix:** Update or remove broken URLs. 12/17 sources still work — not blocking.

---

### BUG-5: FTP Auto-MKD [LOW]

**File:** `src/m5_distributor.py`
**Issue:** FTP upload fails on first attempt to a new date path because the remote directory doesn't exist.
**Fix:** Add `ftp.mkd(remote_dir)` (wrapped in try/except) before upload.

---

## 3. Server Environment

### Connection Details
| Key | Value |
|-----|-------|
| Hostname | waldhomeserver |
| OS | Ubuntu 24.04.4 LTS |
| IP (LAN) | 10.100.102.2 |
| IP (Tailscale) | 100.125.98.56 |
| User | nimrodw |
| Project path | /data/projects/famely-neuslettr |
| Python venv | /data/projects/famely-neuslettr/venv |
| Git remote | git@github.com:WaldNimrod/famely-neuslettr.git |

### What's Already Configured on Server
- Python 3.12.3 + venv + all requirements installed
- `.env` configured with:
  - `ANTHROPIC_API_KEY` — working ($0.03/build)
  - `FTP_HOST` = ftp.s887.upress.link (tested, uploads work)
  - `SMTP_HOST` = smtp.inbox.co.il:587 (authenticated)
  - `SMTP_USER` = agent@nimrod.bio
- Git: cloned, main branch, commit 9365c10
- Data dirs created: `data/submissions/`, `data/archive/`, `logs/`

### Server Agent (Team 61)
The server has a Claude Code agent for operations. After pushing fixes:

**Deployment:**
```bash
ssh nimrodw@100.125.98.56
cd /data/projects/famely-neuslettr
git pull
source venv/bin/activate
pip install -r requirements.txt  # if new deps added

# Test build
python -m src.orchestrator daily-build

# Test send (after email addresses are configured)
python -m src.orchestrator daily-send
```

**Or communicate via agent_comm protocol:**
- Place message file in server's `~/agent_comm/inbox/`
- Server agent will execute and respond to `~/agent_comm/outbox/`

### Cron Schedule (to be enabled after all bugs fixed)
```cron
TZ=Asia/Jerusalem
0  9 * * *  cd /data/projects/famely-neuslettr && ./run.sh daily-build  >> logs/cron.log 2>&1
0 12 * * *  cd /data/projects/famely-neuslettr && ./run.sh daily-send   >> logs/cron.log 2>&1
```

---

## 4. Testing Protocol

After fixing bugs, test in this order:

```bash
# 1. Health check
python -m src.orchestrator health-check

# 2. Mock build (no external calls)
python -m src.orchestrator daily-build --mock

# 3. Real build (real RSS + Claude API)
python -m src.orchestrator daily-build

# 4. Verify HTML
cat data/archive/html/$(date +%Y-%m-%d).html | head -30
# Check: no raw markdown, proper HTML formatting

# 5. Test email (after BUG-1 fix)
python -m src.orchestrator daily-send
# Check: emails received by family members
```

---

## 5. Definition of Done

- [ ] BUG-1: Real email addresses in family.json (Nimrod provides)
- [ ] BUG-2: items_selected counter accurate
- [ ] BUG-3: AI text renders as HTML, not raw markdown
- [ ] BUG-4: Broken sources updated or removed
- [ ] BUG-5: FTP auto-creates directories
- [ ] All fixes pushed to GitHub
- [ ] Server updated: `git pull` + test build + test send
- [ ] Cron enabled on server
- [ ] First real newsletter: **Sunday, April 13, 2026, 09:00 IST**

---

## 6. Files Reference

| File | Purpose |
|------|---------|
| `config/family.json` | Family member profiles + contact info |
| `config/sources.json` | RSS/web source URLs |
| `src/m3_normalizer.py` | Scoring + item selection (BUG-2) |
| `src/m4_renderer.py` | HTML rendering (BUG-3) |
| `src/m5_distributor.py` | FTP + email (BUG-5) |
| `templates/newsletter.html.j2` | HTML template |
| `.env` | Secrets (on server only, never in git) |
| `SERVER_SETUP_PROMPT.md` | Full server deployment guide |

---

*Mandate issued by Team 100 via Nimrod | 2026-04-10*
*Target: Launch Sunday April 13, 2026*
