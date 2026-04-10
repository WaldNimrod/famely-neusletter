# Family Newsletter — Canonical Style Guide v1.0.0

**Date:** 2026-04-10  
**Status:** Binding for all agents. Any deviation requires Team 00 approval.

---

## 1. Brand Identity

### Official Name
**English:** Family Newsletter  
**Hebrew:** בית ולד (transliteration: "Beit Vald")  
⚠️ **NOTE:** "Famely Neuslettr" was a typo from early development. This is the canonical name.

### Tagline & Footer
All editions must include the footer text: **"by AgentsOS @ nimrod.bio"**

### Logo Character (Monthly Rotation)
Characters rotate monthly. All characters are fictional/licensed IP and must be rendered as PNG assets.

| Month | Character | Source | Notes |
|-------|-----------|--------|-------|
| April 2026 | Cat in the Hat | Dr. Seuss | Playful, mischievous energy |
| May 2026 | Popeye | King Features | Sailor theme aligns with family adventures |

Character assets stored at: `assets/characters/{YYYY-MM}/{pose}.png`  
Fallback: If asset unavailable, use emoji placeholder matching character theme.

---

## 2. Writing Styles (TWO Distinct Styles)

### Style A — "סימניה/חם" (Simaniia Warm)
**Hebrew:** סימניה קלה וחמה  
**English translation:** "Easy Hebrew, Warm & Conversational"

