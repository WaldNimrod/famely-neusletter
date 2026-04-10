# MANDATE — Full E2E Pilot Build & Distribution
**Date:** 2026-04-10
**From:** Team 100 (Cowork) via Nimrod (Team 00)
**To:** Team 61 (Server Claude)
**Priority:** CRITICAL — Execute immediately upon receipt
**Version:** v3.0.0 (tag after successful pilot)

---

## 1. Objective

Pull the latest code from git and execute a **full real build** (NOT `--mock`) of the Family Newsletter. Then validate every piece of content and every link in the generated HTML. If all checks pass, distribute a **pilot edition** to all 5 family members via email.

This is the first real edition. It must be perfect.

---

## 2. Pre-Flight: Pull & Install

```bash
cd /data/projects/famely-neuslettr
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

### Verify environment:
```bash
# These must all be set and non-empty:
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+SET}"
echo "UPRESS_SFTP_HOST: ${UPRESS_SFTP_HOST:+SET}"
echo "EMAIL_SMTP_HOST: ${EMAIL_SMTP_HOST:+SET}"
echo "EMAIL_PASSWORD: ${EMAIL_PASSWORD:+SET}"
```

If `ANTHROPIC_API_KEY` is not set, the build will fail. Set it in `.env` before proceeding.

---

## 3. Execute Real Build

```bash
python -m src.orchestrator weekly-build
```

**This will:**
- M1: Load 5 member profiles from `config/family.json`
- M2: Fetch REAL content from 15+ active RSS/web/YouTube sources
- M3: Score, curate, and generate all AI content via Claude API:
  - Opener (warm intro paragraph in Hebrew — Style A)
  - Personalized headlines + summaries per member
  - Math puzzle for צליל
  - "Today in history" fact
  - Discovery bridges (cross-member recommendations)
  - Survey question
  - Closer (warm sign-off in Hebrew — Style A)
  - Weather forecast (Open-Meteo API — Pardes Hanna + Basel)
- M4: Render HTML via Jinja2 template

**Expected output:** `data/archive/html/YYYY-MM-DD.html` (should be 25-45KB)

---

## 4. E2E Content Validation

After build completes, run these checks **before distributing**:

### 4.1 — Basic HTML validation
```bash
HTML_FILE="data/archive/html/$(date +%Y-%m-%d).html"
echo "File size: $(wc -c < $HTML_FILE) bytes"
# Must be > 10000 bytes. If smaller, build failed.
```

### 4.2 — Check for placeholder/mock content
```bash
# NONE of these should appear in real build output:
grep -c 'example\.com' "$HTML_FILE"          # should be 0
grep -c 'lorem ipsum' "$HTML_FILE"            # should be 0
grep -c 'placeholder' "$HTML_FILE"            # should be 0
grep -c 'TODO' "$HTML_FILE"                   # should be 0
grep -c 'MOCK' "$HTML_FILE"                   # should be 0
```

If any count > 0, the build used mock data. Re-run without `--mock` flag.

### 4.3 — Check all sections are populated
```bash
# These sections MUST exist in the HTML:
grep -c 'opener' "$HTML_FILE"                 # opener section
grep -c 'weather-section' "$HTML_FILE"        # weather forecast
grep -c 'closer' "$HTML_FILE"                 # closer section
grep -c 'hero-panel' "$HTML_FILE"             # at least 1 hero article
grep -c 'feat-panel' "$HTML_FILE"             # at least 2 feature articles
grep -c 'puzzle' "$HTML_FILE"                 # math puzzle for Tzlil
grep -c 'survey' "$HTML_FILE"                 # survey section
```

### 4.4 — Validate all article URLs
```bash
# Extract all href URLs from the HTML and test each one:
python3 -c "
import re, requests, sys
html = open('$HTML_FILE').read()
urls = set(re.findall(r'href=\"(https?://[^\"]+)\"', html))
broken = []
for url in urls:
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code >= 400:
            broken.append(f'{r.status_code} {url}')
    except Exception as e:
        broken.append(f'ERROR {url}: {e}')
if broken:
    print('BROKEN LINKS FOUND:')
    for b in broken:
        print(f'  {b}')
    sys.exit(1)
else:
    print(f'All {len(urls)} links OK')
