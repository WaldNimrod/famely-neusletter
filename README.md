# Famely Neuslettr

A personalized family newsletter generator that aggregates content from RSS feeds, websites, and social media based on individual family member interests, curates it with AI, and distributes via FTP + WhatsApp/Email.

## Overview

Famely Neuslettr is a full-stack daily newsletter pipeline for families that:

- **M1 (Profiles)**: Loads family member profiles, interests, and content sources
- **M2 (Scanner)**: Fetches content from RSS feeds, websites, and YouTube
- **M3 (Normalizer)**: Deduplicates, scores, curates content with AI summaries
- **M4 (Renderer)**: Generates beautiful HTML newsletters with Jinja2
- **M5 (Distributor)**: Publishes via FTP and sends via WhatsApp/Email
- **M6 (Feedback)**: Collects user feedback via webhook and daily survey
- **Orchestrator**: CLI for managing the full pipeline

## Quick Start

### Prerequisites

- Python 3.8+
- `.env` file with API keys (see `.env.example`)

### Setup

```bash
# Clone and install
git clone <repo-url>
cd famely-neuslettr
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with real API keys and credentials
```

### Configuration

Configuration lives in `config/`:

- **`family.json`**: Family profiles, members, interests, media sources
- **`sources.json`**: RSS feeds and website scanners
- **`settings.json`**: Newsletter settings, budget, distribution channels

### Running

#### Daily Build (M1→M2→M3→M4)
Scan sources, curate content, and render today's newsletter:

```bash
python3 -m src.orchestrator daily-build [--mock]
```

Use `--mock` for testing (uses generated content instead of fetching).

#### Daily Send (M5)
Distribute today's newsletter via FTP and WhatsApp/Email:

```bash
python3 -m src.orchestrator daily-send [--mock]
```

#### Daily Survey (M5+M6)
Send feedback survey at 21:00 (requires completed newsletter):

```bash
python3 -m src.orchestrator daily-survey [--mock]
```

#### Health Check
Verify all systems and configurations:

```bash
python3 -m src.orchestrator health-check
```

#### Webhook Server (M6)
Run feedback collection webhook (e.g., for submissions):

```bash
python3 -m src.orchestrator webhook [--host 0.0.0.0] [--port 8443]
```

## Architecture

### Module Structure

```
src/
├── m1_profiles.py       # Configuration loader
├── m2_scanner.py        # RSS/web/YouTube fetcher
├── m3_normalizer.py     # Dedup, score, curate, summarize
├── m4_renderer.py       # Jinja2 HTML renderer
├── m5_distributor.py    # FTP + WhatsApp/Email distribution
├── m6_feedback.py       # Webhook + survey collection
├── db.py                # SQLite database (newsletters, costs, submissions)
├── models.py            # Data models (NCI, NEO, etc.)
├── token_tracker.py     # Claude API token cost tracking
└── orchestrator.py      # CLI entry points
```

### Data Flow

1. **M1**: Load family profiles + sources
2. **M2**: Fetch raw content (NCI = News Content Item)
3. **M3**: Normalize, deduplicate, score, curate (select top items)
4. **M3**: AI summarization (if budget allows)
5. **M4**: Render HTML (NEO = Newsletter Edition Object)
6. **M5**: Save HTML, upload to FTP, send via WhatsApp/Email
7. **M6**: Collect feedback via webhook + survey

### Database

SQLite (`data/famely.db`) tracks:
- Newsletter editions (date, status, HTML path, public URL)
- Token costs per build (Claude API)
- Submissions via webhook
- Survey responses

## Configuration Details

### family.json

```json
{
  "family_name": "Ben-Tzvi Wald Family",
  "members": [
    {
      "id": "nimrod",
      "name": "Nimrod",
      "role": "parent",
      "language_preference": "both",
      "interests": [
        {
          "topic": "Sailing & Skipper Life",
          "subtopics": ["sailing", "cruising", "skipper"],
          "priority": "high"
        }
      ],
      "media_sources": [
        {
          "type": "rss",
          "url": "https://www.yachtingworld.com/feed",
          "name": "Yachting World"
        }
      ]
    }
  ]
}
```

### sources.json

Global RSS feeds and websites to scan (member sources can override).

### settings.json

- `newsletter`: URL base, publication time, template
- `budget`: Daily token limit (USD), alert threshold
- `distribution`: FTP, WhatsApp, Email configs
- `ai`: Claude model, temperature, max tokens per summary

## Environment Variables (.env)

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# FTP (newsletter upload)
FTP_HOST=ftp.upress.co.il
FTP_USER=...
FTP_PASS=...
FTP_PATH=/newsletter

# WhatsApp (Twilio)
WHATSAPP_PROVIDER=twilio
TWILIO_SID=...
TWILIO_TOKEN=...
TWILIO_FROM=whatsapp:+...

# Email (SMTP)
SMTP_HOST=...
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=famely@nimrod.bio

