"""
Famely Neuslettr — Orchestrator
CLI entry points per LOD400 §10.
Usage:
    python -m src.orchestrator daily-build [--mock]
    python -m src.orchestrator daily-send [--mock]
    python -m src.orchestrator daily-survey [--mock]
    python -m src.orchestrator health-check
"""

import argparse
import json
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

from src.m1_profiles import load_profiles, load_sources, load_settings, get_scan_rules
from src.m2_scanner import scan_all, generate_mock_ncis
from src.m3_normalizer import build_edition
from src.m4_renderer import render, save_html
from src.m5_distributor import distribute, send_survey
from src.m6_feedback import run_webhook_server
from src.db import Database
from src.token_tracker import TokenTracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('famely')


def cmd_daily_build(args):
    """M1 → M2 → M3 → M4: Build today's newsletter."""
    logger.info("=" * 60)
    logger.info("DAILY BUILD starting")
    logger.info("=" * 60)

    # Load config
    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)

    logger.info(f"Family: {family.family_name} ({len(family.members)} members)")

    # Init DB
    db = Database(args.db or "data/famely.db")

    # Init token tracker
    tt = TokenTracker(db, mock=args.mock)

    # M2: Scan
    if args.mock:
        logger.info("[MOCK] Using mock content")
        ncis = generate_mock_ncis()
    else:
        sources = load_sources(config_dir)
        scan_rules = get_scan_rules(family, sources)
        logger.info(f"Scanning {len(scan_rules)} sources...")
        ncis = scan_all(scan_rules, settings)

    logger.info(f"Scan complete: {len(ncis)} items fetched")

    if not ncis:
        logger.warning("No items fetched! Checking for submissions...")

    # M3: Build edition
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    neo = build_edition(ncis, family, settings, db, tt, today)

    # M4: Render HTML
    html = render(neo, template_path="templates/", db=db)
    html_path = save_html(html, today)

    # Update DB with HTML path
    url_base = settings.newsletter.get('url_base', 'https://nimrod.bio/newsletter')
    db.update_newsletter(today, html_path=html_path,
                         public_url=f"{url_base}/{today}/index.html")

    # Summary
    logger.info("=" * 60)
    logger.info(f"BUILD COMPLETE: {today}")
    logger.info(f"  Items fetched: {neo.metadata['items_fetched']}")
    logger.info(f"  Items selected: {neo.metadata['items_selected']}")
    logger.info(f"  Submissions: {neo.metadata['submissions_count']}")
    logger.info(f"  HTML: {html_path} ({len(html)} bytes)")
    logger.info(f"  Duration: {neo.metadata['build_duration_ms']}ms")

    # Token cost
    daily_cost = db.get_daily_cost(today)
    logger.info(f"  Token cost today: ${daily_cost:.4f}")
    if daily_cost > settings.budget.get('daily_alert_usd', 0.50):
        logger.warning(f"  BUDGET ALERT: ${daily_cost:.4f} exceeds daily limit!")

    logger.info("=" * 60)

    db.close()
    return html_path


def cmd_daily_send(args):
    """M5: Distribute today's newsletter via FTP + WhatsApp/Email."""
    logger.info("=" * 60)
    logger.info("DAILY SEND starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)

    db = Database(args.db or "data/famely.db")

    # Get today's newsletter
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)

    if not newsletter:
        logger.error(f"No newsletter found for {today}. Run daily-build first!")
        db.close()
        return

    if newsletter['status'] != 'ready':
        logger.error(f"Newsletter status is '{newsletter['status']}', expected 'ready'")
        db.close()
        return

    html_path = newsletter['html_path']
    neo_json = newsletter.get('neo_json')

    if not neo_json:
        logger.error("No NEO data in newsletter record")
        db.close()
        return

    # Reconstruct NEO from JSON
    from src.models import NEO
    neo_data = json.loads(neo_json)
    neo = NEO(**neo_data)

    # Distribute
    result = distribute(html_path, neo, family, settings, mock=args.mock)

    # Update status
    if result.ftp_success:
        db.update_newsletter(today, status='distributed', public_url=result.public_url)
        logger.info(f"DISTRIBUTED: {result.public_url}")
    else:
        db.update_newsletter(today, status='send_failed')
        logger.error("DISTRIBUTION FAILED")

    for r in result.member_results:
        status = "✓" if r['success'] else "✗"
        logger.info(f"  {status} {r['member_id']} via {r['channel']}")

    db.close()