"
```

**If broken links are found:** These are from real RSS sources that may have changed. Acceptable if ≤2 broken links. If more, investigate.

### 4.5 — Validate weather data
```bash
# Weather section should contain real temperature numbers:
grep -oP '\d+°' "$HTML_FILE" | head -5
# Should show real temperatures (15-40 range for Israel, 5-25 for Basel)
```

### 4.6 — Visual inspection
Open the HTML in a browser and verify:
- Hebrew text renders correctly (RTL)
- Weather graph bars display with real temperatures
- Opener paragraph is warm, personal Hebrew text (not raw markdown)
- Member sections have real article headlines (not "Title here" or similar)
- Closer paragraph is warm sign-off
- Images load (or fallback gradients display for L2)
- Footer shows "Family Newsletter" branding

---

## 5. FTP Upload & Distribution

Only proceed if ALL checks in Section 4 pass.

### 5.1 — Upload to FTP and send emails
```bash
python -m src.orchestrator weekly-send
```

This will:
1. Upload HTML to `ftp.s887.upress.link` → public URL on nimrod.bio
2. Send personalized email to each family member:
   - nimrod@mezoo.co
   - michal@hbarc.co.il
   - shakedwald@gmail.com
   - mayyanwald@gmail.com
   - tslilwald@gmail.com

### 5.2 — Verify public URL
```bash
curl -s -o /dev/null -w "%{http_code}" "https://www.nimrod.bio/agents/newsletter/$(date +%Y-%m-%d)/index.html"
# Should return 200
```

---

## 6. Post-Distribution Checks

```bash
# Check distribution results in logs:
tail -50 logs/newsletter-$(date +%Y-%m-%d).log | grep -E '\[M5\]'
# Should show: FTP upload success + email sent to each member
```

### Success criteria:
- [ ] HTML > 10KB with real content (no placeholders)
- [ ] 0 broken links (or ≤2 acceptable)
- [ ] Weather section shows real temperatures for Pardes Hanna + Basel
- [ ] Opener + Closer paragraphs are real Hebrew editorial text
- [ ] All 5 member sections populated with real articles
- [ ] Math puzzle exists and is non-trivial
- [ ] FTP upload returned 200
- [ ] All 5 emails sent successfully

---

## 7. Cron Schedule Update

After successful pilot, update cron to weekly schedule:

```cron
TZ=Asia/Jerusalem
# Weekly build: Friday 09:00 IST
0  9 * * 5  cd /data/projects/famely-neuslettr && ./run.sh weekly-build  >> logs/cron.log 2>&1
# Weekly send: Friday 12:00 IST
0 12 * * 5  cd /data/projects/famely-neuslettr && ./run.sh weekly-send   >> logs/cron.log 2>&1
```

**NOTE:** Day `5` = Friday. Not `*` (daily).

---

## 8. Report Back

After completing this mandate, write a response file to:
```
~/agent_comm/outbox/REPORT_PILOT_E2E_$(date +%Y-%m-%d).md
```

Include:
- Build success/failure
- Number of articles fetched + selected
- Weather data status
- Link validation results (broken count)
- Distribution results per member
- Any errors encountered
- Public URL of published edition

---

## 9. Known Issues & Notes

1. **Character assets (PNG):** Not yet created. Emoji fallback is active and working. This is expected for the pilot.

2. **Phone numbers:** Still placeholders in family.json. WhatsApp will fall back to email. This is fine for the pilot.

3. **Degraded RSS sources (7 of 22):** Some sources are marked degraded and will be skipped. The remaining 15 should provide enough content. If M2 returns 0 items from ALL sources, there may be a network issue — check server connectivity.

4. **Open-Meteo weather API:** Free, no key required. If blocked by firewall, weather section will gracefully not render (the newsletter still works without it).

5. **Claude API tokens:** Expected cost per build: ~$0.15-$0.30. Weekly alert threshold: $1.00.

6. **Style guide:** All AI-generated text follows the binding STYLE_GUIDE.md at project root. Style A (Simaniia/warm) for opener/closer, Style B (Calcalist/factual) for article summaries.

---

*Mandate issued by Team 100 (Cowork) — approved by Team 00 (Nimrod)*
*Execute upon receipt. Report results via ~/agent_comm/outbox/*
