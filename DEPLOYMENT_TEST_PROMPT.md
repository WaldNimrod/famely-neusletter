# Famely Neuslettr — Deployment Verification & Test Plan

> **Who you are:** You are Claude Code running on the home server via terminal.
> **Who sent this:** The architecture team (Claude Opus in Cowork) via Nimrod.
> **What this is:** A structured verification and test plan for the Famely Neuslettr deployment.
> **How to work:** Execute each phase in order. Report results in the exact format specified. STOP at gates marked 🚦 and report back before continuing.

---

## Context

Famely Neuslettr is an automated daily family newsletter system. It was built and tested in mock mode on the dev machine and has been deployed to this server via git. The system scans RSS/web/YouTube sources, generates AI summaries via Claude API, renders HTML, uploads to nimrod.bio via FTP, and sends notifications to 5 family members.

**Project location:** Should be at `/opt/famely-neuslettr/` or similar — you need to locate it.
**Version:** v1.0.0 (git tag)
**Target:** First real newsletter on Sunday, April 13, 2026.

---

## PHASE 1: Environment Reconnaissance

Run ALL of these commands and report the full output:

```bash
echo "=== SYSTEM ==="
uname -a
echo "---"
hostname
echo "---"
uptime

echo ""
echo "=== PYTHON ==="
python3 --version 2>&1
pip3 --version 2>&1
which python3

echo ""
echo "=== PROJECT LOCATION ==="
# Find the project
find / -name "orchestrator.py" -path "*/famely*" 2>/dev/null
find / -name "settings.json" -path "*/famely*" 2>/dev/null
ls -la /opt/famely-neuslettr/ 2>/dev/null || echo "NOT at /opt/famely-neuslettr"

echo ""
echo "=== GIT ==="
cd /opt/famely-neuslettr 2>/dev/null || cd $(find / -name "orchestrator.py" -path "*/famely*" -exec dirname {} \; 2>/dev/null | head -1)/..
git log --oneline -3
git status -s
git remote -v
git tag -l

echo ""
echo "=== VENV & PACKAGES ==="
ls -la venv/ 2>/dev/null || echo "No venv found"
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    pip list 2>/dev/null | grep -iE "jinja|request|beautifulsoup|dotenv|anthropic"
fi

echo ""
echo "=== ENV FILE ==="
ls -la .env 2>/dev/null || echo "NO .env FILE"
# Show which keys are set (values hidden)
if [ -f .env ]; then
    echo "Keys configured:"
    grep -v "^#" .env | grep -v "^$" | cut -d= -f1 | sort
fi

echo ""
echo "=== NETWORK ==="
# Test Claude API reachability
curl -s -o /dev/null -w "Claude API: HTTP %{http_code}\n" --max-time 10 https://api.anthropic.com/ 2>&1 || echo "Claude API: UNREACHABLE"

# Test RSS feed reachability
curl -s -o /dev/null -w "RSS (archdaily): HTTP %{http_code}\n" --max-time 10 https://www.archdaily.com/feed 2>&1 || echo "RSS: UNREACHABLE"

# Test FTP
curl -s -o /dev/null -w "FTP (upress): HTTP %{http_code}\n" --max-time 10 ftp://ftp.upress.co.il/ 2>&1 || echo "FTP: UNREACHABLE (may need credentials)"

# Test SMTP port
timeout 5 bash -c 'echo > /dev/tcp/smtp.gmail.com/465' 2>/dev/null && echo "SMTP (gmail 465): OPEN" || echo "SMTP (gmail 465): CLOSED/BLOCKED"

echo ""
echo "=== DISK ==="
df -h / | tail -1
du -sh data/ 2>/dev/null || echo "No data dir yet"

echo ""
echo "=== CRON ==="
crontab -l 2>/dev/null || echo "No crontab configured"

echo ""
echo "=== PORTS ==="
ss -tlnp 2>/dev/null | grep -E "8443|8080" || echo "Ports 8443/8080: free"
```

### 🚦 GATE 1 — Report back with full output before continuing

Format your report as:
```
PROJECT PATH: [path]
PYTHON: [version]
GIT VERSION: [tag/commit]
GIT REMOTE: [url or "none"]
VENV: [exists/missing]
PACKAGES: [all installed / missing: X, Y]
.ENV: [configured / missing / partial — list missing keys]
NETWORK:
  Claude API: [OK/BLOCKED]
  RSS feeds: [OK/BLOCKED]
  FTP: [OK/BLOCKED]
  SMTP: [OK/BLOCKED]
CRON: [configured/not configured]
BLOCKERS: [list anything that prevents testing]
```

---

## PHASE 2: Health Check + Mock Test

Only proceed here after Phase 1 is reported and confirmed.

