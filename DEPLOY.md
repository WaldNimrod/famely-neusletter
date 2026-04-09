# Famely Neuslettr — Deployment Guide (v1.1.0)

## Prerequisites

- Python 3.10+
- pip
- Git
- Access to: Anthropic API key, FTP credentials (nimrod.bio), SMTP credentials

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

## Step 4: First Test Run

```bash
# Build with real RSS sources + real Claude API
python -m src.orchestrator daily-build

# Check the generated HTML
ls -la data/archive/html/
# Open the HTML file in browser to verify content quality

# Check costs
python -c "
from src.db import Database
db = Database('data/famely.db')
import datetime
today = datetime.date.today().isoformat()
print(f'Today cost: \${db.get_daily_cost(today):.4f}')
db.close()
"
```

## Step 5: Test Distribution

```bash
# Send to all family members via email
python -m src.orchestrator daily-send
```

Verify: check each family member received the email.

## Step 6: Set Up Cron (Automation)

```bash
# Create the run script
chmod +x run.sh

# Edit crontab
crontab -e
```

Add these lines:
```cron
# Famely Neuslettr — Daily Schedule (IST)
TZ=Asia/Jerusalem
0  9 * * *  cd /opt/famely-neuslettr && ./run.sh daily-build  >> logs/cron.log 2>&1
0 12 * * *  cd /opt/famely-neuslettr && ./run.sh daily-send   >> logs/cron.log 2>&1
```

## Step 7: Verify Automation

Wait for the next scheduled run, or test manually:
```bash
./run.sh daily-build && ./run.sh daily-send
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