**Used for:**
- Greeting / Cover opener
- Opener section (what's coming this week)
- Character speech bubbles
- Puzzle intro / quiz questions
- Closer / Sign-off
- Survey preamble

**Rules:**
- Short sentences: maximum 8-10 words each
- Address family members by first name only (e.g., "נימרוד" not "אבא" or "Mr. Nimrod")
- Sounds like conversation at the dinner table—natural, warm, personal
- Direct and honest; no pretension
- No attempting to be clever or witty without genuine basis
- Inspired by Simaniia magazine editorial voice: accessible Hebrew, dialogic, warm
- Avoid jargon; use simple, everyday vocabulary

**Example:**
> נימרוד מצא מסלולי הפלגה חדשים ביוון.  
> הרוח נושבת.  
> בואו נתחיל.

**Translation (for reference only):**  
"Nimrod discovered new sailing routes in Greece. The wind is blowing. Let's begin."

---

### Style B — "כלכליסט/עובדתי" (Calcalist Factual)
**Hebrew:** כלכליסט עובדתי  
**English translation:** "Calcalist Professional & Factual"

**Used for:**
- Article headlines
- Article summaries
- Discovery bridge text (connecting members across themes)
- History section entries
- Data-driven content callouts

**Rules:**
- Factual, precise, data-driven language
- Professional yet readable; avoid academic tone
- No emotional language, hype, or superlatives without data
- Active voice preferred (e.g., "מדענים גילו" not "גוליי על ידי מדענים")
- Every summary must be **at least one full paragraph** (3+ sentences minimum)
- Source name always attributed (e.g., "לפי BBC" or "מתוך הנטע"ה")
- Inspired by Calcalist news style: clear, authoritative, evidence-based

**Example:**
> מדריך מקיף המציג מרינות חדשות ועגינות בלתי מוכרות באיי יוון. כולל ראיונות עם סקיפרים ישראלים ותנאי רוח מפורטים. המקור: כתב אישי של נימרוד מטיול בקיץ 2025.

**Translation (for reference only):**  
"A comprehensive guide presenting new marinas and little-known anchorages in the Greek islands. Includes interviews with Israeli sailors and detailed wind conditions. Source: Nimrod's personal journal from summer 2025 travels."

---

## 3. Content Hierarchy (3 Levels)

The Family Newsletter uses a 3-tier visual and content hierarchy. **Minimum rule:** Every family member must have at least 1 item somewhere across L1+L2 combined (does not apply to L3).

### HERO (L1)
- **Count:** Exactly 1 per edition
- **Layout:** Full-width banner
- **Visual:** Large hero image required; character placeholder overlay positioned in top-right or bottom-left
- **Text visible:** Category tag + headline + full summary paragraph (3+ sentences)
- **Interaction:** Click/tap to expand → shows full_text + source link (if applicable)
- **Styling:** Largest border (4px solid), largest shadow (6px 6px 0), member color background if no image

### FEATURE (L2)
- **Count:** 2 per row, at least 2-4 panels (adjust based on week content)
- **Visual:** MANDATORY — must include either image_url OR fallback (gradient in member color + member emoji)
- **Text visible:** Category tag + title + summary paragraph (2-3 sentences)
- **Interaction:** Click/tap to expand → shows full_text + source link (if applicable)
- **Styling:** 3px solid border, 4px 4px 0 shadow, rounded corners 12-16px
- **Responsive:** 2-col on desktop, 1-col on mobile
- **Member diversity:** Across L1+L2, ensure every family member has ≥1 item

### COMPACT (L3)
- **Count:** Variable (typically 3-8 items per week)
- **Layout:** Single row per item, icon + title + category tag
- **Visual:** Icon or emoji (no images for L3)
- **Text visible:** Title only (1-2 words)
- **Interaction:** Click/tap to expand → shows summary + source link
- **Styling:** Minimal border (2px), no shadow or thin shadow (2px 2px 0), smallest text size

---

## 4. Mandatory Sections (In Order)

Every edition must include these sections in exactly this order:

1. **Cover / Masthead**
   - Headline: "Family Newsletter!" (English) + "בית ולד" (Hebrew)
   - Edition badge (e.g., "April 10, 2026" or "Week 15")
   - Monthly logo character (4-6 inches wide on desktop)

2. **Opener**
   - Style A (Simaniia Warm)
   - 2-3 sentences summarizing what's coming this week per family member
   - Tone: excitement, anticipation, warmth

3. **Family Strip**
   - Horizontal row of 5 member chips (one per family member)
   - Each chip: Member emoji + Hebrew name + item count for week (e.g., "נימרוד 3")
   - Interactive: Click chip to highlight/filter that member's content (optional but recommended)
   - Background: Light halftone, solid border 2px

4. **Weekly Weather Forecast**
   - Summary bar (1-2 lines): "Week of April 10-16: Mixed conditions across Israel"
   - Expandable section per location (if applicable): 7-day forecast with graph
   - Data: Must include `daily` array with min/max temps, precipitation %, wind direction/speed
   - Style: Factual, Calcalist-inspired

5. **HERO Panel (L1)**
   - One full-width item with large image, character overlay, full summary paragraph

6. **FEATURE Panels (L2)**
   - 2-4 panels arranged 2-per-row
   - Each with image or fallback gradient+emoji, headline, summary paragraph

7. **COMPACT Panels (L3)**
   - 3-8 items, single-row layout, minimal styling
   - Quick reads and links

8. **Discovery Bridge**
   - Cross-member connective text (Style B, Calcalist Factual)
   - Highlights shared themes or common interests across family members
   - Example: "This week, both נימרוד and שקד explored maritime topics"

9. **Weekly Puzzle**
   - New puzzle for this week (riddle, word game, or visual puzzle)
   - Puzzle intro written in Style A (warm, playful)
   - Include last week's answer/solution
   - Interactive: Expandable solution (click to reveal)

10. **Today in History**
    - 2-3 historical events or facts related to the current date
    - Style B (Calcalist Factual)
    - Format: "On April 10, [YEAR]: [Fact]"

11. **Family Survey / Poll**
    - One multiple-choice question for the week
    - Question written in Style A (warm, conversational)
    - Include WhatsApp link or response mechanism: "Reply here via WhatsApp"
    - Display previous week's poll results (if available)

12. **Closer / Sign-Off**
    - Style A (Simaniia Warm)
    - 2-3 sentences
    - Tone: warm, encouraging, sets up anticipation for next week
    - Example: "זה היה שבוע מדהים. ראו אתכם בשבוע הבא!"

13. **Footer**
    - Text: "by AgentsOS @ nimrod.bio"
    - Font: Smaller, secondary color, right-aligned (RTL)
    - Date and edition number

---

## 5. Visual Design Standards

### Typography
- **Headers (H1, H2, H3):** Bangers font (comic book style, all sizes)
- **Body Text:** Patrick Hand font (friendly, handwritten-style sans serif)
- **Small Text (metadata, dates):** Patrick Hand, 0.85em, lighter weight

### Colors & Background
- **Page Background:** #fdf6e3 (warm cream) with halftone dot pattern overlay (#e8dcc8, ~8-12px dots, 20-30% opacity)
- **Borders:** Bold 3-4px solid var(--ink) (#2c3e50 or darker)
- **Shadows:** Comic-style offset, e.g., `4px 4px 0px rgba(0,0,0,0.3)` (no blur)
- **Corner Radius:** 12-16px for panels and cards (slightly exaggerated)

### Member Brand Colors
Each family member has a canonical color and emoji:

| Family Member | Hebrew | ID | Emoji | HEX Color | Role |
|---|---|---|---|---|---|
| Nimrod | נימרוד | nimrod | ⛵ | #2471a3 (navy blue) | Parent |
| Michal | מיכל | michal | 🌿 | #27ae60 (forest green) | Parent |
| Shaked | שקד | shaked | ⚗️ | #7d3c98 (purple) | Child |
| Maayan | יויו | maayan | 🎪 | #c0392b (red) | Child |
| Tzlil | צליל | tzlil | 🧮 | #e67e22 (orange) | Child |

**Usage:**
- When content is attributed to a member, use their color for the border or background accent
- If an L2 panel has no image, use gradient: member color (#XXX) → fade to white, with large emoji centered
- Member emoji appear in Family Strip, headers, and decorative elements

### Language & Layout
- **Default direction:** RTL (Right-to-Left) for Hebrew content
- **English content blocks:** Apply class `.ltr` for left-to-right rendering within RTL page
- **Mixed content:** Hebrew text flows RTL, English text within same line flows LTR

### Interactive Elements
- **Expand/Collapse:** All L1, L2, and L3 panels are expandable using `togglePanel()` JavaScript function
- **Button styling:** 3px border, member color or ink color, rounded corners, hover state with shadow increase
- **Transitions:** Smooth expand/collapse (300ms ease)

---

## 6. Schedule & Cadence

### Frequency
**WEEKLY** — NOT daily, NOT monthly

### Build & Send Times (Israel Standard Time)
- **Build:** Every Friday, 09:00 IST
- **Send:** Every Friday, 12:00 IST
- **Cron expression (build):** `0 9 * * 5` (09:00 Friday)
- **Cron expression (send):** `0 12 * * 5` (12:00 Friday)

### Deadline
All content for the week must be submitted by **Thursday 17:00 IST** to allow for build and review.

---

## 7. Technical Standards

### Template Engine
- **Framework:** Jinja2 with `autoescape=True` enabled
- **Encoding:** UTF-8 with BOM for proper Hebrew character rendering
- **Charset:** `<meta charset="UTF-8">`

### Variable Handling
- **Plain text variables:** Rendered as-is (autoescape active)
- **HTML content in variables:** Must use `|safe` filter explicitly
  - ❌ `{{ panel.description }}` (if it contains HTML)
  - ✅ `{{ panel.description|safe }}` (correct)
- **Markdown conversion:** AI-generated text (Claude API output) may include markdown → convert to HTML before template insertion
  - Use library: `markdown2` or `python-markdown`
  - Render to HTML, then insert with `|safe` filter

### Character Assets
- **Storage:** `assets/characters/{YYYY-MM}/{pose}.png`
- **Format:** PNG with transparency
- **Sizes:** Provide at least 2x for high-DPI screens
- **Fallback:** If asset unavailable, render emoji (e.g., 🎩 for Cat in the Hat, ⚓ for Popeye)
- **Licensing:** Ensure all characters are properly licensed or use generic illustrations

### Weather Data Structure
```json
{
  "location": "ירושלים",
  "summary": "Mixed conditions with afternoon showers",
  "daily": [
    {
      "date": "2026-04-10",
      "day": "שישי",
      "high": 24,
      "low": 16,
      "precipitation": 10,
      "wind_speed": 12,
      "wind_direction": "NW"
    }
    // ... 6 more days
  ]
}
```

### Image & Fallback Logic
**For L2 (FEATURE) panels:**
```
if panel.image_url exists:
  render <img src={image_url} />
else:
  render gradient background in member_color, centered member_emoji
```

**For L1 (HERO) panels:**
- Image required; if missing, use solid member color + emoji

**For L3 (COMPACT) panels:**
- No images; use emoji or icon only

---

## 8. Family Members (Canonical Registry)

This table is the source of truth for family member data across all systems:

| ID | Hebrew Name | English Name | Role | Member Emoji | Member Color | Notes |
|---|---|---|---|---|---|---|
| `nimrod` | נימרוד | Nimrod | Parent | ⛵ | #2471a3 | Sailor, explorer |
| `michal` | מיכל | Michal | Parent | 🌿 | #27ae60 | Nature-focused |
| `shaked` | שקד | Shaked | Child | ⚗️ | #7d3c98 | Science, chemistry |
| `maayan` | יויו | Maayan (nickname: Yoyo) | Child | 🎪 | #c0392b | Performance, creativity |
| `tzlil` | צליל | Tzlil | Child | 🧮 | #e67e22 | Math, logic |

**Usage Rules:**
- Always use canonical ID (e.g., `nimrod`, not `dad` or `nimrod_ben_tzvi_vald`)
- Display name in UI: Hebrew name (with English fallback for international contexts)
- Full family name "משפחת בן-צבי ולד" is NEVER used in display—use only "בית ולד"

---

## 9. Communication Protocol

### Inter-Team Artifacts
- **Location:** `_COMMUNICATION/{team_id}/`
- **File format:** Markdown with version number (e.g., `v1.0.0`)
- **Routing:** If artifact is for Team 00 (Nimrod), include path in message for routing

### Server Team Communication (Team 61)
- **Inbox:** `~/agent_comm/inbox/`
- **Outbox:** `~/agent_comm/outbox/`
- **Format:** JSON or YAML with timestamp

### Version Control
- Every canonical document includes version number (e.g., `v1.0.0`)
- Update version in filename/header when promoting to new status
- Current STYLE_GUIDE version: **v1.0.0** (as of 2026-04-10)

---

## 10. Absolute Rules (What NOT to Do)

### Naming
- ❌ Do NOT use "Famely Neuslettr" anywhere—it's a typo
- ✅ Use "Family Newsletter" (English) or "בית ולד" (Hebrew)

### Frequency & Schedule
- ❌ Do NOT use the word "daily" in any context—the cadence is weekly
- ❌ Do NOT send editions on days other than Friday unless explicitly authorized by Team 00
- ✅ Stick to weekly Friday schedule (09:00 build, 12:00 send)

### Writing
- ❌ Do NOT attempt to be clever or witty in Style A without genuine basis in the content
- ❌ Do NOT use slang or forced humor that doesn't match the family's actual tone
- ✅ Keep Style A warm, conversational, and authentic

### Visual Layout
- ❌ Do NOT leave any L2 (FEATURE) panel without a visual (image or fallback gradient+emoji)
- ❌ Do NOT render raw markdown in HTML output—convert to HTML first
- ✅ Every L2 panel must have either `image_url` or a generated fallback

### Template & Code
- ❌ Do NOT show HTML tags as visible text (e.g., displaying `<strong>Bold Text</strong>` as literal text)
- ❌ Do NOT forget the `|safe` filter when inserting HTML content into templates
- ❌ Do NOT use symlinks for character assets—use physical files only
- ✅ Always use `{{ html_variable|safe }}` for pre-rendered HTML

### Content
- ❌ Do NOT use "משפחת בן-צבי ולד" (full family name) in display—use only "בית ולד"
- ❌ Do NOT create family member names other than the five canonical members
- ✅ Stick to the canonical registry (Section 8)

---

## 11. Change Management & Deviations

### Requesting Changes
- Any deviation from this style guide requires **explicit approval from Team 00 (Nimrod)**
- Submit change request via: `_COMMUNICATION/team_100/STYLE_GUIDE_CHANGE_REQUEST_v1.0.0.md`
- Include: rationale, proposed change, impact assessment

### Version Updates
- Minor corrections (typos, clarifications): patch version (v1.0.1)
- New sections or refined rules: minor version (v1.1.0)
- Major restructuring: major version (v2.0.0)
- All updates must be dated and logged in `_COMMUNICATION/`

---

## 12. Quick Reference Checklist

Use this checklist before publishing each edition:

### Content
- [ ] Cover/masthead includes month's character (April = Cat in the Hat)
- [ ] Opener written in Style A (Simaniia Warm)
- [ ] Family Strip shows all 5 members with item counts
- [ ] Weather Forecast includes 7-day `daily` array with temps/wind/precipitation
- [ ] L1 (HERO): 1 item with image, character overlay, full summary paragraph
- [ ] L2 (FEATURE): 2-4 items, each with image or fallback gradient+emoji, 2-per-row layout
- [ ] L3 (COMPACT): 3-8 items, minimal styling
- [ ] Every family member has ≥1 item in L1+L2 combined
- [ ] Discovery Bridge includes cross-member theme connection
- [ ] Puzzle includes new puzzle + last week's solution
- [ ] Today in History: 2-3 historical facts in Style B
- [ ] Survey: 1 question in Style A with WhatsApp link + previous poll results
- [ ] Closer written in Style A
- [ ] Footer: "by AgentsOS @ nimrod.bio"

### Style & Voice
- [ ] Opener/Closer/Puzzle/Survey use Style A (warm, conversational, 8-10 word sentences)
- [ ] Headlines/summaries/history use Style B (factual, 3+ sentences, attributed sources)
- [ ] No "clever" moments without basis
- [ ] No "daily" language used anywhere
- [ ] No "Famely Neuslettr" references

### Visual & Technical
- [ ] All colors match member registry (Section 8)
- [ ] All fonts are Bangers (headers) or Patrick Hand (body)
- [ ] Background is #fdf6e3 with halftone dot overlay
- [ ] All borders are bold 3-4px solid
- [ ] All shadows are comic-style offset (4px 4px 0)
- [ ] Corner radius 12-16px on all panels
- [ ] L2 panels without images have gradient fallback (member color + emoji)
- [ ] All HTML content uses `|safe` filter in template
- [ ] All markdown converted to HTML before insertion
- [ ] Character assets placed in `assets/characters/{YYYY-MM}/`
- [ ] RTL layout for Hebrew, `.ltr` class for English blocks

### Scheduling & Submission
- [ ] Edition date is Friday (09:00 IST build, 12:00 IST send)
- [ ] All content submitted by Thursday 17:00 IST
- [ ] Edition tagged with week number and date (e.g., "Week 15, April 10-16, 2026")

---

**End of Style Guide**

*This document is binding for all agents and teams working on the Family Newsletter project. No deviation without Team 00 approval. For questions or change requests, contact via `_COMMUNICATION/` artifacts.*
