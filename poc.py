#!/usr/bin/env python3
"""
Famely Neuslettr - POC v1.0
End-to-end pipeline: Fetch → Score → Curate → Generate → Build → Archive

Usage:
    python poc.py                    # Run with today's date
    python poc.py --date 2026-04-08  # Run for specific date
    python poc.py --mock             # Use mock data (no network)

Requirements (in sandbox): requests, jinja2, sqlite3 (all built-in)
For production, add: feedparser, anthropic, httpx, boto3
"""

import json
import hashlib
import sqlite3
import re
import os
import sys
import argparse
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Optional
from dataclasses import dataclass, field, asdict

import requests
from jinja2 import Template

# ─── Setup ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('poc')

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / 'config'
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / 'famely.db'


# ─── Data Models ─────────────────────────────────────────────────────

@dataclass
class ContentItem:
    id: str
    title: str
    url: str
    source_name: str
    source_type: str
    published: Optional[str] = None
    summary: str = ""
    language: str = "en"
    tags: list = field(default_factory=list)
    image_url: Optional[str] = None

@dataclass
class ScoredItem:
    item: ContentItem
    member_id: str
    score: float
    matched_topic: str
    is_discovery: bool = False


# ─── 0. Database Setup ──────────────────────────────────────────────

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with archive schema."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS content_archive (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        source_name TEXT,
        source_type TEXT,
        published_at TEXT,
        fetched_at TEXT DEFAULT (datetime('now')),
        language TEXT,
        raw_summary TEXT,
        generated_summary_he TEXT,
        generated_summary_en TEXT,
        generated_headline TEXT,
        tags TEXT,
        image_url TEXT
    );

    CREATE TABLE IF NOT EXISTS newsletters (
        date TEXT PRIMARY KEY,
        html_path TEXT,
        url TEXT,
        items_count INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS newsletter_items (
        newsletter_date TEXT,
        content_id TEXT,
        member_id TEXT,
        section TEXT,
        relevance_score REAL,
        position INTEGER,
        FOREIGN KEY (content_id) REFERENCES content_archive(id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT NOT NULL,
        date TEXT NOT NULL,
        timestamp TEXT DEFAULT (datetime('now')),
        type TEXT,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS member_preferences_log (
        member_id TEXT,
        date TEXT,
        preferences_snapshot TEXT
    );
    """)
    conn.commit()
    return conn


# ─── 1. FETCH ────────────────────────────────────────────────────────

def fetch_rss(url: str, source_name: str, timeout: int = 15) -> list[ContentItem]:
    """Fetch and parse RSS feed using basic XML parsing."""
    items = []
    try:
        resp = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'FamelyNeuslettr/1.0 POC'
        })
        resp.raise_for_status()

        # Parse XML
        root = ET.fromstring(resp.content)

        # Handle both RSS 2.0 and Atom feeds
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        # Try RSS 2.0 format
        for item_el in root.findall('.//item'):
            title = _xml_text(item_el, 'title') or 'Untitled'
            link = _xml_text(item_el, 'link') or ''
            desc = _xml_text(item_el, 'description') or ''
            pub_date = _xml_text(item_el, 'pubDate') or ''

            if not link:
                continue

            items.append(ContentItem(
                id=_hash(link),
                title=_clean_html(title),
                url=link.strip(),
                source_name=source_name,
                source_type='rss',
                published=pub_date,
                summary=_clean_html(desc)[:400],
                language=_detect_lang(title),
                tags=_extract_tags(item_el),
            ))

        # Try Atom format if no RSS items found
        if not items:
            for entry in root.findall('.//atom:entry', ns):
                title = _xml_text(entry, 'atom:title', ns) or 'Untitled'
                link_el = entry.find('atom:link', ns)
                link = link_el.get('href', '') if link_el is not None else ''
                summary = _xml_text(entry, 'atom:summary', ns) or _xml_text(entry, 'atom:content', ns) or ''
                updated = _xml_text(entry, 'atom:updated', ns) or ''

                if not link:
                    continue

                items.append(ContentItem(
                    id=_hash(link),
                    title=_clean_html(title),
                    url=link.strip(),
                    source_name=source_name,
                    source_type='rss',
                    published=updated,
                    summary=_clean_html(summary)[:400],
                    language=_detect_lang(title),
                ))

        log.info(f"  ✓ {source_name}: {len(items)} items")

    except requests.exceptions.Timeout:
        log.warning(f"  ✗ {source_name}: timeout")
    except ET.ParseError as e:
        log.warning(f"  ✗ {source_name}: XML parse error - {e}")
    except Exception as e:
        log.warning(f"  ✗ {source_name}: {type(e).__name__} - {e}")

    return items


def fetch_all_sources(members: list) -> list[ContentItem]:
    """Fetch content from all family members' sources."""
    log.info("📥 FETCH: Collecting content from all sources...")

    seen_urls = set()
    all_items = []
    all_sources = []

    for member in members:
        for src in member.get('media_sources', []):
            if src.get('type') == 'rss' and src.get('url'):
                key = src['url']
                if key not in seen_urls:
                    seen_urls.add(key)
                    all_sources.append(src)

    for src in all_sources:
        items = fetch_rss(src['url'], src.get('name', 'Unknown'))
        all_items.extend(items)

    # Deduplicate by URL
    unique = {}
    for item in all_items:
        if item.url not in unique:
            unique[item.url] = item

    result = list(unique.values())
    log.info(f"  Total: {len(result)} unique items from {len(all_sources)} sources")
    return result


# ─── 2. SCORE ────────────────────────────────────────────────────────

def score_items(items: list[ContentItem], members: list) -> dict[str, list[ScoredItem]]:
    """Score all items for each family member."""
    log.info("📊 SCORE: Rating content relevance...")

    scored = {}
    for member in members:
        mid = member['id']
        member_scores = []

        for item in items:
            score, topic = _calc_score(item, member)
            if score >= 20:  # minimum threshold
                member_scores.append(ScoredItem(
                    item=item,
                    member_id=mid,
                    score=score,
                    matched_topic=topic
                ))

        member_scores.sort(key=lambda x: x.score, reverse=True)
        scored[mid] = member_scores
        log.info(f"  {member['nickname']}: {len(member_scores)} relevant items (top score: {member_scores[0].score:.0f})" if member_scores else f"  {member['nickname']}: 0 relevant items")

    return scored


def _calc_score(item: ContentItem, member: dict) -> tuple[float, str]:
    """Calculate relevance score for item × member."""
    best_score = 0.0
    best_topic = ""
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()

    for interest in member.get('interests', []):
        topic = interest.get('topic', '')
        subtopics = interest.get('subtopics', [])
        topic_en = interest.get('topic_en', '')
        priority = interest.get('priority', 'medium')

        keywords = [topic.lower(), topic_en.lower()] + [s.lower() for s in subtopics]
        matches = sum(1 for kw in keywords if kw and kw in text)

        if matches == 0:
            continue

        # Base score + match bonus
        score = 30 + min(matches - 1, 5) * 10

        # Priority multiplier
        mult = {'high': 1.5, 'medium': 1.0, 'low': 0.6}
        score *= mult.get(priority, 1.0)

        # Language preference match
        lang_pref = member.get('language_preference', 'both')
        if lang_pref == 'both' or item.language == lang_pref:
            score += 10

        # Source trust (item from member's own sources)
        member_source_names = [s.get('name', '').lower() for s in member.get('media_sources', [])]
        if item.source_name.lower() in member_source_names:
            score += 15

        score = min(score, 100)
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_score, best_topic


# ─── 3. CURATE ───────────────────────────────────────────────────────

def curate(scored: dict, members: list) -> dict:
    """Select final content mix for the newsletter."""
    log.info("🎯 CURATE: Selecting content mix...")

    result = {'family': [], 'discovery': [], 'trivia': None}
    used_urls = set()

    for member in members:
        mid = member['id']
        max_items = member.get('content_preferences', {}).get('max_items_per_day', 3)
        selected = []

        for si in scored.get(mid, []):
            if si.item.url in used_urls:
                continue
            selected.append(si)
            used_urls.add(si.item.url)
            if len(selected) >= max_items:
                break

        result[mid] = selected
        log.info(f"  {member['nickname']}: {len(selected)} items selected")

    # Discovery: pick an item from one member's world for another
    for member in members:
        mid = member['id']
        others = [m for m in members if m['id'] != mid]
        for other in others:
            for si in scored.get(other['id'], [])[:5]:
                if si.item.url not in used_urls and si.score > 50:
                    result['discovery'].append({
                        'item': si,
                        'from': other['nickname'],
                        'to': member['nickname'],
                        'bridge': f"{other['nickname']} → {member['nickname']}"
                    })
                    used_urls.add(si.item.url)
                    break
            break  # One discovery item total for POC

    return result


# ─── 4. GENERATE (Mock for POC) ─────────────────────────────────────

def generate_content(curated: dict, members: list, target_date: date) -> dict:
    """
    Generate summaries and enrichments.
    POC: uses extracted summaries. Production: calls Claude API.
    """
    log.info("✍️  GENERATE: Creating summaries...")

    enriched = {}

    for key, value in curated.items():
        if key == 'family':
            enriched['family'] = _mock_family_content()
            continue

        if key == 'discovery':
            enriched['discovery'] = value
            continue

        if key == 'trivia':
            continue

        # Member sections
        member = next((m for m in members if m['id'] == key), None)
        if not member:
            continue

        enriched_items = []
        for si in value:
            # POC: use existing summary, trim to appropriate length
            pref_len = member.get('content_preferences', {}).get('preferred_length', 'medium')
            max_chars = {'short': 80, 'medium': 150, 'long': 250}.get(pref_len, 150)

            summary = si.item.summary[:max_chars]
            if len(si.item.summary) > max_chars:
                summary = summary.rsplit(' ', 1)[0] + '...'

            enriched_items.append({
                'scored_item': si,
                'headline': si.item.title[:70],
                'summary': summary,
                'category': si.matched_topic,
                'source': si.item.source_name,
                'language': si.item.language,
                'url': si.item.url,
            })

        enriched[key] = enriched_items
        log.info(f"  {member['nickname']}: {len(enriched_items)} enriched")

    # Generate trivia (mock for POC)
    enriched['trivia'] = _generate_trivia_mock(target_date)

    return enriched


def _mock_family_content() -> list:
    """Mock family-uploaded content for POC."""
    return [
        {'who': 'מיכל', 'text': 'שקיעה מדהימה מהמרפסת אתמול 🌅', 'type': 'text'},
        {'who': 'נימרוד', 'text': 'סשן קייט מטורף היום בחוף - הרוח הייתה מושלמת! 🪁', 'type': 'text'},
    ]


def _generate_trivia_mock(target_date: date) -> dict:
    """Mock trivia. Production: Claude generates this."""
    return {
        'content': f'ב-{target_date.day} באפריל 1961, יורי גגארין הפך לאדם הראשון בחלל. '
                   f'הוא הקיף את כדור הארץ פעם אחת ב-108 דקות בלבד.\n\n'
                   f'**חידה לצליל** 🧩: יש לך 8 מטבעות זהים לחלוטין, חוץ מאחד שכבד יותר. '
                   f'עם מאזניים (ובלי משקולות), מה המספר המינימלי של שקילות שצריך כדי למצוא אותו?',
    }


# ─── 5. BUILD HTML ───────────────────────────────────────────────────

NEWSLETTER_TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="הניוזלטר המשפחתי - {{ date_he }}">
<meta property="og:description" content="{{ og_description }}">
<title>הניוזלטר המשפחתי - {{ date_he }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #f5f3ef; color: #3a3a3a; line-height: 1.75; direction: rtl; padding: 12px;
  }
  .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 20px; overflow: hidden; box-shadow: 0 2px 24px rgba(0,0,0,0.06); }
  .header { background: linear-gradient(135deg, #e8f0e4 0%, #d4e4cf 100%); padding: 32px 24px 28px; text-align: center; }
  .header .logo { font-size: 11px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #6b8f5e; margin-bottom: 6px; }
  .header h1 { font-size: 24px; font-weight: 800; color: #2d3a28; margin-bottom: 4px; }
  .header .date { font-size: 13px; color: #6b8f5e; }
  .header .greeting { font-size: 15px; color: #4a6343; margin-top: 10px; font-style: italic; }
  .section { padding: 20px 24px 24px; border-bottom: 1px solid #f0ede8; }
  .section:last-of-type { border-bottom: none; }
  .section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
  .section-header .icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
  .section-header h2 { font-size: 16px; font-weight: 700; }
  .section-header .subtitle { font-size: 12px; color: #999; font-weight: 400; }
  .family-card { background: #fefbf6; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; border-right: 3px solid #f0c873; }
  .family-card .who { font-size: 12px; font-weight: 600; color: #c8942a; margin-bottom: 2px; }
  .family-card p { font-size: 14px; color: #555; }
  .card { background: #fafaf8; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; border-right: 3px solid #ddd; }
  .card:hover { background: #f5f4f0; }
  .card .cat { font-size: 10px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 3px; }
  .card h3 { font-size: 15px; font-weight: 700; line-height: 1.4; margin-bottom: 4px; }
  .card h3 a { color: #3a3a3a; text-decoration: none; }
  .card h3 a:hover { text-decoration: underline; }
  .card .excerpt { font-size: 13px; color: #777; line-height: 1.6; }
  .card .meta { margin-top: 6px; font-size: 11px; color: #aaa; }
  .lang-tag { font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 3px; background: #eee; color: #888; }
  .discovery-card { background: #faf7fd; border-radius: 12px; padding: 14px 16px; border: 1px dashed #d4c0ea; }
  .discovery-card .bridge { font-size: 12px; font-weight: 600; color: #7c50a8; margin-bottom: 6px; }
  .trivia-box { background: #fefbf6; border-radius: 12px; padding: 16px; border-right: 3px solid #daa520; font-size: 14px; color: #555; line-height: 1.8; }
  .feedback { background: #f9f8f5; padding: 28px 24px; text-align: center; border-top: 1px solid #f0ede8; }
  .feedback h3 { font-size: 17px; font-weight: 700; margin-bottom: 4px; }
  .feedback .sub { font-size: 13px; color: #999; margin-bottom: 16px; }
  .rating-row { display: flex; justify-content: center; gap: 10px; }
  .rate-btn { display: flex; flex-direction: column; align-items: center; gap: 3px; text-decoration: none; padding: 10px 14px; border-radius: 12px; background: #fff; border: 1px solid #e8e6e1; transition: all 0.15s; }
  .rate-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
  .rate-btn .emoji { font-size: 26px; }
  .rate-btn .label { font-size: 10px; color: #aaa; font-weight: 600; }
  .footer { padding: 16px 24px; text-align: center; font-size: 11px; color: #bbb; }
  .nimrod .card { border-right-color: #3b7dd8; } .nimrod .cat { color: #3b7dd8; } .nimrod .icon { background: #e6f0fa; }
  .michal .card { border-right-color: #2d8e5e; } .michal .cat { color: #2d8e5e; } .michal .icon { background: #e6f5ed; }
  .shaked .card { border-right-color: #6b3fa0; } .shaked .cat { color: #6b3fa0; } .shaked .icon { background: #ece6f5; }
  .maayan .card { border-right-color: #c4304a; } .maayan .cat { color: #c4304a; } .maayan .icon { background: #fce8ec; }
  .tzlil .card { border-right-color: #b8860b; } .tzlil .cat { color: #b8860b; } .tzlil .icon { background: #fef3e2; }
  .ltr { direction: ltr; text-align: left; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">Famely Neuslettr</div>
    <h1>בוקר טוב, {{ family_name }}!</h1>
    <div class="date">{{ date_he }}</div>
    <div class="greeting">"{{ greeting }}"</div>
  </div>

  {% if family_content %}
  <div class="section family">
    <div class="section-header">
      <div class="icon" style="background: #fef3e2;">📸</div>
      <h2>מהמשפחה שלנו</h2>
    </div>
    {% for fc in family_content %}
    <div class="family-card">
      <div class="who">{{ fc.who }} שיתפ/ה</div>
      <p>{{ fc.text }}</p>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  {% for ms in member_sections %}
  <div class="section {{ ms.css_class }}">
    <div class="section-header">
      <div class="icon">{{ ms.icon }}</div>
      <div>
        <h2>{{ ms.section_title }}</h2>
        <div class="subtitle">{{ ms.subtitle }}</div>
      </div>
    </div>
    {% for article in ms.articles %}
    <div class="card{% if article.language == 'en' %} ltr{% endif %}">
      <div class="cat">{{ article.category }}</div>
      <h3><a href="{{ article.url }}" target="_blank">{{ article.headline }}</a></h3>
      <div class="excerpt">{{ article.summary }}</div>
      <div class="meta">{{ article.source }} {% if article.language == 'en' %}<span class="lang-tag">EN</span>{% elif article.language == 'he' %}<span class="lang-tag">HE</span>{% endif %}</div>
    </div>
    {% endfor %}
    {% if not ms.articles %}
    <div class="card"><div class="excerpt" style="color:#bbb; text-align:center;">אין תכנים חדשים היום - נמשיך לחפש! 🔍</div></div>
    {% endif %}
  </div>
  {% endfor %}

  {% if discovery %}
  <div class="section">
    <div class="section-header">
      <div class="icon" style="background: #f0e6fa;">💡</div>
      <h2>גילוי היום</h2>
    </div>
    {% for d in discovery %}
    <div class="discovery-card">
      <div class="bridge">{{ d.bridge }}: "תראה מה מצאתי!"</div>
      <h3>{{ d.item.item.title }}</h3>
      <div class="excerpt" style="font-size:13px; color:#777;">{{ d.item.item.summary[:150] }}</div>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <div class="section">
    <div class="section-header">
      <div class="icon" style="background: #fef3e2;">📅</div>
      <h2>טריוויה והיום בהיסטוריה</h2>
    </div>
    <div class="trivia-box">{{ trivia_content | replace('\\n', '<br>') | safe }}</div>
  </div>

  <div class="feedback" id="feedback">
    <h3>איך היה היום?</h3>
    <div class="sub">ביחד נעשה את הניוזלטר טוב יותר</div>
    <div class="rating-row">
      <a href="#rate-5" class="rate-btn"><span class="emoji">😍</span><span class="label">מעולה</span></a>
      <a href="#rate-3" class="rate-btn"><span class="emoji">😊</span><span class="label">טוב</span></a>
      <a href="#rate-2" class="rate-btn"><span class="emoji">😐</span><span class="label">ככה ככה</span></a>
      <a href="#rate-1" class="rate-btn"><span class="emoji">👎</span><span class="label">לשפר</span></a>
    </div>
  </div>

  <div class="footer">
    Famely Neuslettr &copy; {{ year }} &middot; נבנה עם ❤️ ל{{ family_name }}<br>
    <small>POC v1.0 &middot; {{ items_count }} פריטים &middot; {{ sources_count }} מקורות</small>
  </div>
</div>
</body>
</html>"""


MEMBER_CONFIG = {
    'nimrod': {'icon': '⛵', 'title': 'הפינה של נימרוד', 'subtitle': 'שייט · קייט · קיימות · גידול מזון', 'css': 'nimrod'},
    'michal': {'icon': '🌿', 'title': 'הפינה של מיכל', 'subtitle': 'אדריכלות ירוקה · קפוארה · מיינדפולנס', 'css': 'michal'},
    'shaked': {'icon': '⚗️', 'title': "Shaked's Corner", 'subtitle': 'Sci-Fi · Chemistry · The Weird Stuff', 'css': 'shaked'},
    'maayan': {'icon': '🎪', 'title': 'הפינה של מעיין', 'subtitle': 'קרקס · אקרובטיקה · ביצוע', 'css': 'maayan'},
    'tzlil':  {'icon': '🧮', 'title': 'הפינה של צליל', 'subtitle': 'מתמטיקה · היסטוריה · כלכלה · ידע כללי', 'css': 'tzlil'},
}


def build_html(enriched: dict, family_config: dict, target_date: date) -> str:
    """Render the newsletter HTML."""
    log.info("🔨 BUILD: Rendering HTML newsletter...")

    weekdays = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
    months = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
              'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

    date_he = f"יום {weekdays[target_date.weekday()]}, {target_date.day} ב{months[target_date.month - 1]} {target_date.year}"

    # Build member sections
    member_sections = []
    items_count = 0
    members_order = ['nimrod', 'michal', 'shaked', 'maayan', 'tzlil']

    for mid in members_order:
        articles = enriched.get(mid, [])
        if not articles and mid not in enriched:
            continue

        cfg = MEMBER_CONFIG.get(mid, {})
        member_sections.append({
            'css_class': cfg.get('css', mid),
            'icon': cfg.get('icon', '📰'),
            'section_title': cfg.get('title', mid),
            'subtitle': cfg.get('subtitle', ''),
            'articles': articles,
        })
        items_count += len(articles)

    # OG description for WhatsApp preview
    top_headlines = []
    for ms in member_sections[:3]:
        for a in ms['articles'][:1]:
            top_headlines.append(a.get('headline', '')[:40])
    og_desc = ' | '.join(top_headlines) if top_headlines else 'הניוזלטר המשפחתי היומי'

    greetings = [
        "הרוח טובה היום - זמן לצאת למים ⛵",
        "כל יום מתחיל עם סיפור חדש",
        "היום יהיה יום מעולה!",
        "מה חדש בעולם? בואו נגלה ביחד",
    ]
    greeting = greetings[target_date.toordinal() % len(greetings)]

    template = Template(NEWSLETTER_TEMPLATE)
    html = template.render(
        family_name=family_config.get('family_name', 'המשפחה'),
        date_he=date_he,
        greeting=greeting,
        og_description=og_desc,
        family_content=enriched.get('family', []),
        member_sections=member_sections,
        discovery=enriched.get('discovery', []),
        trivia_content=enriched.get('trivia', {}).get('content', ''),
        year=target_date.year,
        items_count=items_count,
        sources_count=len(set(a.get('source', '') for ms in member_sections for a in ms['articles'])),
    )

    log.info(f"  HTML rendered: {len(html):,} bytes, {items_count} items")
    return html


# ─── 6. ARCHIVE ──────────────────────────────────────────────────────

def archive_results(conn: sqlite3.Connection, items: list[ContentItem],
                    enriched: dict, html_path: str, target_date: date):
    """Save everything to SQLite archive."""
    log.info("💾 ARCHIVE: Saving to database...")

    # Archive all fetched content
    for item in items:
        conn.execute("""
            INSERT OR IGNORE INTO content_archive (id, url, title, source_name, source_type,
                published_at, language, raw_summary, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.id, item.url, item.title, item.source_name, item.source_type,
              item.published, item.language, item.summary, json.dumps(item.tags)))

    # Archive newsletter
    total_items = sum(len(v) for k, v in enriched.items() if k not in ('family', 'trivia', 'discovery'))
    conn.execute("""
        INSERT OR REPLACE INTO newsletters (date, html_path, items_count)
        VALUES (?, ?, ?)
    """, (target_date.isoformat(), str(html_path), total_items))

    # Archive newsletter items
    for mid, articles in enriched.items():
        if mid in ('family', 'trivia', 'discovery'):
            continue
        for i, article in enumerate(articles):
            si = article.get('scored_item')
            if si:
                conn.execute("""
                    INSERT INTO newsletter_items (newsletter_date, content_id, member_id,
                        section, relevance_score, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (target_date.isoformat(), si.item.id, mid, 'personal', si.score, i))

    conn.commit()

    # Stats
    total_archived = conn.execute("SELECT COUNT(*) FROM content_archive").fetchone()[0]
    total_newsletters = conn.execute("SELECT COUNT(*) FROM newsletters").fetchone()[0]
    log.info(f"  Archive: {total_archived} total items, {total_newsletters} newsletters")


# ─── Helpers ─────────────────────────────────────────────────────────

def _xml_text(el, tag, ns=None):
    child = el.find(tag, ns) if ns else el.find(tag)
    return child.text.strip() if child is not None and child.text else None

def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _detect_lang(text: str) -> str:
    hebrew = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    alpha = sum(1 for c in text if c.isalpha())
    if alpha == 0:
        return 'unknown'
    return 'he' if hebrew / alpha > 0.3 else 'en'

def _extract_tags(item_el) -> list:
    tags = []
    for cat in item_el.findall('category'):
        if cat.text:
            tags.append(cat.text.strip())
    return tags[:5]


# ─── MAIN ────────────────────────────────────────────────────────────

def run(target_date: date = None, use_mock: bool = False):
    """Run the full POC pipeline."""
    target_date = target_date or date.today()

    print(f"""
╔══════════════════════════════════════════════════════╗
║  Famely Neuslettr - POC v1.0                        ║
║  Date: {target_date}                                ║
╚══════════════════════════════════════════════════════╝
""")

    # Load config
    with open(CONFIG_DIR / 'family.json', 'r', encoding='utf-8') as f:
        family = json.load(f)

    members = family['members']

    # Init DB
    conn = init_db(DB_PATH)

    # Step 1: Fetch
    if use_mock:
        log.info("📥 FETCH: Using mock data (--mock flag)")
        raw_items = _mock_items()
    else:
        raw_items = fetch_all_sources(members)

    if not raw_items:
        log.warning("⚠️  No items fetched! Using mock data as fallback.")
        raw_items = _mock_items()

    # Step 2: Score
    scored = score_items(raw_items, members)

    # Step 3: Curate
    curated = curate(scored, members)

    # Step 4: Generate
    enriched = generate_content(curated, members, target_date)

    # Step 5: Build HTML
    html = build_html(enriched, family, target_date)

    # Save HTML
    output_dir = DATA_DIR / 'newsletters'
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f'{target_date}.html'
    html_path.write_text(html, encoding='utf-8')

    # Step 6: Archive
    archive_results(conn, raw_items, enriched, str(html_path), target_date)
    conn.close()

    # Summary
    print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ Newsletter generated successfully!              ║
║                                                      ║
║  HTML: {str(html_path):<44} ║
║  DB:   {str(DB_PATH):<44} ║
║  Items: {len(raw_items)} fetched, {sum(len(v) for k,v in enriched.items() if k not in ('family','trivia','discovery')):>3} in newsletter         ║
╚══════════════════════════════════════════════════════╝
""")

    # Print WhatsApp message preview
    print("📱 WhatsApp message preview (would be sent to each member):")
    print("─" * 50)
    for member in members:
        if member.get('phone'):
            name = member['nickname']
            print(f"\nTo: {name}")
            print(f"  בוקר טוב {name}! ☀️")
            print(f"  📰 הניוזלטר המשפחתי - {target_date}")
            items = enriched.get(member['id'], [])
            for a in items[:2]:
                print(f"  → {a.get('headline', '')[:50]}")
            print(f"  👉 https://newsletter.family/{target_date}")
    print("─" * 50)

    return str(html_path)


def _mock_items() -> list[ContentItem]:
    """Generate mock items for testing without network."""
    return [
        ContentItem(id='m1', title='New Sailing Route Through Greek Islands Discovered',
                    url='https://example.com/sailing-greece', source_name='Yachting World',
                    source_type='rss', summary='A new sailing route through the Cyclades offers stunning anchorages and local tavernas. Perfect for family cruises with experienced skippers.',
                    language='en', tags=['sailing', 'greece', 'cruising']),
        ContentItem(id='m2', title='2026 Kite Foil Board Review - Best Gear for Light Wind',
                    url='https://example.com/kite-review', source_name='IKSURFMAG',
                    source_type='rss', summary='We tested 12 new kite foil boards for light wind conditions. The new North Seek model with hydrofoil integration stands out.',
                    language='en', tags=['kite', 'foil', 'gear review']),
        ContentItem(id='m3', title='Growing Food Year-Round in a 20sqm Garden',
                    url='https://example.com/permaculture', source_name='Permaculture Magazine',
                    source_type='rss', summary='A practical guide to year-round food production using raised beds, succession planting, and permaculture principles in a small urban garden.',
                    language='en', tags=['permaculture', 'growing', 'urban farming']),
        ContentItem(id='m4', title='The Greenest Building in the World Opens in Copenhagen',
                    url='https://example.com/green-building', source_name='ArchDaily',
                    source_type='rss', summary='A new building in Denmark produces more energy than it consumes, with a 3000sqm vertical garden and fully recycled materials.',
                    language='en', tags=['green architecture', 'sustainable', 'design']),
        ContentItem(id='m5', title='Capoeira Angola Festival 2026 - Bahia Highlights',
                    url='https://example.com/capoeira-festival', source_name='Open Capoeira',
                    source_type='rss', summary='The annual festival in Bahia featured workshops by leading mestres, incredible berimbau music, and a return to Angola roots.',
                    language='en', tags=['capoeira', 'angola', 'festival']),
        ContentItem(id='m6', title='CNAC France Opens 2027 Applications for Young Circus Artists',
                    url='https://example.com/cnac', source_name='CircusTalk',
                    source_type='rss', summary='CNAC, one of the world\'s leading circus schools, is accepting applications for their 2027 program. Open to 16+, auditions in July.',
                    language='en', tags=['circus', 'school', 'aerial', 'CNAC']),
        ContentItem(id='m7', title='New Catalyst Breaks Water Into Hydrogen at Room Temperature',
                    url='https://example.com/chemistry', source_name='Nature Chemistry',
                    source_type='rss', summary='ETH Zurich researchers developed a novel catalyst that could revolutionize green hydrogen production without requiring extreme heat.',
                    language='en', tags=['chemistry', 'catalyst', 'hydrogen']),
        ContentItem(id='m8', title='Royal Road Rising Stars: Progression Fantasy Breakouts',
                    url='https://example.com/royal-road', source_name='Royal Road',
                    source_type='rss', summary='A hard sci-fi progression fantasy about a chemist trapped in a simulated universe is trending at #3. New Dungeon Crawler Carl chapter dropped.',
                    language='en', tags=['sci-fi', 'progression fantasy', 'web novel']),
        ContentItem(id='m9', title='The Mathematical Beauty of Tessellations in Architecture',
                    url='https://example.com/math-arch', source_name='Numberphile',
                    source_type='rss', summary='How mathematical tessellation patterns are used in modern architecture, from the Alhambra to contemporary parametric design.',
                    language='en', tags=['math', 'architecture', 'geometry', 'tessellation']),
        ContentItem(id='m10', title='Mindfulness for Busy Parents: 5-Minute Morning Practice',
                    url='https://example.com/mindful', source_name='Mindful.org',
                    source_type='rss', summary='A simple breathing exercise based on new research, designed for busy mornings. Even 5 minutes can shift your entire day.',
                    language='en', tags=['mindfulness', 'meditation', 'parents']),
        ContentItem(id='m11', title='How Money Was Invented: The Story of Lydian Coins',
                    url='https://example.com/money-history', source_name='TED-Ed',
                    source_type='rss', summary='2600 years ago, a very wealthy king (Croesus) invented the first coin. How did this change the world forever?',
                    language='en', tags=['history', 'economics', 'money']),
        ContentItem(id='m12', title='Claude Code Gets Multi-Agent Orchestration',
                    url='https://example.com/claude-update', source_name='Anthropic Blog',
                    source_type='rss', summary='Small but significant update: you can now manage multiple agents in parallel from Claude Code.',
                    language='en', tags=['AI', 'Claude', 'agents', 'developer tools']),
    ]


# ─── CLI ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Famely Neuslettr POC v1.0')
    parser.add_argument('--date', type=str, default=None, help='Target date (YYYY-MM-DD)')
    parser.add_argument('--mock', action='store_true', help='Use mock data (no network)')
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today()
    html_path = run(target, use_mock=args.mock)
