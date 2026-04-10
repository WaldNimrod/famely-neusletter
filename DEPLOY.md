# Famely Neuslettr — Deployment Guide (v3.1.2)

## Overview

Famely Neuslettr is a 3-level content system for weekly family newsletters powered by AgentsOS. The system automatically curates, summarizes, and enriches family stories using AI, with character-driven design that changes monthly.

**Weekly Schedule:** Build on Fridays, send for weekend reading
**Cadence:** One newsletter per week (Friday releases)
**Branding:** AgentsOS — Agents OS methodology engine

## Prerequisites

- Python 3.10+
- pip
- Git
- Access to: Anthropic API key, FTP credentials (nimrod.bio), SMTP credentials
- Character assets directory structure (see Step 7)

## Step 1: Clone & Setup

```bash
cd /opt
git clone https://github.com/WaldNimrod/famely-neuslettr.git
cd famely-neuslettr

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in ALL values:
```
ANTHROPIC_API_KEY=sk-ant-...        # Required for AI generation
FTP_HOST=ftp.upress.co.il           # FTP server
FTP_USER=...                         # FTP username
FTP_PASS=...                         # FTP password
SMTP_HOST=...                        # Email server (e.g., smtp.gmail.com)
SMTP_USER=...                        # Email login
SMTP_PASS=...                        # Email password or app password
SMTP_FROM=famely@nimrod.bio          # From address
```

For v1.1.0, WhatsApp fields are optional (email-only distribution).

## Step 3: Verify

```bash
source venv/bin/activate
python -m src.orchestrator health-check
```

Expected output: all ✓ checks pass.

## Step 4: Set Up Character Assets

The newsletter uses rotating monthly characters with 3-level asset support:

```bash
# Create asset directory structure
mkdir -p assets/characters/2026-04
mkdir -p assets/characters/2026-05
mkdir -p assets/characters/_placeholder
mkdir -p assets/decorations
mkdir -p assets/og-images

# Create .gitkeep files to preserve directory structure
touch assets/characters/2026-04/.gitkeep
touch assets/characters/2026-05/.gitkeep
touch assets/characters/_placeholder/.gitkeep
touch assets/decorations/.gitkeep
touch assets/og-images/.gitkeep
```

**Character Schedule:**
- April 2026: Cat in the Hat (Dr. Seuss style)
- May 2026: Popeye (Classic Popeye strip)

Add PNG assets for each pose to `assets/characters/{YYYY-MM}/`:
- `hero-greeting.png`
- `reading.png`
- `thinking.png`
- `pointing.png`
- `goodbye.png`
- `icon.png`

If assets don't exist, the system falls back to emoji representations.

## Step 5: First Test Run

```bash
# Build with real RSS sources + real Claude API
python -m src.orchestrator weekly-build

# Check the generated HTML
ls -la data/archive/html/
# Open the HTML file in browser to verify content quality

# Check costs
python -c "
from src.db import Database
db = Database('data/famely.db')
import datetime
today = datetime.date.today().isoformat()
print(f'This week cost: \${db.get_weekly_cost(today):.4f}')
db.close()
"
```

## Step 6: Test Distribution

```bash
# Send to all family members via email
python -m src.orchestrator weekly-send
```

Verify: check each family member received the email.

## Step 7: Set Up Cron (Automation)

```bash
# Create the run script
chmod +x run.sh

# Edit crontab
crontab -e
```

Add these lines:
```cron
# Famely Neuslettr — Weekly Schedule (IST, Fridays)
TZ=Asia/Jerusalem
0  9 * * 5  cd /opt/famely-neuslettr && ./run.sh weekly-build  >> logs/cron.log 2>&1
0 12 * * 5  cd /opt/famely-neuslettr && ./run.sh weekly-send   >> logs/cron.log 2>&1
```

This runs every Friday:
- 9:00 AM: Build weekly newsletter
- 12:00 PM: Send to all family members

## Step 8: Verify Automation

Wait for the next Friday, or test manually:
```bash
./run.sh weekly-build && ./run.sh weekly-send
```

Check logs:
```bash
tail -50 logs/cron.log
```

## Rollback

If something goes wrong:
```bash
git log --oneline -5          # Find last good commit
git checkout v1.0.0           # Roll back to known good version
```

## 3-Level Content System

The newsletter supports three content depth levels:

1. **Level 1 (BASE):** Configuration, family info, system metadata
2. **Level 2 (LEAN):** Team info, work packages, story ideas
3. **Level 3 (FULL):** AI-enriched stories, summaries, puzzle generation, analytics

Each level inherits content from the previous level. Character assets enhance all levels.

## Monitoring

```bash
# Check last newsletter status
python -c "
from src.db import Database
db = Database('data/famely.db')
nl = db.get_last_newsletter()
if nl:
    print(f'Date: {nl[\"date\"]}')
    print(f'Status: {nl[\"status\"]}')
    print(f'Items: {nl[\"items_selected\"]}')
    print(f'URL: {nl[\"public_url\"]}')
db.close()
"

# Check weekly token costs
python -c "
from src.db import Database
import datetime
db = Database('data/famely.db')
today = datetime.date.today().isoformat()
print(f'This week cost: \${db.get_weekly_cost(today):.4f}')
db.close()
"

# Check monthly token costs
python -c "
from src.db import Database
import datetime
db = Database('data/famely.db')
ym = datetime.date.today().strftime('%Y-%m')
print(f'Monthly cost ({ym}): \${db.get_monthly_cost(ym):.4f}')
db.close()
"
```

## AgentsOS Integration

Famely Neuslettr is managed as a project under AgentsOS (AOS) v3.1.2:
- Profile: L2 (Dashboard + API backend)
- Methodology: LOD Standard v0.3
- Character assets: Monthly rotation driven by AOS content calendar
- Deployment: Docker container with FastAPI backend (python3.11)