```bash
cd [PROJECT_PATH]
source venv/bin/activate

echo "=== HEALTH CHECK ==="
python -m src.orchestrator health-check

echo ""
echo "=== MOCK BUILD ==="
# Delete any old test DB first
rm -f data/famely.db
python -m src.orchestrator daily-build --mock

echo ""
echo "=== MOCK BUILD RESULT ==="
ls -la data/archive/html/
python3 -c "
from src.db import Database
db = Database('data/famely.db')
nl = db.get_last_newsletter()
if nl:
    print(f'Date: {nl[\"date\"]}')
    print(f'Status: {nl[\"status\"]}')
    print(f'Items fetched: {nl[\"items_fetched\"]}')
    print(f'Items selected: {nl[\"items_selected\"]}')
    print(f'HTML path: {nl[\"html_path\"]}')
    cost = db.get_daily_cost(nl['date'])
    print(f'Token cost: \${cost:.4f}')
else:
    print('ERROR: No newsletter record found')
db.close()
"

echo ""
echo "=== MOCK SEND ==="
python -m src.orchestrator daily-send --mock
```

### Expected results:
- Health check: all ✓
- Mock build: 13 items fetched → 9 selected, HTML ~13KB, $0.0170 mock cost
- Mock send: 5 members sent via mock channel

### 🚦 GATE 2 — Report mock test results before continuing to real tests

---

## PHASE 3: Real RSS Scan Test (no AI, no send)

This tests that the scanner can actually reach RSS feeds and fetch content.

```bash
cd [PROJECT_PATH]
source venv/bin/activate

echo "=== REAL RSS SCAN ==="
rm -f data/famely.db
python3 -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

from src.m1_profiles import load_profiles, load_sources, load_settings, get_scan_rules
from src.m2_scanner import scan_all

family = load_profiles('config/')
sources = load_sources('config/')
settings = load_settings('config/')
rules = get_scan_rules(family, sources)

ncis = scan_all(rules, settings)
print(f'\nTOTAL: {len(ncis)} items fetched')

from collections import Counter
by_source = Counter(n.source_name for n in ncis)
for src, cnt in by_source.most_common():
    print(f'  {cnt:3d}  {src}')

print(f'\nSample titles:')
for nci in ncis[:5]:
    lang = 'HE' if nci.language == 'he' else 'EN'
    print(f'  [{lang}] [{nci.source_name}] {nci.title[:80]}')
"
```

### Expected results:
- At least some sources return content (not all will — some sites block scrapers)
- YouTube channels should work via RSS
- RSS feeds (ArchDaily, Dezeen, Permaculture, Nature Chemistry, etc.) should return items

### 🚦 GATE 3 — Report which sources work, which fail. List any 0-item sources.

---

## PHASE 4: Full Real Build (RSS + Claude API)

This is the first real newsletter build. Requires ANTHROPIC_API_KEY in .env.

```bash
cd [PROJECT_PATH]
source venv/bin/activate

echo "=== FULL REAL BUILD ==="
rm -f data/famely.db
python -m src.orchestrator daily-build 2>&1

echo ""
echo "=== BUILD ANALYSIS ==="
python3 -c "
from src.db import Database
import datetime
db = Database('data/famely.db')
today = datetime.date.today().isoformat()
nl = db.get_newsletter(today)
if nl:
    print(f'Status: {nl[\"status\"]}')
    print(f'Items fetched: {nl[\"items_fetched\"]}')
    print(f'Items selected: {nl[\"items_selected\"]}')
    print(f'Submissions: {nl[\"submissions_count\"]}')
    print(f'Build time: {nl[\"build_duration_ms\"]}ms')
    print(f'HTML: {nl[\"html_path\"]}')
    cost = db.get_daily_cost(today)
    print(f'Token cost: \${cost:.4f}')
else:
    print('ERROR: No newsletter found for today')
db.close()
"

echo ""
echo "=== HTML SIZE ==="
ls -la data/archive/html/
wc -c data/archive/html/*.html

echo ""
echo "=== HTML STRUCTURE CHECK ==="
HTML_FILE=$(ls -t data/archive/html/*.html | head -1)
python3 -c "
html = open('$HTML_FILE').read()
checks = [
    ('Size > 5KB', len(html) > 5000),
    ('DOCTYPE', '<!DOCTYPE html>' in html),
    ('Family name', 'בן-צבי ולד' in html),
    ('Nimrod section', 'נימרוד' in html),
    ('Michal section', 'מיכל' in html),
    ('Shaked LTR', 'shaked' in html.lower()),
    ('YoYo (not Maayan)', 'יויו' in html and 'הפינה של מעיין' not in html),
    ('Tzlil section', 'צליל' in html),
    ('Puzzle present', 'חידת היום' in html or 'חידה' in html),
    ('Footer', 'powered by AI' in html),
]
for name, ok in checks:
    print(f'  {\"✓\" if ok else \"✗\"} {name}')
print(f'\nSize: {len(html)} bytes')
print(f'Result: {sum(ok for _, ok in checks)}/{len(checks)} checks passed')
"
```

