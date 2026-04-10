"""
Resolve environment variables with Upress deployment names and legacy Famely aliases.
UPRESS_SFTP_* keys control plain FTP (port 21) — naming is historical from hosting panels.
"""

from __future__ import annotations

import os
from typing import Any


def env_first(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.environ.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def env_int_first(*keys: str, default: int) -> int:
    for k in keys:
        v = os.environ.get(k)
        if v is not None and str(v).strip():
            try:
                return int(str(v).strip())
            except ValueError:
                continue
    return default


def ftp_credentials() -> tuple[str, str, str, int]:
    """host, user, password, port (FTP; default 21)."""
    host = env_first("UPRESS_SFTP_HOST", "FTP_HOST")
    user = env_first("UPRESS_SFTP_USER", "FTP_USER")
    passwd = env_first("UPRESS_SFTP_PASS", "FTP_PASS")
    port = env_int_first("UPRESS_SFTP_PORT", "FTP_PORT", default=21)
    return host, user, passwd, port


def ftp_remote_base(settings: Any) -> str:
    """Remote directory prefix for newsletter uploads."""
    base = env_first("UPRESS_UPLOAD_PATH", "FTP_PATH")
    if base:
        return base.rstrip("/")
    return str(settings.ftp.get("remote_path", "/newsletter")).rstrip("/")


def newsletter_url_base(settings: Any) -> str:
    """Public HTTPS base for built HTML (no trailing slash)."""
    base = env_first("UPRESS_PUBLIC_BASE")
    if base:
        return base.rstrip("/")
    return str(settings.newsletter.get("url_base", "https://nimrod.bio/newsletter")).rstrip("/")


def smtp_config(default_from: str = "newsletter@nimrod.bio") -> dict[str, Any]:
    """
    Keys: host, port, user, password, from_addr.
    EMAIL_FROM / SMTP_FROM used as login fallback when user not set.
    """
    from_addr = env_first("EMAIL_FROM", "SMTP_FROM", default=default_from)
    user = env_first("EMAIL_SMTP_USER", "SMTP_USER")
    if not user:
        user = from_addr
    return {
        "host": env_first("EMAIL_SMTP_HOST", "SMTP_HOST"),
        "port": env_int_first("EMAIL_SMTP_PORT", "SMTP_PORT", default=465),
        "user": user,
        "password": env_first("EMAIL_PASSWORD", "SMTP_PASS", "EMAIL_SMTP_PASS"),
        "from_addr": from_addr,
    }


def smtp_deliver_message(msg: Any) -> None:
    """Send an email.message.Message using env-resolved SMTP (SSL or STARTTLS)."""
    import smtplib

    cfg = smtp_config()
    host = cfg["host"]
    password = cfg["password"]
    if not host or not password:
        raise ValueError("SMTP: missing EMAIL_SMTP_HOST/SMTP_HOST or EMAIL_PASSWORD/SMTP_PASS")

    port = int(cfg["port"])
    user = cfg["user"]

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(user, password)
            server.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=30) as server:
        if port in (587, 2525, 25):
            try:
                server.starttls()
            except smtplib.SMTPException:
                if port != 25:
                    raise
        server.login(user, password)
        server.send_message(msg)
