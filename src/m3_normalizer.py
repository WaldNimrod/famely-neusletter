"""
Famely Neuslettr — M3 Normalizer
7-step pipeline: dedup → score → load_submissions → curate → generate → build_neo → archive
Per LOD400 §5.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

from .models import (
    NCI, ScoredNCI, NEO, FamilyConfig, Settings,
    FamilySubmission, GeneratedContent
)
from .db import Database
from .token_tracker import TokenTracker

logger = logging.getLogger('famely.m3')


def build_edition(ncis: list[NCI], family: FamilyConfig, settings: Settings,
                   db: Database, token_tracker: TokenTracker,
                   today: Optional[str] = None) -> NEO:
    """Main pipeline function per LOD400 §5."""
    start_time = time.time()
    today = today or datetime.now(timezone.utc).strftime('%Y-%m-%d')

    logger.info(f"[M3] Building edition for {today} with {len(ncis)} NCIs")
    db.create_newsletter(today, 'building')

    try:
        # Step 1: Dedup
        deduped = dedup(ncis, db, settings.content.get('duplicate_threshold_days', 30))
        logger.info(f"[M3] After dedup: {len(deduped)} items (removed {len(ncis) - len(deduped)})")

        # Step 2: Score
        scored = score(deduped, family)

        # Step 3: Load submissions
        cutoff = (datetime.now(timezone.utc) -
                  timedelta(minutes=settings.schedule.get('submission_cutoff_minutes_before_build', 30)))
        submissions = load_pending_submissions(db, cutoff.isoformat())
        logger.info(f"[M3] Loaded {len(submissions)} pending submissions")

        # Step 4: Curate
        curated = curate(scored, family, settings)

        # Step 5: Generate content (all AI calls)
        generated = generate_content(curated, submissions, family, settings,
                                      token_tracker, today)

        # Step 6: Build NEO
        elapsed_ms = int((time.time() - start_time) * 1000)
        neo = _build_neo(curated, generated, submissions, family, settings,
                         today, len(ncis), len(deduped), elapsed_ms)

        # Step 7: Archive
        archive(neo, ncis, db, today)

        db.update_newsletter(today, status='ready',
                            greeting=neo.greeting,
                            puzzle=neo.trivia.get('puzzle', ''),
                            puzzle_answer=neo.trivia.get('answer', ''),
                            survey_question=neo.survey_question,
                            items_fetched=len(ncis),
                            items_selected=neo.metadata.get('items_selected', 0),
                            sources_scanned=neo.metadata.get('sources_scanned', 0),
                            submissions_count=len(submissions),
                            build_duration_ms=elapsed_ms,
                            neo_json=neo.to_json())

        logger.info(f"[M3] Edition ready: {neo.metadata.get('items_selected', 0)} items, {elapsed_ms}ms")
        return neo

    except Exception as e:
        logger.critical(f"[M3] Build failed: {e}")
        db.update_newsletter(today, status='build_failed')
        raise


# ─── Step 1: Dedup ────────────────────────────────────────────

def dedup(ncis: list[NCI], db: Database, threshold_days: int = 30) -> list[NCI]:
    """Remove items whose content_hash exists in archive from last N days."""
    existing_hashes = db.get_recent_hashes(threshold_days)
    return [nci for nci in ncis if nci.content_hash not in existing_hashes]


# ─── Step 2: Score ────────────────────────────────────────────

def score(ncis: list[NCI], family: FamilyConfig) -> dict[str, list[ScoredNCI]]:
    """Score each NCI for each member. Returns {member_id: [ScoredNCI]}."""
    result = {m.id: [] for m in family.members}

    priority_weights = {"high": 1.0, "medium": 0.6, "low": 0.3}

    for member in family.members:
        for nci in ncis:
            # Language filter: Shaked gets only English
            if member.language_preference == "en" and nci.language != "en":
                continue

            best_score = 0
            best_topic = ""
            best_priority = "low"

            for interest in member.interests:
                # Count keyword matches — use threshold of 2 matches for full score
                # This prevents penalizing members with many subtopics
                text = (nci.title + ' ' + nci.raw_text + ' ' + ' '.join(nci.tags)).lower()
                matches = sum(1 for kw in interest.subtopics if kw.lower() in text)
                keyword_match = min(matches / 2.0, 1.0)  # 2+ matches = full score

                if keyword_match == 0:
                    continue

                priority_weight = priority_weights.get(interest.priority, 0.3)
                source_trust = nci.source_trust
                freshness = _calculate_freshness(nci.published_at)

                # Hebrew bonus for non-English members
                lang_bonus = 0.1 if nci.language == "he" and member.language_preference != "en" else 0

                item_score = (keyword_match * priority_weight * source_trust * freshness * 100) + lang_bonus * 10

                if item_score > best_score:
                    best_score = item_score
                    best_topic = interest.topic
                    best_priority = interest.priority

            if best_score > 0:
                result[member.id].append(ScoredNCI(
                    nci=nci,
                    member_id=member.id,
                    score=round(best_score, 2),
                    matched_topic=best_topic,
                    matched_priority=best_priority,
                ))

        # Sort by score DESC
        result[member.id].sort(key=lambda s: s.score, reverse=True)

    return result


def _calculate_freshness(published_at: str) -> float:
    """Calculate freshness factor based on publication age."""
    try:
        pub = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        age = datetime.now(timezone.utc) - pub
        hours = age.total_seconds() / 3600
        if hours < 24:
            return 1.0
        elif hours < 48:
            return 0.7
        elif hours < 168:  # 7 days
            return 0.5
        else:
            return 0.1
    except (ValueError, TypeError):
        return 0.5  # unknown age


# ─── Step 3: Load Submissions ────────────────────────────────

def load_pending_submissions(db: Database, cutoff_time: str) -> list[FamilySubmission]:
    """Load pending family submissions from DB."""
    rows = db.get_pending_submissions(cutoff_time)
    return [
        FamilySubmission(
            id=r['id'], member_id=r['member_id'], timestamp=r['timestamp'],
            message_type=r['message_type'], content_text=r.get('content_text'),
            media_local_path=r.get('media_local_path'),
            media_mime_type=r.get('media_mime_type'),
            media_size_bytes=r.get('media_size_bytes'),
            link_url=r.get('link_url'), status=r['status'],
            edited_headline=r.get('edited_headline'),
            edited_summary=r.get('edited_summary'),
            edition_date=r.get('edition_date'),
            retry_count=r.get('retry_count', 0),
        )
        for r in rows
    ]


# ─── Step 4: Curate ──────────────────────────────────────────

def curate(scored: dict[str, list[ScoredNCI]], family: FamilyConfig,
           settings: Settings) -> dict[str, list[ScoredNCI]]:
    """Select top items per member with topic balance and discovery."""
    max_total = settings.content.get('max_items_total', 15)
    max_topic_ratio = settings.content.get('max_topic_ratio_per_member', 0.6)
    discovery_ratio = settings.content.get('discovery_ratio', 0.2)
    min_score = settings.content.get('min_relevance_score', 30)

    member_map = {m.id: m for m in family.members}
    curated = {}
    all_selected_ids = set()

    # First pass: select per member
    for member_id, items in scored.items():
        member = member_map.get(member_id)
        if not member:
            continue

        max_items = member.max_items_per_day
        selected = []
        topic_counts = {}

        for item in items:
            if item.score < min_score:
                continue
            if item.nci.id in all_selected_ids:
                continue

            # Topic balance check
            topic = item.matched_topic
            current_count = topic_counts.get(topic, 0)
            if max_items > 0 and current_count / max(len(selected), 1) >= max_topic_ratio and len(selected) > 1:
                continue

            selected.append(item)
            topic_counts[topic] = current_count + 1
            all_selected_ids.add(item.nci.id)

            if len(selected) >= max_items:
                break

        curated[member_id] = selected

    # Second pass: discovery items (cross-member recommendations)
    for member_id, items in curated.items():
        member = member_map.get(member_id)
        if not member:
            continue

        discovery_slots = max(1, int(member.max_items_per_day * discovery_ratio))

        # Find items from other members that this member scored low on
        for other_id, other_items in scored.items():
            if other_id == member_id or discovery_slots <= 0:
                continue
            for item in other_items[:3]:  # top items from other member
                if item.nci.id not in all_selected_ids and item.nci.id not in {i.nci.id for i in items}:
                    # Create a discovery item
                    discovery = ScoredNCI(
                        nci=item.nci,
                        member_id=member_id,
                        score=item.score * 0.5,  # lower score for discovery
                        matched_topic=f"discovery:{other_id}",
                        matched_priority="discovery",
                    )
                    curated[member_id].append(discovery)
                    all_selected_ids.add(item.nci.id)
                    discovery_slots -= 1
                    break

    total_selected = sum(len(v) for v in curated.values())
    logger.info(f"[M3] Curated {total_selected} items across {len(curated)} members")
    return curated


# ─── Step 5: Generate Content ────────────────────────────────

def generate_content(curated: dict[str, list[ScoredNCI]],
                      submissions: list[FamilySubmission],
                      family: FamilyConfig, settings: Settings,
                      tt: TokenTracker, today: str) -> GeneratedContent:
    """All Claude API calls happen here."""
    model = settings.ai.get('summary_model', 'claude-sonnet-4-6')

    # 1. Greeting
    greeting = _generate_greeting(tt, today, family.family_name, model, settings)
    greeting_en = _generate_greeting_en(tt, today, model, settings)

    # 2. Puzzle for צליל
    prev_answer = _get_previous_puzzle_answer(family)
    puzzle, puzzle_answer = _generate_puzzle(tt, today, prev_answer, model, settings)

    # 3. Headlines + Summaries
    headlines, summaries = _generate_summaries(tt, curated, family, today, model, settings)

    # 4. Submission editing
    submission_edits = _edit_submissions(tt, submissions, family, today, model, settings)

    # 5. Discovery bridges
    bridges = _generate_bridges(tt, curated, family, today, model, settings)

    # 6. Survey question
    topic_list = _collect_topics(curated)
    survey_q = _generate_survey(tt, topic_list, today, model, settings)
    survey_q_en = _generate_survey_en(tt, topic_list, today, model, settings)

    # 7. Today in history
    history = _generate_history(tt, today, model, settings)

    return GeneratedContent(
        greeting=greeting,
        greeting_en=greeting_en,
        puzzle=puzzle,
        puzzle_answer=puzzle_answer,
        survey_question=survey_q,
        survey_question_en=survey_q_en,
        headlines=headlines,
        summaries=summaries,
        submission_edits=submission_edits,
        bridges=bridges,
        history=history,
    )


def _generate_greeting(tt, today, family_name, model, settings):
    try:
        return tt.generate("m3", "greeting",
            f"Generate a warm Hebrew family greeting for {today}.\n"
            f"Family name: {family_name}\n"
            f"Include a fun fact about today. 1-2 sentences. Casual, warm.",
            max_tokens=settings.ai.get('greeting_max_tokens', 100),
            model=model, newsletter_date=today)
    except Exception:
        return f"בוקר טוב, {family_name}! ☀️"


def _generate_greeting_en(tt, today, model, settings):
    try:
        return tt.generate("m3", "greeting_en",
            f"Generate a warm English family greeting for {today}.\n"
            f"Include a fun fact about today. 1-2 sentences. Casual.",
            max_tokens=settings.ai.get('greeting_max_tokens', 100),
            model=model, newsletter_date=today)
    except Exception:
        return "Good morning! Here's your daily digest."


def _generate_puzzle(tt, today, prev_answer, model, settings):
    try:
        puzzle = tt.generate("m3", "puzzle",
            f"Create a hard math puzzle for a very smart 13-year-old.\n"
            f"Competition level. Include yesterday's puzzle answer: {prev_answer}.\n"
            f"Hebrew. Format: puzzle text + (תשובה מחר!)",
            max_tokens=settings.ai.get('puzzle_max_tokens', 150),
            model=model, newsletter_date=today)
        answer = tt.generate("m3", "puzzle_answer",
            f"What is the answer to this puzzle? Just the answer, no explanation.\n{puzzle}",
            max_tokens=50, model=model, newsletter_date=today)
        return puzzle, answer
    except Exception:
        return "חידת היום 🧩\nאין חידה היום, אבל מחר תהיה! (תשובה מחר!)", ""


def _generate_summaries(tt, curated, family, today, model, settings):
    """Generate headlines and summaries, batched per 3-4 articles."""
    headlines = {}
    summaries = {}
    member_map = {m.id: m for m in family.members}

    for member_id, items in curated.items():
        member = member_map.get(member_id)
        if not member:
            continue

        lang = "English" if member.language_preference == "en" else "Hebrew"

        # Batch articles in groups of 3
        for batch_start in range(0, len(items), 3):
            batch = items[batch_start:batch_start + 3]
            articles_text = "\n\n".join(
                f"[{i+1}] Title: {item.nci.title}\nText: {item.nci.raw_text[:500]}"
                for i, item in enumerate(batch)
            )

            try:
                response = tt.generate("m3", "summary",
                    f"For each article below, generate:\n"
                    f"1. A catchy headline (max 15 words)\n"
                    f"2. A 2-sentence summary\n"
                    f"Language: {lang}\n\n"
                    f"Format your response as JSON array:\n"
                    f'[{{"headline": "...", "summary": "..."}}]\n\n'
                    f"Articles:\n{articles_text}",
                    max_tokens=settings.ai.get('summary_max_tokens', 200) * len(batch),
                    model=model, newsletter_date=today)

                # Parse response
                try:
                    parsed = json.loads(response)
                    for i, item in enumerate(batch):
                        if i < len(parsed):
                            headlines[item.nci.id] = parsed[i].get('headline', item.nci.title)
                            summaries[item.nci.id] = parsed[i].get('summary', item.nci.raw_text[:200])
                        else:
                            headlines[item.nci.id] = item.nci.title
                            summaries[item.nci.id] = item.nci.raw_text[:200]
                except (json.JSONDecodeError, IndexError):
                    # Title-only fallback
                    for item in batch:
                        headlines[item.nci.id] = item.nci.title
                        summaries[item.nci.id] = item.nci.raw_text[:200]

            except Exception:
                # Title-only fallback
                for item in batch:
                    headlines[item.nci.id] = item.nci.title
                    summaries[item.nci.id] = item.nci.raw_text[:200]

    return headlines, summaries


def _edit_submissions(tt, submissions, family, today, model, settings):
    """Edit family submissions with AI newspaper editor."""
    edits = {}
    member_map = {m.id: m for m in family.members}

    for sub in submissions:
        member = member_map.get(sub.member_id)
        name = member.nickname_newsletter if member else sub.member_id

        try:
            response = tt.generate("m3", "submission_edit",
                f"You are a professional newspaper editor for a family newsletter.\n"
                f"A family member ({name}) sent this content:\n"
                f"Type: {sub.message_type}\n"
                f"Text: {sub.content_text or '(no text)'}\n"
                f"{'Link: ' + sub.link_url if sub.link_url else ''}\n\n"
                f"Create:\n"
                f"1. An engaging headline (max 10 words, Hebrew)\n"
                f"2. A brief edited summary (2-3 sentences, keep original intent)\n\n"
                f"Be warm, family-friendly. This WILL be published.\n"
                f'Respond as JSON: {{"headline": "...", "summary": "..."}}',
                max_tokens=settings.ai.get('submission_edit_max_tokens', 300),
                model=model, newsletter_date=today)

            try:
                parsed = json.loads(response)
                edits[sub.id] = {
                    'headline': parsed.get('headline', sub.content_text[:50] if sub.content_text else 'ידיעה מהמשפחה'),
                    'summary': parsed.get('summary', sub.content_text or ''),
                }
            except json.JSONDecodeError:
                edits[sub.id] = {
                    'headline': sub.content_text[:50] if sub.content_text else 'ידיעה מהמשפחה',
                    'summary': sub.content_text or '',
                }
        except Exception:
            # Publish with raw text if AI fails
            if sub.retry_count >= 2:
                edits[sub.id] = {
                    'headline': sub.content_text[:50] if sub.content_text else 'ידיעה מהמשפחה',
                    'summary': sub.content_text or '',
                }
            # else leave out — will retry next build

    return edits


def _generate_bridges(tt, curated, family, today, model, settings):
    """Generate bridge text for discovery items."""
    bridges = []
    member_map = {m.id: m for m in family.members}

    for member_id, items in curated.items():
        member = member_map.get(member_id)
        if not member:
            continue

        for item in items:
            if item.matched_priority == "discovery" and ':' in item.matched_topic:
                from_id = item.matched_topic.split(':')[1]
                from_member = member_map.get(from_id)
                if not from_member:
                    continue

                try:
                    text = tt.generate("m3", "bridge",
                        f"Write a short bridge text (1 sentence, Hebrew) explaining why\n"
                        f"{from_member.nickname_newsletter} would recommend this article to "
                        f"{member.nickname_newsletter}.\n"
                        f"Article: {item.nci.title}\n"
                        f"Casual, fun, family tone.",
                        max_tokens=settings.ai.get('bridge_max_tokens', 100),
                        model=model, newsletter_date=today)
                except Exception:
                    text = f"המלצה מ{from_member.nickname_newsletter}!"

                bridges.append({
                    'from_member': from_id,
                    'to_member': member_id,
                    'nci_id': item.nci.id,
                    'text': text,
                })

    return bridges


def _generate_survey(tt, topics, today, model, settings):
    try:
        return tt.generate("m3", "survey",
            f"Generate a varied daily survey question for a family newsletter.\n"
            f"Today's main topics were: {', '.join(topics)}\n"
            f"Hebrew. Short. Engaging. Should feel like a fun family conversation.",
            max_tokens=settings.ai.get('survey_max_tokens', 100),
            model=model, newsletter_date=today)
    except Exception:
        return "מה דעתכם על הניוזלטר של היום?"


def _generate_survey_en(tt, topics, today, model, settings):
    try:
        return tt.generate("m3", "survey_en",
            f"Generate a varied daily survey question for a family newsletter.\n"
            f"Today's main topics were: {', '.join(topics)}\n"
            f"English. Short. Engaging. Fun family tone.",
            max_tokens=settings.ai.get('survey_max_tokens', 100),
            model=model, newsletter_date=today)
    except Exception:
        return "What did you think of today's newsletter?"


def _generate_history(tt, today, model, settings):
    """Generate a 'Today in History' fact in Hebrew."""
    try:
        return tt.generate("m3", "history",
            f"Write a fascinating 'Today in History' fact for {today}.\n"
            f"Hebrew. 2-3 sentences. Include the year and what happened.\n"
            f"Pick something interesting for a family with kids aged 13-18.\n"
            f"Topics: science, exploration, art, inventions, nature discoveries.\n"
            f"Avoid wars and politics unless very significant.",
            max_tokens=settings.ai.get('greeting_max_tokens', 100),
            model=model, newsletter_date=today)
    except Exception:
        return f"ב-{today} קרו הרבה דברים מעניינים לאורך ההיסטוריה!"


def _format_hebrew_date(today: str) -> str:
    """Convert YYYY-MM-DD to Hebrew formatted date string."""
    HEB_DAYS = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
    HEB_MONTHS = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                  'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
    try:
        dt = datetime.strptime(today, '%Y-%m-%d')
        day_name = HEB_DAYS[dt.weekday()]
        month_name = HEB_MONTHS[dt.month]
        return f"יום {day_name}, {dt.day} ב{month_name} {dt.year}"
    except (ValueError, IndexError):
        return today


def _collect_topics(curated):
    topics = set()
    for items in curated.values():
        for item in items:
            if item.matched_priority != "discovery":
                topics.add(item.matched_topic)
    return list(topics)[:5]


def _get_previous_puzzle_answer(family):
    """Get previous puzzle answer (placeholder for now)."""
    return "42"


# ─── Step 6: Build NEO ───────────────────────────────────────

def _build_neo(curated, generated, submissions, family, settings,
               today, items_fetched, items_after_dedup, elapsed_ms) -> NEO:
    """Build the complete NEO object."""
    member_map = {m.id: m for m in family.members}
    member_order = ["nimrod", "michal", "shaked", "maayan", "tzlil"]

    # Build member sections
    member_sections = []
    discovery_items = []
    items_selected = 0

    for mid in member_order:
        member = member_map.get(mid)
        if not member:
            continue

        items = curated.get(mid, [])
        section_items = []
        for item in items:
            if item.matched_priority == "discovery":
                # Find bridge text
                bridge = ""
                for b in generated.bridges:
                    if b['nci_id'] == item.nci.id and b['to_member'] == mid:
                        bridge = b['text']
                        break
                discovery_items.append({
                    'nci_id': item.nci.id,
                    'title': generated.headlines.get(item.nci.id, item.nci.title),
                    'summary': generated.summaries.get(item.nci.id, item.nci.raw_text[:200]),
                    'url': item.nci.url,
                    'source_name': item.nci.source_name,
                    'from_member': item.matched_topic.split(':')[1] if ':' in item.matched_topic else '',
                    'to_member': mid,
                    'bridge_text': bridge,
                    'language': item.nci.language,
                })
            else:
                section_items.append({
                    'nci_id': item.nci.id,
                    'title': generated.headlines.get(item.nci.id, item.nci.title),
                    'summary': generated.summaries.get(item.nci.id, item.nci.raw_text[:200]),
                    'url': item.nci.url,
                    'source_name': item.nci.source_name,
                    'category': item.matched_topic,
                    'score': item.score,
                    'language': item.nci.language,
                    'published_at': item.nci.published_at,
                    'image_url': item.nci.image_url,
                })

        items_selected += len(section_items)
        member_sections.append({
            'member_id': mid,
            'member_name': member.nickname_newsletter,
            'member_name_en': member.name_en,
            'language': member.language_preference,
            'items': section_items,
        })

    # Add discovery items to count
    items_selected += len(discovery_items)
    logger.info(f"[M3] Items selected: {items_selected} total ({len(member_sections)} members, {len(discovery_items)} discovery)")

    # Build family content (submissions)
    family_content = []
    for sub in submissions:
        edit = generated.submission_edits.get(sub.id, {})
        member = member_map.get(sub.member_id)
        family_content.append({
            'submission_id': sub.id,
            'member_id': sub.member_id,
            'member_name': member.nickname_newsletter if member else sub.member_id,
            'headline': edit.get('headline', sub.content_text[:50] if sub.content_text else 'ידיעה מהמשפחה'),
            'summary': edit.get('summary', sub.content_text or ''),
            'message_type': sub.message_type,
            'link_url': sub.link_url,
            'media_local_path': sub.media_local_path,
        })

    # Count unique sources
    sources_scanned = len(set(
        item.nci.source_name
        for items in curated.values()
        for item in items
    ))

    return NEO(
        date=today,
        family_name=family.family_name,
        greeting=generated.greeting,
        family_content=family_content,
        member_sections=member_sections,
        discovery=discovery_items,
        trivia={
            'puzzle': generated.puzzle,
            'answer': generated.puzzle_answer,
            'history': generated.history,
        },
        survey_question=generated.survey_question,
        date_formatted=_format_hebrew_date(today),
        metadata={
            'items_fetched': items_fetched,
            'items_after_dedup': items_after_dedup,
            'items_selected': items_selected,
            'sources_scanned': sources_scanned,
            'submissions_count': len(submissions),
            'discovery_count': len(discovery_items),
            'build_duration_ms': elapsed_ms,
        }
    )


# ─── Step 7: Archive ─────────────────────────────────────────

def archive(neo: NEO, ncis: list[NCI], db: Database, today: str):
    """Archive NCIs and NEO to DB + JSON files."""
    # 1. Archive all fetched NCIs
    for nci in ncis:
        db.archive_nci(nci)

    # 2. Save NEO as JSON
    editions_dir = Path("data/archive/editions")
    editions_dir.mkdir(parents=True, exist_ok=True)
    neo_path = editions_dir / f"{today}.json"
    neo_path.write_text(neo.to_json(), encoding='utf-8')

    # 3. Save raw NCIs as JSON
    raw_dir = Path("data/archive/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{today}.json"
    from dataclasses import asdict
    raw_data = [asdict(nci) for nci in ncis]
    raw_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding='utf-8')

    # 4. Update submission statuses
    for fc in neo.family_content:
        db.update_submission(fc['submission_id'], status='published', edition_date=today)

    logger.info(f"[M3] Archived {len(ncis)} NCIs and NEO for {today}")
