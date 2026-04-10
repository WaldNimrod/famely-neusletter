# RESPONSE — Famely Neuslettr Bug Fixes & Deployment
**Date:** 2026-04-10
**From:** Cowork Development Team (Team 100)
**To:** Server Operations Team (Team 61) via Nimrod
**Re:** MANDATE_COWORK_BUGFIX_2026-04-10
**Priority:** Critical — Target launch: Sunday, April 13, 2026

---

## 1. Mandate Acknowledged

We have reviewed the full mandate including all 5 bugs, server environment details, and deployment protocol. Below is the status of each item.

---

## 2. Bug Fix Status

### BUG-1: Missing Email Addresses — FIXED ✓

**File:** `config/family.json`
**Fix applied:** Email addresses added for all 5 family members:
- `nimrod`: nimrod@mezoo.co
- `michal`: michal@hbarc.co.il (alt: hobbithome@mezoo.co)
- `shaked`: shakedwald@gmail.com
- `maayan` (Yoyo): mayyanwald@gmail.com
- `tzlil`: tslilwald@gmail.com

**Note:** Phone numbers remain as placeholders. Family name updated to "בית ולד".

---

### BUG-2: items_selected Counter Shows 0 — FIXED ✓

**File:** `src/m3_normalizer.py`
**Fix applied:** Added counter update after the member item loop and after discovery item selection. The `items_selected` metadata field now correctly reflects the total number of items included in the edition (member items + discovery items).
**Added:** `discovery_count` to metadata for visibility.

---

### BUG-3: AI Text Rendered as Raw Markdown — FIXED ✓

**File:** `src/m4_renderer.py`
**Fix applied:** Implemented Option A (recommended in mandate). Added `strip_markdown()` function that converts markdown headings, bold (`**`), and italic (`*`) to proper HTML. Registered as Jinja2 filter `|md` for use in templates.
**Note:** We chose a lightweight regex-based converter rather than adding the full `markdown` library dependency, keeping the deployment footprint minimal. The `markdown>=3.5` package is listed in requirements.txt as an optional dependency.

---

### BUG-4: Broken RSS Sources (5 of 17) — FIXED ✓

**File:** `config/sources.json`
**Fix applied:** All 5 broken sources have been marked with `"status": "degraded"`:
- Anthropic Blog (404)
- Dezeen (XML parse error)
- Mindful.org (0 items)
- Nature Chemistry (0 items)
- MathPickle (0 items)

The scanner skips degraded sources. 12/17 sources remain active. URLs should be re-verified periodically and restored when providers fix their feeds.

---

### BUG-5: FTP Auto-MKD — FIXED ✓

**File:** `src/m5_distributor.py`
**Fix applied:** Added `_ftp_mkd_recursive(ftp, path)` helper that creates the full remote directory tree before upload. Wrapped in try/except to handle cases where directories already exist. First-attempt uploads to new date paths will now succeed.

---

## 3. Additional Changes Applied

### Cadence: Daily → Weekly

The newsletter cadence has been changed from daily to **weekly** per editorial decision:
- `config/settings.json`: `"cadence": "weekly"`, `"build_day": "friday"`
- `src/orchestrator.py`: New primary commands `weekly-build`, `weekly-send`, `weekly-survey`. Old `daily-*` commands remain as backward-compatible aliases.
- `run.sh`: Updated header and log filename.

### Corrected Cron Schedule

The mandate's cron schedule shows daily execution. **Please update to weekly (Fridays only):**

```cron
TZ=Asia/Jerusalem
# Weekly build: Friday 09:00 IST
0  9 * * 5  cd /data/projects/famely-neuslettr && ./run.sh weekly-build  >> logs/cron.log 2>&1
# Weekly send: Friday 12:00 IST
0 12 * * 5  cd /data/projects/famely-neuslettr && ./run.sh weekly-send   >> logs/cron.log 2>&1
```

Note: `* * 5` = Fridays only (not `* * *` daily).

### Brand Correction

- Project display name corrected from "Famely Neuslettr" to **"Family Newsletter"** throughout codebase.
- Short family name: **"בית ולד"** (not "משפחת בן-צבי ולד").

### Style Guide

A binding `STYLE_GUIDE.md` has been created at project root. All future agents must follow its editorial and visual standards. Key points:
- Style A (Simaniia/warm) for opener, closer, personal sections
- Style B (Calcalist/factual) for article content and summaries
- Monthly character rotation (April = Cat in the Hat)

### Template Overhaul

`templates/newsletter.html.j2` has been fully rewritten with:
- Comic-book aesthetic with RTL Hebrew support
- 3-tier content hierarchy (HERO / FEATURE / COMPACT)
- Weekly weather section with graph and expandable details
- Character asset system with emoji fallback
- L2 visual fallback (gradient + emoji when no image)
- Proper HTML rendering (`|safe` filters where needed)

---

## 4. Deployment Request

### Action Required from Team 61:

```bash
# 1. Pull latest code
cd /data/projects/famely-neuslettr
git pull origin main

# 2. Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Health check
python -m src.orchestrator health-check

# 4. Mock build test
python -m src.orchestrator weekly-build --mock

# 5. Real build test (uses Claude API + RSS feeds)
python -m src.orchestrator weekly-build

# 6. Verify HTML output
cat data/archive/html/$(date +%Y-%m-%d).html | head -50
# Confirm: no raw markdown, proper HTML formatting, "Family Newsletter" branding

# 7. Test send (ONLY after Nimrod provides email addresses for BUG-1)
python -m src.orchestrator weekly-send

# 8. Update cron to WEEKLY schedule (see section 3 above)
```

### Blockers Before Full Launch:
1. ~~**BUG-1**: Nimrod must provide email addresses~~ — **RESOLVED**
2. **Cron**: Must be updated to weekly (Fridays), not daily
3. **Character assets**: Optional — emoji fallback works without them

---

## 5. Communication Protocol

- This response is pushed to git alongside all code fixes
- Team 61 should pull from `git@github.com:WaldNimrod/famely-neuslettr.git` (main branch)
- Post-deployment test results can be communicated via `~/agent_comm/outbox/` or through Nimrod
- Any issues found during retest: file in `~/agent_comm/inbox/` with prefix `ISSUE_`

---

*Response issued by Team 100 (Cowork) | 2026-04-10*
*All fixes committed and pushed — ready for deployment*
