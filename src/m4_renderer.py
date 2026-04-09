"""
Famely Neuslettr — M4 Renderer
Jinja2 template → HTML per LOD400 §6.
"""

import logging
from pathlib import Path
from dataclasses import asdict

from jinja2 import Environment, FileSystemLoader

from .models import NEO
from .db import Database

logger = logging.getLogger('famely.m4')


def render(neo: NEO, template_path: str = "templates/",
           db: Database = None) -> str:
    """Render NEO to HTML string using Jinja2 template."""
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=True,
    )

    template = env.get_template("newsletter.html.j2")

    # Calculate edition number from DB
    edition_number = 1
    if db:
        try:
            row = db.conn.execute(
                "SELECT COUNT(*) as cnt FROM newsletters WHERE status != 'build_failed'"
            ).fetchone()
            edition_number = (row['cnt'] or 0)
        except Exception:
            pass

    # Convert NEO to template-friendly dict
    neo_dict = asdict(neo) if hasattr(neo, '__dataclass_fields__') else neo.__dict__

    html = template.render(
        neo=neo,
        edition_number=edition_number,
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