# Webhook
WEBHOOK_SECRET=...
```

## API & Formats

### NCI (News Content Item)

Raw content item from a source:

```python
{
  "id": "unique_id",
  "source_id": "source_name",
  "title": "Article Title",
  "url": "https://...",
  "summary": "Original summary",
  "published": "2026-04-09T12:30:00Z",
  "tags": ["keyword1", "keyword2"],
  "type": "article|video|social_post"
}
```

### NEO (Newsletter Edition Object)

Curated and rendered newsletter:

```python
{
  "date": "2026-04-09",
  "family_name": "Ben-Tzvi Wald Family",
  "sections": [
    {
      "member_id": "nimrod",
      "member_name": "Nimrod",
      "items": [
        {
          "title": "...",
          "url": "...",
          "summary": "...",
          "source": "...",
          "ai_summary": "..."
        }
      ]
    }
  ],
  "metadata": {
    "items_fetched": 500,
    "items_selected": 15,
    "submissions_count": 2,
    "build_duration_ms": 2500,
    "token_cost_usd": 0.12
  }
}
```

## Testing & Development

### Run with Mock Data

```bash
# Test full pipeline without network calls
python3 -m src.orchestrator daily-build --mock
python3 -m src.orchestrator daily-send --mock
```

### Custom Config/DB Paths

```bash
python3 -m src.orchestrator daily-build \
  --config /path/to/config/ \
  --db /path/to/famely.db
```

### Database Queries

```bash
sqlite3 data/famely.db
sqlite> .schema
sqlite> SELECT * FROM newsletters ORDER BY date DESC LIMIT 5;
sqlite> SELECT * FROM token_usage WHERE date = '2026-04-09';
```

## Troubleshooting

### Health Check Shows Errors

```bash
python3 -m src.orchestrator health-check
```

This verifies:
- ✓ Config files (family.json, sources.json, settings.json)
- ✓ Database (last newsletter status)
- ✓ Template (newsletter.html.j2)
- ✓ .env file
- ✓ Disk space

### Newsletter Not Found for Send

Run `daily-build` first to create today's newsletter:

```bash
python3 -m src.orchestrator daily-build
python3 -m src.orchestrator daily-send
```

### Token Cost Too High

Check `settings.json` daily budget limit and adjust model/summary settings:

```json
{
  "budget": {
    "daily_alert_usd": 0.50
  },
  "ai": {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens_per_summary": 100
  }
}
```

### FTP Connection Fails

Verify `.env` FTP credentials and test connectivity:

```bash
# Check environment
echo $FTP_HOST $FTP_USER
```

## Directory Structure

```
famely-neuslettr/
├── README.md                    # This file
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── config/
│   ├── family.json             # Family profiles + interests
│   ├── sources.json            # RSS feeds & websites
│   └── settings.json           # Newsletter config + budget
├── src/
│   ├── __init__.py
│   ├── m1_profiles.py          # M1: Load configs
│   ├── m2_scanner.py           # M2: Fetch content
│   ├── m3_normalizer.py        # M3: Curate & summarize
│   ├── m4_renderer.py          # M4: Render HTML
│   ├── m5_distributor.py       # M5: Distribute
│   ├── m6_feedback.py          # M6: Feedback webhook
│   ├── models.py               # Data models
│   ├── db.py                   # SQLite database
│   ├── token_tracker.py        # Token cost tracking
│   └── orchestrator.py         # CLI + entry points
├── templates/
│   └── newsletter.html.j2      # Jinja2 HTML template
├── data/
│   ├── famely.db              # SQLite database (generated)
│   ├── submissions/           # Webhook submissions
│   └── archive/               # Old newsletters
├── logs/                       # Daily logs
├── tests/                      # Test suite
└── poc.py                      # Proof of concept reference

```

## Deployment

### Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python3 -m src.orchestrator health-check
python3 -m src.orchestrator daily-build --mock
```

### Production Scheduling (cron)

```bash
# Add to crontab (crontab -e)
# Build: 07:00 daily
0 7 * * * cd /path/to/famely-neuslettr && python3 -m src.orchestrator daily-build >> logs/daily-build.log 2>&1

# Send: 09:00 daily
0 9 * * * cd /path/to/famely-neuslettr && python3 -m src.orchestrator daily-send >> logs/daily-send.log 2>&1

# Survey: 21:00 daily
0 21 * * * cd /path/to/famely-neuslettr && python3 -m src.orchestrator daily-survey >> logs/daily-survey.log 2>&1

# Webhook: Start at boot
@reboot cd /path/to/famely-neuslettr && nohup python3 -m src.orchestrator webhook >> logs/webhook.log 2>&1 &
```

### Docker (Optional)

A Dockerfile can be added for containerized deployment.

## Contributing

1. Keep module separation (M1-M6 are independent)
2. Add tests in `tests/`
3. Update `README.md` with new config options
4. Respect `.gitignore` (no `.env`, databases, logs)

## License

Private project for the Ben-Tzvi Wald family.

## Contact

Questions or feedback? Contact Nimrod or the family team.
