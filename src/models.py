"""
Famely Neuslettr — Data Models
All dataclasses per LOD400 §3-§8.
"""

from dataclasses import dataclass, field
from typing import Optional
import hashlib
import json
from datetime import datetime, timezone


# ─── M1: Config Models ───────────────────────────────────────────

@dataclass
class Interest:
    topic: str
    topic_en: str
    subtopics: list[str]
    priority: str  # "high" | "medium" | "low"


@dataclass
class MemberProfile:
    id: str
    name: str
    name_en: str
    nickname: str
    nickname_newsletter: str
    role: str  # "parent" | "child"
    phone: Optional[str]
    email: Optional[str]
    language_preference: str  # "he" | "en" | "both"
    interests: list[Interest]
    max_items_per_day: int
    preferred_format: str  # "summary" | "headline"


@dataclass
class SourceConfig:
    id: str
    name: str
    type: str  # "rss" | "web" | "youtube" | "api"
    url: str
    trust_score: float  # 0.0–1.0
    status: str  # "active" | "degraded" | "disabled"
    linked_members: list[str]
    schedule: str  # "daily" | "weekly"
    fail_count: int = 0


@dataclass
class ScanRule:
    source: SourceConfig
    keywords: list[str]
    language: str


@dataclass
class FamilyConfig:
    family_name: str
    family_name_en: str
    shared_interests: dict
    members: list[MemberProfile]


@dataclass
class Settings:
    schedule: dict
    content: dict
    newsletter: dict
    ftp: dict
    distribution: dict
    ai: dict
    budget: dict


# ─── M2: Content Models ──────────────────────────────────────────

@dataclass
class NCI:
    """Normalized Content Item"""
    id: str               # SHA256(url)[:16]
    url: str
    title: str
    source_name: str
    source_type: str      # "rss" | "web" | "youtube" | "family_submission"
    source_url: str
    source_trust: float
    published_at: str     # ISO8601
    fetched_at: str       # ISO8601
    language: str         # "he" | "en"
    raw_text: str         # summary/excerpt, max 5000 chars
    tags: list[str]
    image_url: Optional[str]
    content_hash: str     # SHA256(title + raw_text)[:16]
    is_submission: bool = False
    submitted_by: Optional[str] = None


def create_nci(title: str, url: str, source_name: str, source_type: str,
               source_url: str, source_trust: float, published_at: str,
               raw_text: str, tags: list[str], language: str,
               image_url: Optional[str] = None) -> NCI:
    """Factory function. Generates id (SHA256 of URL) and content_hash."""
    nci_id = hashlib.sha256(url.encode()).hexdigest()[:16]
    content_hash = hashlib.sha256((title + raw_text).encode()).hexdigest()[:16]
    fetched_at = datetime.now(timezone.utc).isoformat()
    return NCI(
        id=nci_id,
        url=url,
        title=title,
        source_name=source_name,
        source_type=source_type,
        source_url=source_url,
        source_trust=source_trust,
        published_at=published_at,
        fetched_at=fetched_at,
        language=language,
        raw_text=raw_text[:5000],
        tags=tags,
        image_url=image_url,
        content_hash=content_hash,
    )


# ─── M3: Scoring + Edition Models ────────────────────────────────

@dataclass
class ScoredNCI:
    nci: NCI
    member_id: str
    score: float        # 0-100
    matched_topic: str
    matched_priority: str


@dataclass
class GeneratedContent:
    greeting: str
    greeting_en: str
    puzzle: str
    puzzle_answer: str
    survey_question: str
    survey_question_en: str
    headlines: dict  # {nci_id: headline}
    summaries: dict  # {nci_id: summary}
    submission_edits: dict  # {submission_id: {headline, summary}}
    bridges: list[dict]  # [{from_member, to_member, nci_id, text}]


@dataclass
class NEO:
    """Normalized Edition Object"""
    date: str
    family_name: str
    greeting: str
    family_content: list[dict]    # edited submissions
    member_sections: list[dict]   # per-member curated articles
    discovery: list[dict]         # cross-member items with bridge text
    trivia: dict                  # {puzzle, answer, history}
    survey_question: str
    metadata: dict

    def to_json(self) -> str:
        """Serialize to JSON string."""
        from dataclasses import asdict
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# ─── M6: Feedback Models ─────────────────────────────────────────

@dataclass
class FamilySubmission:
    id: str
    member_id: str
    timestamp: str
    message_type: str  # "text" | "image" | "video" | "document" | "link"
    content_text: Optional[str]
    media_local_path: Optional[str]
    media_mime_type: Optional[str]
    media_size_bytes: Optional[int]
    link_url: Optional[str]
    status: str  # "received" | "editing" | "published" | "rejected" | "edit_failed"
    edited_headline: Optional[str] = None
    edited_summary: Optional[str] = None
    edition_date: Optional[str] = None
    retry_count: int = 0


@dataclass
class FeedbackEvent:
    member_id: str
    timestamp: str
    type: str  # "survey" | "text"
    newsletter_date: Optional[str]
    value: str
    article_id: Optional[str] = None
    source_detail: Optional[str] = None


# ─── Exceptions ───────────────────────────────────────────────────

class ConfigError(Exception):
    """Raised when config files are missing or invalid."""
    pass


class FTPUploadError(Exception):
    """Raised when FTP upload fails after all retries."""
    pass


class MemberNotFound(Exception):
    """Raised when member_id not found in family config."""
    pass
