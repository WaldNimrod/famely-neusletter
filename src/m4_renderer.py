"""
Family Newsletter — M4 Renderer
Jinja2 template → HTML per LOD400 §6.
"""

import logging
import re
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from .models import NEO
from .db import Database

logger = logging.getLogger('famely.m4')

# Character schedule for monthly rotation
CHARACTER_SCHEDULE = {
    '2026-04': {'name': 'Cat in the Hat', 'emoji': '🎩', 'style': 'Dr. Seuss'},
    '2026-05': {'name': 'Popeye', 'emoji': '💪', 'style': 'Classic Popeye strip'},
}

POSE_EMOJI_MAP = {
    'hero-greeting': '🎩',
    'reading': '📖',
    'thinking': '🤔',
    'pointing': '👉',
    'goodbye': '👋',
    'icon': '🎩',
}


def strip_markdown(text: str) -> str:
    """
    Convert basic markdown to HTML.

    - Removes heading markers (#, ##, etc.)
    - Converts **bold** to <strong>bold</strong>
    - Converts *italic* to <em>italic</em>
    - Strips excess newlines
    """
    if not text:
        return ''

    # Remove heading markers (# at start of lines)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    # Convert **bold** to <strong>bold</strong>
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', text)

    # Convert *italic* to <em>italic</em>
    text = re.sub(r'\*([^\*]+)\*', r'<em>\1</em>', text)

    # Strip excess newlines (more than 2 in a row)
    text = re.sub(r'\n\n+', '\n\n', text)

    return text.strip()


def get_character_html(pose: str, month: str = None) -> str:
    """
    Get character HTML image or emoji fallback.

    Args:
        pose: Character pose name (e.g., 'hero-greeting', 'reading')
        month: Month in YYYY-MM format. Defaults to current month.

    Returns:
        HTML img tag if asset exists, otherwise emoji fallback.
    """
    if month is None:
        month = datetime.now().strftime('%Y-%m')

    # Check if character asset exists
    asset_path = Path(f"assets/characters/{month}/{pose}.png")
    if asset_path.exists():
        return f'<img src="assets/characters/{month}/{pose}.png" alt="{pose}" class="character-img character-{pose}">'

    # Fallback to emoji
    emoji = POSE_EMOJI_MAP.get(pose, '🎭')
    return f'<span class="character-emoji character-{pose}">{emoji}</span>'


def render(neo: NEO, template_path: str = "templates/",
           db: Database = None) -> str:
    """Render NEO to HTML string using Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=True,
    )

    # Register markdown filter
    env.filters['md'] = strip_markdown

    template = env.get_template("newsletter.html.j2")

    # Calculate edition number from DB (weekly editions)
    edition_number = 1
    if db:
        try:
            row = db.conn.execute(
                "SELECT COUNT(*) as cnt FROM newsletters WHERE status != 'build_failed'"
            ).fetchone()
            edition_number = (row['cnt'] or 0)
        except Exception:
            pass

    # Get character metadata for current month
    current_month = datetime.now().strftime('%Y-%m')
    character_meta = CHARACTER_SCHEDULE.get(current_month, {
        'name': 'Character',
        'emoji': '🎭',
        'style': 'Custom'
    })

    # Convert NEO to template-friendly dict
    neo_dict = asdict(neo) if hasattr(neo, '__dataclass_fields__') else neo.__dict__

    html = template.render(
        neo=neo,
        edition_number=edition_number,
        character_html=get_character_html,
        character_name=character_meta['name'],
        character_emoji=character_meta['emoji'],
        character_style=character_meta['style'],
        current_month=current_month,
    )

    # Validate output
    if len(html) < 1000:
        logger.critical(f"[M4] HTML too small ({len(html)}B). Aborting.")
        raise RuntimeError(f"HTML too small ({len(html)}B). Something is wrong.")

    logger.info(f"[M4] Rendered HTML: {len(html)} bytes, edition #{edition_number}")
    return html


def save_html(html: str, date: str, output_dir: str = "data/archive/html/") -> str:
    """Save HTML to disk. Returns file path."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{date}.html"
    file_path.write_text(html, encoding='utf-8')
    logger.info(f"[M4] Saved HTML to {file_path}")
    return str(file_path)
