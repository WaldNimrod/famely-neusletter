"""
Famely Neuslettr — M2 Scanner
Fetches content from sources → NCI[] per LOD400 §4.
Uses stdlib xml.etree (no feedparser), requests, BeautifulSoup.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .models import NCI, SourceConfig, ScanRule, Settings, create_nci

logger = logging.getLogger('famely.m2')

TIMEOUT = 30  # seconds per source
USER_AGENT = "FamelyNeuslettr/1.0 (+https://nimrod.bio/newsletter)"

# YouTube channel ID regex from @handle pages
YT_CHANNEL_RE = re.compile(r'"externalId"\s*:\s*"(UC[\w-]+)"')
YT_RSS_TMPL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


def scan_all(scan_rules: list[ScanRule], settings: Settings) -> list[NCI]:
    """Run all fetchers, return combined NCI list.
    Never raises — individual source failures are logged and skipped."""
    all_ncis = []
    for rule in scan_rules:
        source = rule.source
        if source.status != 'active':
            continue
        try:
            start = time.time()
            if source.type == 'rss':
                ncis = fetch_rss(source, rule.keywords)
            elif source.type == 'youtube':
                ncis = fetch_youtube(source, rule.keywords)
            elif source.type in ('web', 'api'):
                ncis = fetch_web(source, rule.keywords)
            else:
                logger.warning(f"Unknown source type '{source.type}' for {source.name}")
                ncis = []
            elapsed = int((time.time() - start) * 1000)
            logger.info(f"[M2] {source.name}: {len(ncis)} items in {elapsed}ms")
            all_ncis.extend(ncis)
        except Exception as e:
            logger.error(f"[M2] Failed to scan {source.name}: {e}")
            continue

    if not all_ncis:
        logger.critical("[M2] All sources returned 0 items")

    return all_ncis


def fetch_rss(source: SourceConfig, keywords: list[str]) -> list[NCI]:
    """Parse RSS/Atom feed using stdlib xml.etree. Returns NCI list."""
    try:
        resp = requests.get(source.url, timeout=TIMEOUT,
                           headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[M2] RSS fetch failed for {source.name}: {e}")
        return []

    return _parse_feed_xml(resp.content, source, keywords)


def _parse_feed_xml(content: bytes, source: SourceConfig, keywords: list[str]) -> list[NCI]:
    """Parse RSS 2.0 or Atom XML into NCI list."""
    ncis = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        logger.error(f"[M2] XML parse error for {source.name}: {e}")
        return []

    # Detect Atom namespace
    ns = {}
    if root.tag.startswith('{'):
        atom_ns = root.tag.split('}')[0] + '}'
        ns['atom'] = atom_ns.strip('{}')

    # Try RSS 2.0 first
    items = root.findall('.//item')

    if items:
        for item in items[:20]:  # max 20 per source
            title = _text(item, 'title') or ''
            link = _text(item, 'link') or ''
            desc = _text(item, 'description') or ''
            pub_date = _text(item, 'pubDate') or ''
            # Clean HTML from description
            desc_clean = _strip_html(desc)[:5000]
            # Extract image
            image_url = _extract_image_from_html(desc)
            # Detect language
            lang = _detect_language(title + ' ' + desc_clean)

            if link:
                ncis.append(create_nci(
                    title=title,
                    url=link,
                    source_name=source.name,
                    source_type='rss',
                    source_url=source.url,
                    source_trust=source.trust_score,
                    published_at=_parse_date(pub_date),
                    raw_text=desc_clean,
                    tags=_extract_tags(title + ' ' + desc_clean, keywords),
                    language=lang,
                    image_url=image_url,
                ))
    else:
        # Try Atom format
        atom_ns = ns.get('atom', 'http://www.w3.org/2005/Atom')
        entries = root.findall(f'{{{atom_ns}}}entry')
        if not entries:
            entries = root.findall('.//entry')

        for entry in entries[:20]:
            title = _text_ns(entry, 'title', atom_ns) or ''
            link_el = entry.find(f'{{{atom_ns}}}link')
            if link_el is None:
                link_el = entry.find('link')
            link = link_el.get('href', '') if link_el is not None else ''
            summary = _text_ns(entry, 'summary', atom_ns) or _text_ns(entry, 'content', atom_ns) or ''
            published = _text_ns(entry, 'published', atom_ns) or _text_ns(entry, 'updated', atom_ns) or ''
            desc_clean = _strip_html(summary)[:5000]
            lang = _detect_language(title + ' ' + desc_clean)

            if link:
                ncis.append(create_nci(
                    title=title,
                    url=link,
                    source_name=source.name,
                    source_type='rss',
                    source_url=source.url,
                    source_trust=source.trust_score,
                    published_at=_parse_date(published),
                    raw_text=desc_clean,
                    tags=_extract_tags(title + ' ' + desc_clean, keywords),
                    language=lang,
                ))

    return ncis


def fetch_web(source: SourceConfig, keywords: list[str]) -> list[NCI]:
    """Scrape web page for content items using requests + BeautifulSoup."""
    try:
        resp = requests.get(source.url, timeout=TIMEOUT,
                           headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[M2] Web fetch failed for {source.name}: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    ncis = []

    # Strategy: find article-like elements
    articles = soup.find_all('article')
    if not articles:
        # Fallback: look for common patterns
        articles = soup.find_all(['div', 'li'], class_=re.compile(
            r'(post|article|entry|story|item|card)', re.I))

    for art in articles[:15]:
        # Extract title
        title_el = art.find(['h1', 'h2', 'h3', 'h4', 'a'])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if len(title) < 5:
            continue

        # Extract link
        link_el = art.find('a', href=True)
        if not link_el:
            continue
        href = link_el['href']
        if href.startswith('/'):
            parsed = urlparse(source.url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"

        # Extract excerpt
        excerpt_el = art.find(['p', 'div'], class_=re.compile(r'(excerpt|summary|desc|content)', re.I))
        excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ''
        if not excerpt:
            # Fallback: first <p> in article
            p = art.find('p')
            excerpt = p.get_text(strip=True) if p else ''

        # Extract image
        img = art.find('img', src=True)
        image_url = img['src'] if img else None
        if image_url and image_url.startswith('/'):
            parsed = urlparse(source.url)
            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"

        lang = _detect_language(title + ' ' + excerpt)

        ncis.append(create_nci(
            title=title,
            url=href,
            source_name=source.name,
            source_type='web',
            source_url=source.url,
            source_trust=source.trust_score,
            published_at=datetime.now(timezone.utc).isoformat(),
            raw_text=excerpt[:5000],
            tags=_extract_tags(title + ' ' + excerpt, keywords),
            language=lang,
            image_url=image_url,
        ))

    return ncis


def fetch_youtube(source: SourceConfig, keywords: list[str]) -> list[NCI]:
    """Fetch latest videos via YouTube RSS feed (no API key needed)."""
    # Extract channel ID from URL or handle
    channel_id = _resolve_youtube_channel_id(source.url)
    if not channel_id:
        logger.warning(f"[M2] Could not resolve YouTube channel ID for {source.name}")
        return []

    rss_url = YT_RSS_TMPL.format(channel_id)
    try:
        resp = requests.get(rss_url, timeout=TIMEOUT,
                           headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[M2] YouTube RSS failed for {source.name}: {e}")
        return []

    return _parse_feed_xml(resp.content, source, keywords)


def _resolve_youtube_channel_id(url: str) -> Optional[str]:
    """Extract or resolve YouTube channel ID from URL."""
    # Direct channel ID URL
    if '/channel/UC' in url:
        match = re.search(r'/channel/(UC[\w-]+)', url)
        return match.group(1) if match else None

    # @handle format — need to fetch page and extract channel ID
    if '/@' in url or '/c/' in url or '/user/' in url:
        try:
            resp = requests.get(url, timeout=TIMEOUT,
                               headers={"User-Agent": USER_AGENT})
            match = YT_CHANNEL_RE.search(resp.text)
            if match:
                return match.group(1)
            # Try meta tag
            soup = BeautifulSoup(resp.text, 'html.parser')
            meta = soup.find('meta', {'itemprop': 'channelId'})
            if meta:
                return meta.get('content')
            # Try link canonical
            link = soup.find('link', {'rel': 'canonical'})
            if link and '/channel/' in link.get('href', ''):
                m = re.search(r'/channel/(UC[\w-]+)', link['href'])
                return m.group(1) if m else None
        except Exception as e:
            logger.warning(f"[M2] Failed to resolve YouTube channel: {e}")
    return None


# ─── Helper Functions ─────────────────────────────────────────

def _text(element, tag: str) -> Optional[str]:
    """Get text of child element."""
    el = element.find(tag)
    return el.text.strip() if el is not None and el.text else None


def _text_ns(element, tag: str, ns: str) -> Optional[str]:
    """Get text of namespaced child element."""
    el = element.find(f'{{{ns}}}{tag}')
    if el is None:
        el = element.find(tag)
    return el.text.strip() if el is not None and el.text else None


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text).strip()


def _extract_image_from_html(html: str) -> Optional[str]:
    """Extract first image URL from HTML content."""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)', html)
    return match.group(1) if match else None


def _detect_language(text: str) -> str:
    """Simple Hebrew detection based on character frequency."""
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    total = len(text.strip())
    if total == 0:
        return "en"
    return "he" if hebrew_chars / total > 0.1 else "en"


def _extract_tags(text: str, keywords: list[str]) -> list[str]:
    """Find which keywords appear in text."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


