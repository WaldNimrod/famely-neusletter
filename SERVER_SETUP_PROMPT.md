# Famely Neuslettr — Server Deployment Brief

> This document is a deployment brief for the server-side Claude agent.
> Context: You are running as Claude Code on the home server, connected via remote terminal from the Mac dev machine.
> Phase: Information gathering before installation. Report back what exists and what's needed.

---

## 1. Project Overview

**Famely Neuslettr** is an automated daily family newsletter system for a family of 5. It scans content sources (RSS, websites, YouTube), personalizes content per family member using AI (Claude API), generates a beautiful HTML newsletter, uploads it to a static hosting server via FTP, and sends notification messages to each family member.

**Architecture:**
```
[Home Server]                    [nimrod.bio]           [Family Members]
Cron 09:00 → daily-build         Static HTML host       WhatsApp / Email
  M1: Load config                (FTP upload only)      notifications
  M2: Scan RSS/web/YouTube                              with link to
  M3: Score + Claude AI summaries                       newsletter
  M4: Render HTML (Jinja2)
Cron 12:00 → daily-send
  M5: FTP upload → nimrod.bio
  M5: Send email/WhatsApp to family
Cron 21:00 → daily-survey
  M5: Send daily survey question
```

**Tech stack:** Python 3.10+, SQLite, Jinja2, requests, BeautifulSoup4

**Version:** v1.0.0 (tested locally in mock mode, all modules working)

---

## 2. What Needs to Be Installed

### System requirements
- Python 3.10 or newer
- pip3
- git
- cron (should exist already)
- Network access: outbound HTTP/HTTPS (RSS feeds, Claude API, Twilio API), outbound FTP (to upress.co.il), outbound SMTP

### Python packages (requirements.txt)
```
jinja2>=3.0
requests>=2.28
beautifulsoup4>=4.11
python-dotenv>=1.0
anthropic>=0.40
```

### Project location
Recommended: `/opt/famely-neuslettr/`

---

## 3. Information Gathering Phase

Before installation, please check and report:

### A. System
```bash
uname -a
python3 --version
pip3 --version
git --version
crontab -l 2>/dev/null || echo "no crontab"
```

### B. Network
```bash
# Test outbound HTTPS (Claude API)
curl -s -o /dev/null -w "%{http_code}" https://api.anthropic.com/v1/messages 2>/dev/null || echo "BLOCKED"

# Test outbound HTTPS (RSS feeds)
curl -s -o /dev/null -w "%{http_code}" https://www.archdaily.com/feed 2>/dev/null || echo "BLOCKED"

# Test outbound FTP
curl -s -o /dev/null -w "%{http_code}" ftp://ftp.upress.co.il/ 2>/dev/null || echo "BLOCKED or needs credentials"

# Test DNS
nslookup api.anthropic.com 2>/dev/null || echo "DNS issue"
```

### C. Disk & permissions
```bash
df -h /opt
ls -la /opt/
whoami
id
```

### D. Existing services
```bash
# Check if anything already runs on port 8443 (future webhook)
ss -tlnp | grep 8443 || echo "port 8443 free"

# Check existing cron jobs
crontab -l 2>/dev/null

# Check if there are other Python projects
ls /opt/*/requirements.txt 2>/dev/null
```

### E. GitHub access
```bash
# Check if git can reach GitHub
git ls-remote https://github.com/WaldNimrod/famely-neuslettr.git HEAD 2>/dev/null || echo "Cannot reach GitHub repo"

# Or check SSH
ssh -T git@github.com 2>&1 | head -2
```

---

## 4. Transfer Method

The project needs to get from the dev machine (Mac) to the server. Options in order of preference:

### Option A: GitHub (preferred)
If the server has GitHub access:
```bash
cd /opt
git clone https://github.com/WaldNimrod/famely-neuslettr.git
cd famely-neuslettr
```

### Option B: scp from dev machine
If working over SSH terminal from Mac:
```bash
# On Mac (dev machine), from the project directory:
scp -r famely-neuslettr/ user@server:/opt/famely-neuslettr/
```

### Option C: tar + transfer
```bash
# On Mac:
cd /path/to/Famely\ Neuslettr/
tar czf famely-neuslettr-v1.0.0.tar.gz --exclude=data --exclude=__pycache__ --exclude=.git famely-neuslettr/
scp famely-neuslettr-v1.0.0.tar.gz user@server:/opt/

# On server:
cd /opt
tar xzf famely-neuslettr-v1.0.0.tar.gz
```