### Expected results:
- Status: 'ready'
- Multiple real items fetched and selected
- HTML > 5KB with all sections present
- Token cost < $0.50 (daily budget alert threshold)
- All HTML structure checks pass

### 🚦 GATE 4 — Report full build results + HTML check. CRITICAL: Do NOT proceed to Phase 5 without Nimrod reviewing the HTML output.

**How to review:** Show the first 30 lines of the HTML file and the last 10 lines, or provide the file path for Nimrod to open in a browser.

---

## PHASE 5: Distribution Test (FTP + Email)

**ONLY after Nimrod approves the HTML from Phase 4.**

```bash
cd [PROJECT_PATH]
source venv/bin/activate

echo "=== FTP TEST ==="
# Test FTP connection first (without uploading newsletter)
python3 -c "
import ftplib, os
from dotenv import load_dotenv
load_dotenv()
host = os.environ.get('FTP_HOST', '')
user = os.environ.get('FTP_USER', '')
pw = os.environ.get('FTP_PASS', '')
print(f'Connecting to {host}...')
try:
    ftp = ftplib.FTP(host, timeout=15)
    ftp.login(user, pw)
    print(f'Connected! Current dir: {ftp.pwd()}')
    ftp.dir()
    ftp.quit()
    print('FTP: OK')
except Exception as e:
    print(f'FTP FAILED: {e}')
"

echo ""
echo "=== EMAIL TEST ==="
# Test SMTP connection (without sending newsletter)
python3 -c "
import smtplib, os
from dotenv import load_dotenv
load_dotenv()
host = os.environ.get('SMTP_HOST', '')
user = os.environ.get('SMTP_USER', '')
pw = os.environ.get('SMTP_PASS', '')
print(f'Connecting to {host}:465...')
try:
    with smtplib.SMTP_SSL(host, 465, timeout=15) as s:
        s.login(user, pw)
        print('SMTP: OK — authenticated successfully')
except Exception as e:
    print(f'SMTP FAILED: {e}')
"
```

### 🚦 GATE 5 — Report FTP and SMTP test results. Only if both pass, proceed:

```bash
echo "=== FULL SEND ==="
python -m src.orchestrator daily-send 2>&1

echo ""
echo "=== VERIFY PUBLIC URL ==="
URL=$(python3 -c "
from src.db import Database
import datetime
db = Database('data/famely.db')
nl = db.get_newsletter(datetime.date.today().isoformat())
print(nl['public_url'] if nl else 'NONE')
db.close()
")
echo "Public URL: $URL"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$URL" 2>&1 || echo "URL unreachable"
```

### Expected results:
- FTP upload succeeds
- Public URL returns HTTP 200
- Each family member receives email
- Newsletter status changes to 'distributed'

---

## PHASE 6: Cron Setup

Only after Phase 5 succeeds:

```bash
echo "=== CURRENT CRON ==="
crontab -l 2>/dev/null || echo "(empty)"

echo ""
echo "=== ADD FAMELY CRON ==="
# Add to existing crontab (preserve existing entries)
(crontab -l 2>/dev/null; echo "
# Famely Neuslettr — Daily Schedule (IST)
TZ=Asia/Jerusalem
0  9 * * *  cd [PROJECT_PATH] && ./run.sh daily-build  >> logs/cron.log 2>&1
0 12 * * *  cd [PROJECT_PATH] && ./run.sh daily-send   >> logs/cron.log 2>&1
") | crontab -

echo ""
echo "=== VERIFY ==="
crontab -l
```

---

## Summary Report Template

After all phases, compile a final report:

```
=== FAMELY NEUSLETTR DEPLOYMENT REPORT ===
Date: [date]
Server: [hostname]
Project path: [path]
Git version: [tag]

PHASE 1 - Environment:  [PASS/FAIL] — [notes]
PHASE 2 - Mock test:    [PASS/FAIL] — [items fetched, HTML size]
PHASE 3 - RSS scan:     [PASS/FAIL] — [X sources OK, Y failed]
PHASE 4 - Real build:   [PASS/FAIL] — [items, cost, HTML checks]
PHASE 5 - Distribution: [PASS/FAIL] — [FTP, email status]
PHASE 6 - Cron:         [CONFIGURED/PENDING]

Working sources: [list]
Failed sources: [list]
Total token cost for test: $[amount]
Public URL: [url]

BLOCKERS: [any issues]
READY FOR SUNDAY: [YES/NO]
```