def _parse_date(date_str: str) -> str:
    """Best-effort parse of date string to ISO8601."""
    if not date_str:
        return datetime.now(timezone.utc).isoformat()

    # Common RSS date formats
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue

    return datetime.now(timezone.utc).isoformat()


# ─── Mock Scanner (for --mock mode) ──────────────────────────

def generate_mock_ncis() -> list[NCI]:
    """Generate realistic mock NCIs for testing without network."""
    now = datetime.now(timezone.utc).isoformat()
    mocks = [
        # Nimrod - sailing
        create_nci("Mediterranean Sailing Routes: 2026 Guide", "https://example.com/sailing-2026",
                   "Yachting World", "rss", "https://yachtingworld.com/feed", 0.8, now,
                   "A comprehensive guide to the best sailing routes across the Mediterranean for 2026, including new marinas and anchorages.",
                   ["sailing", "ים תיכון", "הפלגה", "skipper"], "en"),
        create_nci("New Kite Foil Technology Revolutionizes Racing", "https://example.com/kite-foil",
                   "IKSURFMAG", "rss", "https://iksurfmag.com/feed", 0.8, now,
                   "The latest hydrofoil technology is changing competitive kiteboarding, with new designs reaching speeds of 40+ knots.",
                   ["kite", "foil", "kiteboarding", "hydrofoil"], "en"),
        create_nci("Urban Permaculture: Growing Food in Small Spaces", "https://example.com/permaculture",
                   "Permaculture Magazine", "rss", "https://permaculture.co.uk/feed", 0.8, now,
                   "How families are transforming balconies and small gardens into productive food forests using permaculture principles.",
                   ["פרמקלצ'ר", "גידול ירקות", "urban farming", "sustainable"], "en"),
        # Michal - architecture
        create_nci("בנייה ירוקה: הפרויקט שמשנה את תל אביב", "https://example.com/green-build-tlv",
                   "ArchDaily", "rss", "https://archdaily.com/feed", 0.9, now,
                   "פרויקט בנייה ירוקה חדשני בלב תל אביב משלב טכנולוגיות passive house עם עיצוב מקומי. הפרויקט צפוי לחסוך 60% באנרגיה.",
                   ["אדריכלות ירוקה", "passive house", "sustainable architecture", "green building"], "he"),
        create_nci("קפוארה אנגולה: סדנה בינלאומית בישראל", "https://example.com/capoeira-israel",
                   "ABADÁ Capoeira Israel", "web", "https://abadacapoeiraisrael.org.il", 0.7, now,
                   "סדנת קפוארה בינלאומית תתקיים בחודש הבא עם מאסטרים מברזיל. הסדנה פתוחה לכל הרמות.",
                   ["קפוארה", "capoeira angola", "roda"], "he"),
        create_nci("Mindfulness for Busy Parents: 5-Minute Practices", "https://example.com/mindfulness-parents",
                   "Mindful.org", "web", "https://mindful.org", 0.7, now,
                   "Quick mindfulness techniques designed for parents who struggle to find time for meditation practice.",
                   ["mindfulness", "meditation", "מדיטציה"], "en"),
        # Shaked - sci-fi & chemistry
        create_nci("Top 10 Progression Fantasy Releases This Month", "https://example.com/prog-fantasy",
                   "Royal Road", "web", "https://royalroad.com", 0.7, now,
                   "The latest trending progression fantasy novels on Royal Road, including new chapters of Dungeon Crawler Carl.",
                   ["progression fantasy", "LitRPG", "Royal Road", "web novels", "Dungeon Crawler Carl"], "en"),
        create_nci("Breakthrough in Organic Synthesis: New Catalyst Design", "https://example.com/catalyst",
                   "Nature Chemistry", "rss", "https://nature.com/nchem.rss", 0.95, now,
                   "Researchers have developed a novel catalyst that enables previously impossible organic reactions at room temperature.",
                   ["organic chemistry", "chemistry", "molecular biology", "research papers"], "en"),
        # יויו - circus
        create_nci("הקרקס הצרפתי CNAC מכריז על מועדי אודישנים 2027", "https://example.com/cnac-auditions",
                   "CircusTalk", "web", "https://circustalk.com", 0.7, now,
                   "בית הספר הלאומי לאומנויות הקרקס בצרפת פרסם את תאריכי האודישנים לשנת הלימודים 2027. ההרשמה נפתחת בקיץ.",
                   ["קרקס", "CNAC", "circus school", "performance", "aerial"], "he"),
        create_nci("Aerial Silks Tutorial: Advanced Drops for Intermediate", "https://example.com/aerial-silks",
                   "CircusTalk", "web", "https://circustalk.com", 0.7, now,
                   "New video tutorial covering advanced aerial silks drops with detailed safety tips.",
                   ["aerial silks", "אקרובטיקה", "cirque", "performance"], "en"),
        # צליל - math & history
        create_nci("Numberphile: The Unsolved Problem Worth $1 Million", "https://example.com/numberphile-million",
                   "Numberphile", "youtube", "https://youtube.com/@numberphile", 0.9, now,
                   "Numberphile explores one of the Millennium Prize Problems and why it has stumped mathematicians for decades.",
                   ["math puzzles", "mathematics", "Numberphile"], "en"),
        create_nci("TED-Ed: How Ancient Trade Routes Shaped Modern Economy", "https://example.com/ted-trade",
                   "TED-Ed", "youtube", "https://youtube.com/@TEDEd", 0.9, now,
                   "Exploring how the Silk Road and other ancient trade routes created the foundations of modern global economics.",
                   ["history", "economics", "trade", "TED-Ed"], "en"),
        create_nci("Veritasium: Why Geometry is Everywhere", "https://example.com/veritasium-geo",
                   "Veritasium", "youtube", "https://youtube.com/@veritasium", 0.9, now,
                   "A deep dive into how geometric patterns appear throughout nature, from honeycombs to crystal structures.",
                   ["geometry", "math", "Veritasium", "מדע"], "en"),
    ]
    logger.info(f"[M2-MOCK] Generated {len(mocks)} mock NCIs")
    return mocks