---

## 5. Installation Steps (after transfer)

```bash
cd /opt/famely-neuslettr

# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create directories
mkdir -p data/submissions data/archive/raw data/archive/editions data/archive/html logs

# 4. Create .env (REQUIRES HUMAN INPUT for secrets)
cp .env.example .env
# STOP HERE — Nimrod will fill in the actual values:
#   ANTHROPIC_API_KEY
#   FTP_HOST, FTP_USER, FTP_PASS
#   SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM
```

---

## 6. Verification Sequence

After .env is configured:

```bash
cd /opt/famely-neuslettr
source venv/bin/activate

# Step 1: Health check
python -m src.orchestrator health-check

# Step 2: Mock build (no external calls)
python -m src.orchestrator daily-build --mock
# Expected: 13 items fetched → 9 selected, HTML ~13KB

# Step 3: Real build (real RSS + real Claude API)
python -m src.orchestrator daily-build
# Expected: real content from RSS feeds, AI-generated summaries

# Step 4: Check output
cat data/archive/html/$(date +%Y-%m-%d).html | head -20
ls -la data/archive/html/

# Step 5: Test send (FTP + email)
python -m src.orchestrator daily-send
# Expected: HTML uploaded to nimrod.bio, emails sent to family
```

---

## 7. Cron Setup (after verification)

```bash
# Edit crontab
crontab -e
```

Add:
```cron
# Famely Neuslettr — Daily Schedule (Israel Standard Time)
TZ=Asia/Jerusalem
0  9 * * *  cd /opt/famely-neuslettr && ./run.sh daily-build  >> logs/cron.log 2>&1
0 12 * * *  cd /opt/famely-neuslettr && ./run.sh daily-send   >> logs/cron.log 2>&1
```

Survey (21:00) will be added in v1.2.0 after WhatsApp integration.

---

## 8. Critical Notes

1. **DO NOT** run daily-send before verifying the HTML output from daily-build looks good
2. **DO NOT** fill in .env values without Nimrod's approval — secrets must come from him
3. The `.env` file must NEVER be committed to git
4. v1.1.0 is email-only distribution — WhatsApp fields in .env are not needed yet
5. First real newsletter target: **Sunday, April 13, 2026**
6. The SQLite database (`data/famely.db`) is created automatically on first run
7. All HTML files are archived in `data/archive/html/` — never delete these

---

## 9. File Structure (for reference)

```
/opt/famely-neuslettr/
├── config/
│   ├── family.json          ← 5 family member profiles
│   ├── sources.json         ← 17 RSS/web/YouTube sources
│   └── settings.json        ← Schedule, thresholds, AI config
├── .env                     ← Secrets (created manually, NOT in git)
├── src/
│   ├── models.py            ← Data models (NCI, NEO, etc.)
│   ├── db.py                ← SQLite database layer
│   ├── m1_profiles.py       ← Config loader
│   ├── m2_scanner.py        ← RSS/web/YouTube scanner
│   ├── m3_normalizer.py     ← Scoring, curation, AI generation
│   ├── m4_renderer.py       ← HTML renderer (Jinja2)
│   ├── m5_distributor.py    ← FTP + email/WhatsApp
│   ├── m6_feedback.py       ← Webhook handler
│   ├── token_tracker.py     ← Claude API cost tracking
│   └── orchestrator.py      ← CLI entry point
├── templates/
│   └── newsletter.html.j2   ← HTML template
├── data/                    ← Created at runtime
├── logs/                    ← Created at runtime
├── run.sh                   ← Cron runner script
├── requirements.txt
├── DEPLOY.md                ← Full deployment guide
└── ROADMAP.md               ← Version plan & roadmap
```

---

## 10. Report Template

After gathering information, report back in this format:

```
=== SERVER READINESS REPORT ===
OS: [uname output]
Python: [version]
pip: [version]
Git: [version]
Disk free (/opt): [size]
Network - HTTPS: [OK/BLOCKED]
Network - FTP: [OK/BLOCKED]
Network - DNS: [OK/FAIL]
GitHub access: [OK/BLOCKED]
Port 8443: [free/in use]
Existing cron: [yes/no, details]
Recommended transfer: [A/B/C]
Blockers: [list any issues]
Ready for install: [YES/NO]
```
