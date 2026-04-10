# Asset Intake Pipeline — Famely Neuslettr
## קליטת תוצרים גרפיים מחיצוני לשילוב בניוזלטר

---

## תהליך עבודה חודשי

```
1. PROMPT GENERATION (אוטומטי)
   │  בתחילת כל חודש, המערכת מייצרת קובץ prompt חדש
   │  בהתבסס על: CHARACTER_PROMPT_TEMPLATE.md + חודש + סגנון
   │  Output: prompts/MONTHLY_CHARACTER_PROMPT_{MONTH}.md
   │
2. MANUAL GENERATION (ידני — נימרוד)
   │  נימרוד לוקח את קובץ ה-prompt ומריץ במנוע חיצוני
   │  (Midjourney / DALL-E / Stable Diffusion / Other)
   │  Output: 6+ תמונות PNG עם רקע שקוף
   │
3. ASSET DROP (ידני)
   │  נימרוד שומר את התמונות בתיקייה:
   │  assets/characters/{year}-{month}/
   │  לפי שמות הקבצים המוגדרים ב-prompt
   │
4. VALIDATION (אוטומטי)
   │  המערכת בודקת:
   │  ✓ כל 6 הפוזות קיימות
   │  ✓ פורמט PNG
   │  ✓ רקע שקוף (alpha channel)
   │  ✓ מינימום 200x200px
   │  Output: validation report
   │
5. INTEGRATION (אוטומטי — build time)
   │  builder.py מחליף placeholders בתמונות אמיתיות
   │  Character emoji (🎩) → <img src="assets/...">
   │  Fallback: אם תמונה חסרה, נשאר emoji placeholder
   │
6. REFINEMENT (אופציונלי)
   │  אם תוצאה לא מספקת:
   │  נימרוד מעדכן prompt → מריץ שוב → שומר מחדש
   │  המערכת מזהה קבצים חדשים ומשלבת אוטומטית
```

---

## מבנה תיקיות

```
famely-neuslettr/
├── assets/
│   ├── characters/
│   │   ├── 2026-04/                    ← אפריל: Cat in the Hat
│   │   │   ├── hero-greeting.png       ← Pose 1: Hero/greeting
│   │   │   ├── reading.png             ← Pose 2: Reading
│   │   │   ├── thinking.png            ← Pose 3: Thinking/puzzle
│   │   │   ├── pointing.png            ← Pose 4: Discovery/pointing
│   │   │   ├── goodbye.png             ← Pose 5: Closer/goodbye
│   │   │   ├── icon.png                ← Pose 6: Mini icon
│   │   │   ├── scene-sailing.png       ← Scene variant (optional)
│   │   │   ├── scene-circus.png        ← Scene variant (optional)
│   │   │   └── manifest.json           ← Auto-generated metadata
│   │   ├── 2026-05/                    ← מאי: Popeye
│   │   │   └── ...
│   │   └── _placeholder/               ← Emoji fallbacks
│   │       ├── hero-greeting.svg       ← SVG placeholder
│   │       └── icon.svg
│   ├── decorations/                     ← Borders, dividers, patterns
│   └── og-images/                       ← WhatsApp preview thumbnails
├── prompts/
│   ├── CHARACTER_PROMPT_TEMPLATE.md     ← Template for all months
│   ├── MONTHLY_CHARACTER_PROMPT_APRIL.md
│   ├── MONTHLY_CHARACTER_PROMPT_MAY.md
│   └── ASSET_INTAKE_PROCESS.md          ← This file
└── src/
    ├── asset_manager.py                 ← Validation + integration
    └── builder.py                       ← Uses assets at build time
```

---

## manifest.json (auto-generated per month)

```json
{
  "month": "2026-04",
  "character_name": "Cat in the Hat",
  "character_style": "Dr. Seuss",
  "poses": {
    "hero-greeting": {
      "file": "hero-greeting.png",
      "status": "ready",
      "dimensions": [1024, 1536],
      "transparent_bg": true,
      "generated_with": "midjourney",
      "prompt_version": "v1"
    },
    "reading": { "file": "reading.png", "status": "ready" },
    "thinking": { "file": "thinking.png", "status": "missing" },
    "pointing": { "file": "pointing.png", "status": "ready" },
    "goodbye": { "file": "goodbye.png", "status": "ready" },
    "icon": { "file": "icon.png", "status": "ready" }
  },
  "scenes": {
    "sailing": { "file": "scene-sailing.png", "status": "ready" },
    "circus": { "file": null, "status": "not_generated" }
  },
  "validation": {
    "last_check": "2026-04-01T08:00:00",
    "all_required_present": false,
    "missing": ["thinking"]
  }
}
```

---

## Builder Integration (src/builder.py)

```python
# Pseudo-code for asset integration in builder

def get_character_image(pose: str, month: str = None) -> str:
    """
    Returns HTML <img> tag or emoji fallback.
    
    pose: "hero-greeting", "reading", "thinking", "pointing", "goodbye", "icon"
    month: "2026-04" (defaults to current)
    """
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    
    asset_path = f"assets/characters/{month}/{pose}.png"
    
    if os.path.exists(asset_path):
        # Use actual image
        return f'<img src="{asset_path}" alt="{pose}" class="character-img character-{pose}">'
    else:
        # Fallback to SVG placeholder or emoji
        fallback = POSE_EMOJI_MAP.get(pose, "🎩")
        return f'<span class="character-placeholder-emoji">{fallback}</span>'


# Pose → context mapping (used by builder to pick the right pose)
POSE_CONTEXT = {
    "cover":     "hero-greeting",   # Cover/header of newsletter
    "opener":    "hero-greeting",   # Opening section
    "puzzle":    "thinking",        # Puzzle/riddle section
    "discovery": "pointing",        # Discovery section
    "survey":    "thinking",        # Survey/feedback
    "closer":    "goodbye",         # Closing section
    "inline":    "icon",            # Inline decorations
    "article":   "reading",         # Article headers
}
```

---

## Character Schedule (Year 1)

| Month    | Character          | Style Reference     | Status    |
|----------|--------------------|---------------------|-----------|
| April    | Cat in the Hat     | Dr. Seuss           | ACTIVE    |
| May      | Popeye             | Classic Popeye strip| PROMPT READY |
| June     | TBD                | —                   | —         |
| July     | TBD                | —                   | —         |
| August   | TBD                | —                   | —         |
| Sept     | TBD                | —                   | —         |
| Oct      | TBD                | —                   | —         |
| Nov      | TBD                | —                   | —         |
| Dec      | TBD                | —                   | —         |
| Jan      | TBD                | —                   | —         |
| Feb      | TBD                | —                   | —         |
| March    | TBD                | —                   | —         |

**Criteria for choosing monthly characters:**
- Iconic, recognizable illustration style
- Translates well to multiple poses
- Works in both RTL and LTR contexts
- Fun and family-friendly
- Diverse styles throughout the year

**Ideas for future months:**
Tintin, Asterix, Mafalda, Calvin & Hobbes, Moomin, Snoopy, Lucky Luke, 
Totoro, Little Prince, Winnie the Pooh, Where's Waldo