def cmd_daily_survey(args):
    """M5: Send daily survey at 21:00."""
    logger.info("=" * 60)
    logger.info("DAILY SURVEY starting")
    logger.info("=" * 60)

    config_dir = args.config or "config/"
    family = load_profiles(config_dir)
    settings = load_settings(config_dir)

    db = Database(args.db or "data/famely.db")

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    newsletter = db.get_newsletter(today)

    if not newsletter or not newsletter.get('neo_json'):
        logger.error(f"No newsletter for {today}")
        db.close()
        return

    from src.models import NEO
    neo = NEO(**json.loads(newsletter['neo_json']))

    results = send_survey(family, neo, settings, mock=args.mock)

    db.update_newsletter(today, status='feedback_collecting')

    for r in results:
        logger.info(f"  Survey → {r['member_id']}: {r['status']} ({r['channel']})")

    db.close()


def cmd_health_check(args):
    """Verify system health."""
    logger.info("HEALTH CHECK")

    config_dir = args.config or "config/"

    # Check configs
    try:
        family = load_profiles(config_dir)
        logger.info(f"  ✓ family.json: {len(family.members)} members")
    except Exception as e:
        logger.error(f"  ✗ family.json: {e}")

    try:
        from src.m1_profiles import load_sources
        sources = load_sources(config_dir)
        logger.info(f"  ✓ sources.json: {len(sources)} active sources")
    except Exception as e:
        logger.error(f"  ✗ sources.json: {e}")

    try:
        settings = load_settings(config_dir)
        logger.info(f"  ✓ settings.json loaded")
    except Exception as e:
        logger.error(f"  ✗ settings.json: {e}")

    # Check DB
    try:
        db = Database(args.db or "data/famely.db")
        last = db.get_last_newsletter()
        if last:
            logger.info(f"  ✓ DB: last newsletter {last['date']} ({last['status']})")
        else:
            logger.info(f"  ✓ DB: no newsletters yet")
        db.close()
    except Exception as e:
        logger.error(f"  ✗ DB: {e}")

    # Check template
    tmpl_path = Path("templates/newsletter.html.j2")
    if tmpl_path.exists():
        logger.info(f"  ✓ Template: {tmpl_path}")
    else:
        logger.error(f"  ✗ Template not found: {tmpl_path}")

    # Check .env
    env_path = Path(".env")
    if env_path.exists():
        logger.info(f"  ✓ .env exists")
    else:
        logger.warning(f"  ⚠ .env not found (needed for API keys)")

    # Disk space
    import shutil
    total, used, free = shutil.disk_usage(".")
    free_mb = free // (1024 * 1024)
    logger.info(f"  ✓ Disk: {free_mb}MB free")


def cmd_webhook(args):
    """Run the webhook server."""
    run_webhook_server(
        host=args.host or '0.0.0.0',
        port=args.port or 8443,
        config_dir=args.config or 'config/',
        db_path=args.db or 'data/famely.db',
    )


def main():
    parser = argparse.ArgumentParser(description='Famely Neuslettr Orchestrator')
    parser.add_argument('command', choices=[
        'daily-build', 'daily-send', 'daily-survey', 'health-check', 'webhook'
    ])
    parser.add_argument('--mock', action='store_true', help='Use mock data (no external calls)')
    parser.add_argument('--config', default='config/', help='Config directory')
    parser.add_argument('--db', default='data/famely.db', help='Database path')
    parser.add_argument('--host', default='0.0.0.0', help='Webhook host')
    parser.add_argument('--port', type=int, default=8443, help='Webhook port')

    args = parser.parse_args()

    commands = {
        'daily-build': cmd_daily_build,
        'daily-send': cmd_daily_send,
        'daily-survey': cmd_daily_survey,
        'health-check': cmd_health_check,
        'webhook': cmd_webhook,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
