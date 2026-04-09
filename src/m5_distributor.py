"""
Famely Neuslettr — M5 Distributor
FTP upload + WhatsApp/Email send per LOD400 §7.
"""

import ftplib
import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from .models import NEO, FamilyConfig, Settings, MemberProfile, FTPUploadError

logger = logging.getLogger('famely.m5')


@dataclass
class DistributionResult:
    public_url: str
    ftp_success: bool
    member_results: list[dict]  # [{member_id, channel, success, error}]


def distribute(html_path: str, neo: NEO, family: FamilyConfig,
               settings: Settings, mock: bool = False) -> DistributionResult:
    """Main distribution function per LOD400 §7."""
    results = []

    # Step 1: FTP upload
    if mock:
        public_url = f"https://nimrod.bio/newsletter/{neo.date}/index.html"
        ftp_ok = True
        logger.info(f"[M5-MOCK] Skipping FTP, URL: {public_url}")
    else:
        try:
            public_url = ftp_upload(html_path, neo.date, settings)
            ftp_ok = True
        except FTPUploadError as e:
            logger.critical(f"[M5] FTP upload failed: {e}")
            return DistributionResult(
                public_url='', ftp_success=False, member_results=[{
                    'member_id': 'admin', 'channel': 'none',
                    'success': False, 'error': str(e),
                }]
            )

    # Step 2: Verify URL (skip in mock)
    if not mock:
        try:
            resp = requests.get(public_url, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[M5] URL verification failed: HTTP {resp.status_code}")
                # Retry FTP once
                try:
                    ftp_upload(html_path, neo.date, settings)
                    resp = requests.get(public_url, timeout=15)
                    if resp.status_code != 200:
                        raise FTPUploadError(f"URL still returns {resp.status_code}")
                except Exception:
                    ftp_ok = False
        except requests.RequestException:
            logger.warning("[M5] URL verification skipped (network error)")

    # Step 3: Send messages to each member
    for member in family.members:
        if mock:
            results.append({
                'member_id': member.id, 'channel': 'mock',
                'success': True, 'error': None,
            })
            logger.info(f"[M5-MOCK] Mock send to {member.nickname_newsletter}")
            continue

        # Try WhatsApp first
        if settings.distribution.get('primary_channel') == 'whatsapp' and member.phone:
            success = send_whatsapp(member, neo, public_url, settings)
            if success:
                results.append({
                    'member_id': member.id, 'channel': 'whatsapp',
                    'success': True, 'error': None,
                })
                continue

        # Fallback to email
        if member.email:
            success = send_email(member, neo, public_url, settings)
            results.append({
                'member_id': member.id,
                'channel': 'email',
                'success': success,
                'error': None if success else 'Email send failed',
            })
        else:
            results.append({
                'member_id': member.id, 'channel': 'none',
                'success': False, 'error': 'No phone or email',
            })

    return DistributionResult(
        public_url=public_url,
        ftp_success=ftp_ok,
        member_results=results,
    )


def ftp_upload(html_path: str, date: str, settings: Settings) -> str:
    """Upload HTML to FTP server. Returns public URL."""
    host = os.environ.get('FTP_HOST', '')
    user = os.environ.get('FTP_USER', '')
    passwd = os.environ.get('FTP_PASS', '')
    remote_base = settings.ftp.get('remote_path', '/newsletter')
    retry_count = settings.ftp.get('retry_count', 3)
    retry_delay = settings.ftp.get('retry_delay_seconds', 10)

    remote_dir = f"{remote_base}/{date}"
    remote_file = f"{remote_dir}/index.html"

    for attempt in range(retry_count):
        try:
            ftp = ftplib.FTP(host, timeout=30)
            ftp.login(user, passwd)

            # Create directory
            try:
                ftp.mkd(remote_dir)
            except ftplib.error_perm:
                pass  # directory exists

            # Upload
            with open(html_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)

            ftp.quit()

            url_base = settings.newsletter.get('url_base', 'https://nimrod.bio/newsletter')
            public_url = f"{url_base}/{date}/index.html"
            logger.info(f"[M5] FTP upload success: {public_url}")
            return public_url

        except Exception as e:
            logger.warning(f"[M5] FTP attempt {attempt+1} failed: {e}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
            continue

    raise FTPUploadError(f"FTP upload failed after {retry_count} retries")


def send_whatsapp(member: MemberProfile, neo: NEO, public_url: str,
                   settings: Settings) -> bool:
    """Send WhatsApp message via Twilio."""
    try:
        sid = os.environ.get('TWILIO_SID')
        token = os.environ.get('TWILIO_TOKEN')
        from_number = os.environ.get('TWILIO_FROM')

        if not all([sid, token, from_number, member.phone]):
            return False

        # Build personalized message
        msg = _build_message(member, neo, public_url)

        # Send via Twilio API
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={
                'From': from_number,
                'To': f"whatsapp:{member.phone}",
                'Body': msg,
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info(f"[M5] WhatsApp sent to {member.nickname_newsletter}")
        return True

    except Exception as e:
        logger.error(f"[M5] WhatsApp failed for {member.id}: {e}")
        return False


def send_email(member: MemberProfile, neo: NEO, public_url: str,
               settings: Settings) -> bool:
    """Send email via SMTP."""
    try:
        smtp_host = os.environ.get('SMTP_HOST', '')
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')
        smtp_from = os.environ.get('SMTP_FROM', 'famely@nimrod.bio')

        if not member.email:
            return False

        msg_text = _build_message(member, neo, public_url)
        subject = f"📰 הניוזלטר המשפחתי — {neo.date}"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Famely Neuslettr <{smtp_from}>"
        msg['To'] = member.email

        # Plain text
        msg.attach(MIMEText(msg_text, 'plain', 'utf-8'))

        # HTML version
        html_body = f"""<html><body dir="rtl" style="font-family: sans-serif;">
        <p>{msg_text.replace(chr(10), '<br>')}</p>
        </body></html>"""
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP_SSL(smtp_host, 465, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"[M5] Email sent to {member.nickname_newsletter}")
        return True

    except Exception as e:
        logger.error(f"[M5] Email failed for {member.id}: {e}")
        return False


def send_survey(family: FamilyConfig, neo: NEO, settings: Settings,
                mock: bool = False) -> list[dict]:
    """Send daily survey at 21:00."""
    results = []

    for member in family.members:
        if mock:
            results.append({'member_id': member.id, 'status': 'mock', 'channel': 'mock'})
            logger.info(f"[M5-MOCK] Mock survey to {member.nickname_newsletter}")
            continue

        # Build survey message
        if member.language_preference == 'en':
            msg = (f"📊 Famely Neuslettr — Daily Check-in\n\n"
                   f"{neo.survey_question}\n\n"
                   f"(Reply freely 🙂)")
        else:
            msg = (f"📊 Famely Neuslettr — סקר יומי\n\n"
                   f"{neo.survey_question}\n\n"
                   f"(שלחו תשובה בחופשיות 🙂)")

        # Try WhatsApp, fallback email
        success = False
        channel = 'none'

        if member.phone and settings.distribution.get('primary_channel') == 'whatsapp':
            success = _send_whatsapp_raw(member.phone, msg, settings)
            channel = 'whatsapp' if success else 'none'

        if not success and member.email:
            success = _send_email_raw(member.email, "📊 Famely Neuslettr Survey", msg)
            channel = 'email' if success else 'none'

        results.append({
            'member_id': member.id,
            'status': 'sent' if success else 'failed',
            'channel': channel,
        })

    return results


def _build_message(member: MemberProfile, neo: NEO, public_url: str) -> str:
    """Build personalized message for member."""
    # Find member's articles
    headlines = []
    for section in neo.member_sections:
        if section['member_id'] == member.id:
            for item in section['items'][:3]:
                headlines.append(f"• {item['title']}")
            break

    headlines_text = '\n'.join(headlines) if headlines else "• Check today's edition!"

    if member.language_preference == 'en':
        return (f"Hey {member.nickname_newsletter}! 🌅\n"
                f"{neo.greeting}\n\n"
                f"📰 Today for you:\n"
                f"{headlines_text}\n\n"
                f"👉 Read: {public_url}")
    else:
        return (f"שלום {member.nickname_newsletter}! 🌅\n"
                f"{neo.greeting}\n\n"
                f"📰 הנה מה שחיכה לך היום:\n"
                f"{headlines_text}\n\n"
                f"👉 לקריאה: {public_url}")


def _send_whatsapp_raw(phone: str, message: str, settings: Settings) -> bool:
    """Low-level WhatsApp send."""
    try:
        sid = os.environ.get('TWILIO_SID')
        token = os.environ.get('TWILIO_TOKEN')
        from_number = os.environ.get('TWILIO_FROM')
        if not all([sid, token, from_number]):
            return False

        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={'From': from_number, 'To': f"whatsapp:{phone}", 'Body': message},
            timeout=30,
        )
        return resp.status_code == 201
    except Exception:
        return False


def _send_email_raw(email: str, subject: str, body: str) -> bool:
    """Low-level email send."""
    try:
        smtp_host = os.environ.get('SMTP_HOST', '')
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')
        smtp_from = os.environ.get('SMTP_FROM', 'famely@nimrod.bio')

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = f"Famely Neuslettr <{smtp_from}>"
        msg['To'] = email

        with smtplib.SMTP_SSL(smtp_host, 465, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception:
        return False
