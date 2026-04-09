"""
Famely Neuslettr — M6 Feedback + Submissions
WhatsApp webhook handler per LOD400 §8.
Uses stdlib http.server (no FastAPI dependency in Phase 1 dev).
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

from .models import FamilySubmission, FeedbackEvent, FamilyConfig
from .db import Database
from .m1_profiles import load_profiles, load_settings

logger = logging.getLogger('famely.m6')

# Size limits
MAX_IMAGE_SIZE = 16 * 1024 * 1024   # 16MB
MAX_VIDEO_SIZE = 64 * 1024 * 1024   # 64MB
MAX_DOC_SIZE = 32 * 1024 * 1024     # 32MB


def identify_sender(phone: str, family: FamilyConfig) -> Optional[str]:
    """Match phone number to member_id. Returns None if unknown."""
    # Normalize phone: strip spaces, ensure +972 prefix
    phone = phone.replace(' ', '').replace('-', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    for member in family.members:
        if not member.phone:
            continue
        member_phone = member.phone.replace(' ', '').replace('-', '')
        if not member_phone.startswith('+'):
            member_phone = '+' + member_phone
        if phone == member_phone or phone.endswith(member_phone[-9:]):
            return member.id
    return None


def is_survey_response(member_id: str, message: str, db: Database) -> bool:
    """True if survey was sent to this member recently and message is short."""
    if len(message) > 200:  # survey responses are typically short
        return False
    return db.has_recent_survey(member_id, hours=6)


def handle_submission(member_id: str, message_type: str, content_text: Optional[str],
                       link_url: Optional[str], media_url: Optional[str],
                       media_mime: Optional[str], media_size: Optional[int],
                       db: Database, family: FamilyConfig) -> dict:
    """Process family submission. Returns response message."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Check media size limits
    if media_size:
        limit = MAX_IMAGE_SIZE
        if media_mime and 'video' in media_mime:
            limit = MAX_VIDEO_SIZE
        elif media_mime and ('pdf' in media_mime or 'document' in media_mime):
            limit = MAX_DOC_SIZE

        if media_size > limit:
            member = _get_member(member_id, family)
            if member and member.language_preference == 'en':
                return {'reply': "File too large! Max: 16MB images, 64MB video, 32MB PDF."}
            return {'reply': "הקובץ גדול מדי 😅 ניתן לשלוח עד 16MB תמונות, 64MB וידאו, 32MB PDF."}

    # Download media if present
    media_local_path = None
    if media_url:
        try:
            media_local_path = _download_media(media_url, today, member_id)
        except Exception as e:
            logger.warning(f"[M6] Media download failed: {e}")
            member = _get_member(member_id, family)
            if member and member.language_preference == 'en':
                return {'reply': "Got it! (without media — try again)"}
            # Continue without media

    # Create submission
    sub = FamilySubmission(
        id=str(uuid.uuid4()),
        member_id=member_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        message_type=message_type,
        content_text=content_text,
        media_local_path=media_local_path,
        media_mime_type=media_mime,
        media_size_bytes=media_size,
        link_url=link_url,
        status='received',
    )

    db.insert_submission(sub)
    logger.info(f"[M6] Submission received from {member_id}: {message_type}")

    # Send confirmation
    member = _get_member(member_id, family)
    if member and member.language_preference == 'en':
        return {'reply': "Got it! 📰 Will be published in the next edition."}
    return {'reply': "התקבל! 📰 יפורסם בגליון הקרוב."}


def handle_survey_response(member_id: str, message: str, db: Database,
                            family: FamilyConfig) -> dict:
    """Process survey response."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    event = FeedbackEvent(
        member_id=member_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        type='survey',
        newsletter_date=today,
        value=message,
    )
    db.insert_feedback(event)
    logger.info(f"[M6] Survey response from {member_id}")

    member = _get_member(member_id, family)
    if member and member.language_preference == 'en':
        return {'reply': "Thanks for the feedback! 🙏"}
    return {'reply': "תודה על המשוב! 🙏"}


def _get_member(member_id, family):
    for m in family.members:
        if m.id == member_id:
            return m
    return None


def _download_media(url: str, date: str, member_id: str) -> str:
    """Download media file and save locally."""
    import requests

    media_dir = Path(f"data/submissions/{date}")
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{member_id}_{uuid.uuid4().hex[:8]}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    # Determine extension from content type
    ct = resp.headers.get('content-type', '')
    ext = '.bin'
    if 'jpeg' in ct or 'jpg' in ct:
        ext = '.jpg'
    elif 'png' in ct:
        ext = '.png'
    elif 'mp4' in ct:
        ext = '.mp4'
    elif 'pdf' in ct:
        ext = '.pdf'

    filepath = media_dir / f"{filename}{ext}"
    filepath.write_bytes(resp.content)
    return str(filepath)


# ─── Webhook Server (stdlib, for dev) ────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for WhatsApp webhooks (dev mode)."""

    family = None
    db = None

    def do_POST(self):
        if self.path != '/webhook/whatsapp':
            self.send_response(404)
            self.end_headers()
            return

        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)

        try:
            data = json.loads(body)
            self._process_webhook(data)
        except Exception as e:
            logger.error(f"[M6] Webhook error: {e}")

        # Always respond 200 within 5 seconds
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "healthy"}')

    def _process_webhook(self, data):
        """Route incoming message to submission or survey handler."""
        # Extract Twilio WhatsApp format
        phone = data.get('From', '').replace('whatsapp:', '')
        message = data.get('Body', '')
        media_url = data.get('MediaUrl0')
        media_mime = data.get('MediaContentType0')
        media_size = None
        num_media = int(data.get('NumMedia', 0))

        if not phone:
            return

        member_id = identify_sender(phone, self.family)
        if not member_id:
            logger.info(f"[M6] Unknown sender: {phone}")
            return

        # Route
        if is_survey_response(member_id, message, self.db):
            result = handle_survey_response(member_id, message, self.db, self.family)
        else:
            # Determine message type
            msg_type = 'text'
            link_url = None
            if num_media > 0:
                if media_mime and 'image' in media_mime:
                    msg_type = 'image'
                elif media_mime and 'video' in media_mime:
                    msg_type = 'video'
                else:
                    msg_type = 'document'
            elif message and ('http://' in message or 'https://' in message):
                msg_type = 'link'
                # Extract URL
                import re
                urls = re.findall(r'https?://\S+', message)
                link_url = urls[0] if urls else None

            result = handle_submission(
                member_id, msg_type, message, link_url,
                media_url, media_mime, media_size, self.db, self.family
            )

        logger.info(f"[M6] Reply to {member_id}: {result.get('reply', '')}")

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def run_webhook_server(host: str = '0.0.0.0', port: int = 8443,
                        config_dir: str = 'config/', db_path: str = 'data/famely.db'):
    """Start the webhook HTTP server."""
    family = load_profiles(config_dir)
    db = Database(db_path)

    WebhookHandler.family = family
    WebhookHandler.db = db

    server = HTTPServer((host, port), WebhookHandler)
    logger.info(f"[M6] Webhook server running on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[M6] Webhook server stopped")
    finally:
        db.close()
