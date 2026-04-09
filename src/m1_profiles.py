"""
Famely Neuslettr — M1 Profiles
Config loader per LOD400 §3. Read-only, no AI, no DB.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .models import (
    Interest, MemberProfile, SourceConfig, ScanRule,
    FamilyConfig, Settings, ConfigError, MemberNotFound
)

logger = logging.getLogger('famely.m1')


def load_profiles(config_dir: str = "config/") -> FamilyConfig:
    """Load and validate family.json. Raises ConfigError if invalid."""
    path = Path(config_dir) / "family.json"
    if not path.exists():
        raise ConfigError("family.json not found or invalid JSON")

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ConfigError("family.json not found or invalid JSON")

    members_raw = data.get('members', [])
    if not members_raw:
        raise ConfigError("No members defined in family.json")

    members = []
    for m in members_raw:
        for req_field in ('id', 'name', 'language_preference'):
            if req_field not in m:
                raise ConfigError(f"Member {m.get('id', '?')} missing required field: {req_field}")

        interests = [
            Interest(
                topic=i.get('topic', ''),
                topic_en=i.get('topic_en', ''),
                subtopics=i.get('subtopics', []),
                priority=i.get('priority', 'low')
            )
            for i in m.get('interests', [])
        ]

        prefs = m.get('content_preferences', {})
        members.append(MemberProfile(
            id=m['id'],
            name=m['name'],
            name_en=m.get('name_en', m['name']),
            nickname=m.get('nickname', m['name']),
            nickname_newsletter=m.get('nickname_newsletter', m.get('nickname', m['name'])),
            role=m.get('role', 'child'),
            phone=m.get('phone'),
            email=m.get('email'),
            language_preference=m['language_preference'],
            interests=interests,
            max_items_per_day=prefs.get('max_items_per_day', 3),
            preferred_format=prefs.get('preferred_format', 'summary'),
        ))

    family = FamilyConfig(
        family_name=data.get('family_name', ''),
        family_name_en=data.get('family_name_en', ''),
        shared_interests=data.get('shared_interests', {}),
        members=members,
    )
    logger.info(f"Loaded {len(members)} family members from {path}")
    return family


def load_sources(config_dir: str = "config/") -> list[SourceConfig]:
    """Load and validate sources.json. Returns only active sources."""
    path = Path(config_dir) / "sources.json"
    if not path.exists():
        raise ConfigError("sources.json not found or invalid JSON")

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ConfigError("sources.json not found or invalid JSON")

    sources = []
    for s in data:
        for req_field in ('id', 'name', 'type', 'url'):
            if req_field not in s:
                raise ConfigError(f"Source {s.get('id', '?')} missing required field: {req_field}")

        source = SourceConfig(
            id=s['id'],
            name=s['name'],
            type=s['type'],
            url=s['url'],
            trust_score=s.get('trust_score', 0.7),
            status=s.get('status', 'active'),
            linked_members=s.get('linked_members', []),
            schedule=s.get('schedule', 'daily'),
            fail_count=s.get('fail_count', 0),
        )
        if source.status == 'active':
            sources.append(source)

    logger.info(f"Loaded {len(sources)} active sources from {path}")
    return sources


def load_settings(config_dir: str = "config/") -> Settings:
    """Load and validate settings.json."""
    path = Path(config_dir) / "settings.json"
    if not path.exists():
        raise ConfigError("settings.json not found or invalid JSON")

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ConfigError("settings.json not found or invalid JSON")

    required_sections = ['schedule', 'content', 'newsletter', 'ftp', 'distribution', 'ai', 'budget']
    for section in required_sections:
        if section not in data:
            raise ConfigError(f"Settings missing section: {section}")

    settings = Settings(
        schedule=data['schedule'],
        content=data['content'],
        newsletter=data['newsletter'],
        ftp=data['ftp'],
        distribution=data['distribution'],
        ai=data['ai'],
        budget=data['budget'],
    )
    logger.info(f"Loaded settings from {path}")
    return settings


def get_member_by_id(family: FamilyConfig, member_id: str) -> MemberProfile:
    """Return member profile or raise MemberNotFound."""
    for m in family.members:
        if m.id == member_id:
            return m
    raise MemberNotFound(f"Member not found: {member_id}")


def get_scan_rules(family: FamilyConfig, sources: list[SourceConfig]) -> list[ScanRule]:
    """Combine sources with member interests to produce scan rules."""
    member_map = {m.id: m for m in family.members}
    rules = []

    for source in sources:
        keywords = []
        language = "he"  # default

        for mid in source.linked_members:
            member = member_map.get(mid)
            if not member:
                continue
            for interest in member.interests:
                keywords.extend(interest.subtopics)
            if member.language_preference == "en":
                language = "en"

        rules.append(ScanRule(
            source=source,
            keywords=list(set(keywords)),  # deduplicate
            language=language,
        ))

    logger.info(f"Generated {len(rules)} scan rules")
    return rules
