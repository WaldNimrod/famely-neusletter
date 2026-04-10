# SVG Module — Famely Neuslettr
## מודול יצירת אלמנטים ויזואליים באמצעות SVG

**גרסה:** 1.0.0  
**תאריך:** 2026-04-10  
**סטטוס:** Architecture Design

---

## 1. הבעיה

הניוזלטר צריך אלמנטים ויזואליים מקוריים, איכותיים ומעניינים:
- **Hero Section** — אלמנט ויזואלי מרכזי בכל ניוזלטר
- **Section Dividers** — הפרדות בין חלקי הניוזלטר
- **Member Avatars** — דמויות מאויירות של בני המשפחה
- **Thematic Icons** — אייקונים ייחודיים לנושאים (שייט, קרקס, כימיה...)
- **Seasonal/Holiday Art** — אלמנטים עונתיים וחגיגיים
- **Book/Content Cards** — כרטיסי תוכן עם ויזואל

### אתגרים:
1. SVG שנוצר ע"י LLM יכול להיות גנרי או שבור
2. קשה לשמר עקביות סגנונית בין הפעלות
3. אין פרוטוקול ברור לאיטרציה ושיפור
4. תוכן דינמי = צריך מערכת, לא קובץ חד-פעמי

---

## 2. ארכיטקטורת המודול

### עקרון מנחה: **Design Token → Template → Render → Refine**

```
┌─────────────────────────────────────────────────────────┐
│                    SVG MODULE PIPELINE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LAYER 1: DESIGN SYSTEM (קבוע, מוגדר פעם אחת)         │
│  ├─ Color palette (per member, per season)               │
│  ├─ Typography tokens (sizes, weights)                   │
│  ├─ Character library (family members as illustrations) │
│  ├─ Icon library (topic icons — sailing, circus, etc.)  │
│  └─ Style guide (line weight, corner radius, texture)   │
│                                                         │
│  LAYER 2: TEMPLATES (מבנים קבועים, תוכן דינמי)        │
│  ├─ hero-template.svg — מבנה ה-Hero עם placeholders     │
│  ├─ divider-template.svg — הפרדות בין sections          │
│  ├─ card-template.svg — כרטיס תוכן                     │
│  └─ badge-template.svg — badge-ים ותגיות               │
│                                                         │
│  LAYER 3: GENERATOR (אייג'נט שמייצר SVG)              │
│  ├─ Input: תוכן יומי + template + design tokens         │
│  ├─ Process: Claude generates SVG with constraints       │
│  ├─ Output: SVG string, validated                        │
│  └─ Validation: syntax check + visual preview            │
│                                                         │
│  LAYER 4: REFINEMENT (איטרציה ושיפור)                  │
│  ├─ Preview → Screenshot → Evaluate                      │
│  ├─ Human feedback: "יותר צבעוני" / "הדמות קטנה"       │
│  ├─ Auto-retry with adjusted prompt                      │
│  └─ Save successful outputs as examples                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Design System — הגדרות קבועות

### 3.1 צבעים
```json
{
  "members": {
    "nimrod":  { "primary": "#2471a3", "light": "#e6f0fa", "accent": "#1a5276" },
    "michal":  { "primary": "#27ae60", "light": "#e6f5ed", "accent": "#1e8449" },
    "shaked":  { "primary": "#7d3c98", "light": "#ece6f5", "accent": "#6c3483" },
    "maayan":  { "primary": "#c0392b", "light": "#fce8ec", "accent": "#a93226" },
    "tzlil":   { "primary": "#e67e22", "light": "#fef3e2", "accent": "#ca6f1e" }
  },
  "shared": {
    "bg": "#fdf6e3",
    "ink": "#2c2c2c",
    "warm": "#f39c12",
    "cool": "#2980b9",
    "nature": "#27ae60"
  },
  "seasons": {
    "spring": ["#a8d8a8", "#f9e79f", "#f5b7b1"],
    "summer": ["#85c1e9", "#f9e79f", "#f5cba7"],
    "autumn": ["#e59866", "#d4ac0d", "#a04000"],
    "winter": ["#aeb6bf", "#d5d8dc", "#85c1e9"]
  }
}
```

### 3.2 סגנון אילוסטרציה
```
STYLE GUIDE:
- Line weight: 2-3px (bold, friendly)
- Corners: rounded (border-radius feel)
- Fills: flat colors with subtle gradients
- Texture: minimal halftone dots or crosshatch for depth
- Vibe: "editorial illustration meets comic strip"
- NO photorealism, NO 3D, NO complex shadows
- Characters: simple, expressive, warm (Quentin Blake meets Hergé)
```

### 3.3 Character Library — דמויות המשפחה

כל בן משפחה מיוצג ע"י דמות SVG קבועה עם וריאציות:

| Member   | Visual Identity                          | Props / Context          |
|----------|------------------------------------------|--------------------------|
| נימרוד   | גבר עם זקן קצר, כובע סקיפר             | הגה ספינה, עפיפון קייט, לפטופ |
| מיכל     | אישה עם שיער חום ארוך, בגדי עבודה       | סרגל T, עציץ, ברימבאו     |
| שקד      | נער גבוה, שיער בהיר, אוזניות           | ספר, מבחנה, Switch        |
| מעיין    | נערה אנרגטית, שיער אסוף, בגדי ספורט    | חישוק אוויר, טרפז, אינסטגרם |
| צליל     | ילדה עם משקפיים, שיער חום, חיוך חכם     | מספרים/חידות, תנור, VR     |

---

## 4. Hero Section Logic

### עיקרון: ה-Hero תמיד כולל דמות + נושא שמעניין את הרוב

```python
def select_hero_topic(curated_content, family_members):
    """
    בחירת נושא ה-Hero:
    1. חשב relevance_score ממוצע לכל נושא על פני כל בני המשפחה
    2. תן עדיפות לנושאים משותפים (shared_interests)
    3. תן boost לתוכן משפחתי (family_content)
    4. בחר את הנושא עם הציון הגבוה ביותר
    """
    topic_scores = {}
    for item in curated_content:
        topic = item['topic']
        # ציון = ממוצע הרלוונטיות לכל בני המשפחה
        avg_score = mean([item.scores.get(m.id, 0) for m in family_members])
        # boost לנושאים משותפים
        if topic in shared_interests:
            avg_score *= 1.5
        # boost לתוכן משפחתי
        if item.source_type == 'family':
            avg_score *= 2.0
        topic_scores[topic] = max(topic_scores.get(topic, 0), avg_score)
    
    return max(topic_scores, key=topic_scores.get)


def generate_hero_svg(topic, member_focus, content_item):
    """
    יצירת ה-Hero SVG:
    - topic: הנושא שנבחר
    - member_focus: בן המשפחה הכי רלוונטי לנושא
    - content_item: הפריט הספציפי
    
    ה-Hero תמיד כולל:
    1. דמות (character) — בן המשפחה הרלוונטי
    2. סצנה (scene) — רקע שקשור לנושא
    3. כותרת (headline) — מוטמעת ב-SVG
    4. אלמנטים דקורטיביים — קשורים לנושא
    """
    pass
```

### Hero Composition Rules

```
┌─────────────────────────────────────────┐
│  HERO SVG (640 x 360)                   │
│                                         │
│  ┌─────────┐  ┌─────────────────────┐   │
│  │ CHARACTER│  │  SCENE / BACKDROP   │   │
│  │  (left   │  │  (related to topic) │   │
│  │  or RTL  │  │                     │   │
│  │  right)  │  │  ┌───────────────┐  │   │
│  │          │  │  │  HEADLINE     │  │   │
│  │  ╔═══╗   │  │  │  (inside SVG) │  │   │
│  │  ║   ║   │  │  └───────────────┘  │   │
│  │  ╚═══╝   │  │                     │   │
│  └─────────┘  └─────────────────────┘   │
│                                         │
│  [decorative elements: waves, stars...] │
└─────────────────────────────────────────┘
```

### Hero Themes (topic → visual mapping)

| Topic                  | Scene              | Character       | Decorations           |
|------------------------|--------------------|-----------------|-----------------------|
| שייט / ים              | ים, גלים, אופק    | נימרוד עם הגה    | מפרשים, ציפורי ים    |
| קייט                   | חוף, רוח, שמיים    | נימרוד עם עפיפון | גלים, שמש, רוח       |
| ארכיטקטורה ירוקה       | בית טבעי, טבע      | מיכל עם תוכניות  | עלים, עץ, חלון       |
| קפוארה                | מעגל רודה           | מיכל בתנועה      | ברימבאו, פנדיירו     |
| קרקס                  | אוהל קרקס, במה     | מעיין על טרפז    | כוכבים, ספוטלייט    |
| כימיה / מדע           | מעבדה              | שקד עם מבחנה     | מולקולות, אטומים    |
| מתמטיקה / חידות       | לוח עם נוסחאות     | צליל עם משקפיים  | מספרים, סימנים       |
| משפחתי / כולם          | סלון / גינה        | כל המשפחה        | משחקי חברה, אוכל    |
| גינון / קיימות        | גינה, ירקות        | נימרוד + צליל    | צמחים, פרפרים       |
| ספרים / קריאה          | ספריה, מדף ספרים    | כל המשפחה        | ספרים פתוחים        |

---

## 5. Agent Prompt — SVG Generator

```markdown
# SVG Generator Agent — Famely Neuslettr

## Role
You are the visual artist for the Ben-Tzvi Wald family newsletter.
You create SVG illustrations that are: warm, original, media-rich, and contextual.

## Design Constraints
- Canvas: 640 x 360 px (hero), 640 x 80 px (dividers), 120 x 120 px (avatars)
- RTL layout (Hebrew text flows right-to-left)
- Hebrew font: system sans-serif (no custom fonts in SVG for compat)
- Style: flat illustration, bold outlines (2-3px), rounded forms
- Colors: use the design tokens from design_system.json
- MUST include character(s) — never leave hero empty of people
- MUST be contextual to the daily content

## Input Format
```json
{
  "type": "hero|divider|avatar|icon",
  "topic": "sailing",
  "headline_he": "סקיפר ישראלי הפליג סביב העולם",
  "headline_en": "Israeli skipper sails around the world",
  "member_focus": "nimrod",
  "season": "spring",
  "mood": "adventurous|warm|playful|intellectual|energetic",
  "content_hint": "Brief description of the content for visual context",
  "iteration": 1,
  "feedback": null
}
```

## Output Format
```json
{
  "svg": "<svg ...>...</svg>",
  "description": "Scene description for accessibility",
  "tokens_used": { "colors": [...], "elements": [...] }
}
```

## Character Drawing Guide
[Each family member's visual description from Section 3.3]

## Iteration Protocol
- iteration 1: Generate based on input
- iteration 2+: Apply feedback adjustments
- Feedback format: "make character larger", "more blue", "add waves"
- ALWAYS preserve the core composition when iterating
- NEVER start from scratch on iteration — modify the previous output

## Quality Checklist (self-validate before output)
- [ ] SVG is valid XML
- [ ] viewBox is set correctly
- [ ] Text is readable (font-size >= 14 for Hebrew)
- [ ] Character is present and recognizable
- [ ] Colors match design tokens
- [ ] Scene matches topic
- [ ] RTL text direction where needed
- [ ] No clipPath issues (keep simple)
- [ ] Responsive (use viewBox, not fixed width/height)
```

---

## 6. תהליך עבודה — הרצה ואיטרציה

### Flow עבור כל ניוזלטר:

```
1. PIPELINE selects hero topic (auto, based on scoring)
2. PIPELINE prepares SVG input payload
3. SVG AGENT generates hero (iteration 1)
4. PREVIEW renders in HTML template
5. IF auto-mode: validate + proceed
   IF manual-mode: show to Nimrod → collect feedback
6. IF feedback: SVG AGENT generates iteration 2+
7. SAVE successful SVG to examples library
8. EMBED in final newsletter HTML
```

### איטרציה ידנית (Nimrod's refinement):

```
# Terminal / Chat flow:
> show hero
[displays SVG in browser]

> refine: "הדמות קטנה מדי, תגדיל. תוסיף גלים"
[agent modifies SVG, iteration 2]

> good
[saved to library as example]
```

### Example Library — למידה מצטברת

כל SVG מוצלח נשמר עם metadata:
```json
{
  "id": "hero-2026-04-10",
  "type": "hero",
  "topic": "sailing",
  "svg_path": "data/svg/heroes/2026-04-10.svg",
  "feedback_history": ["iteration 1: ok but waves too small", "iteration 2: approved"],
  "rating": 5,
  "reuse_for": ["sailing", "sea", "kite"]
}
```

הספרייה הזו מאפשרת לאייג'נט ללמוד מהצלחות קודמות ולשמר עקביות.

---

## 7. קבצי הפרויקט

```
famely-neuslettr/
├── svg/
│   ├── design_system.json       ← צבעים, סגנון, tokens
│   ├── characters/
│   │   ├── nimrod.svg            ← דמות בסיס
│   │   ├── michal.svg
│   │   ├── shaked.svg
│   │   ├── maayan.svg
│   │   └── tzlil.svg
│   ├── templates/
│   │   ├── hero-template.svg    ← מבנה hero עם placeholders
│   │   ├── divider-template.svg
│   │   └── card-template.svg
│   ├── icons/
│   │   ├── sailing.svg
│   │   ├── circus.svg
│   │   ├── chemistry.svg
│   │   ├── math.svg
│   │   └── ...
│   ├── examples/                 ← SVGs מוצלחים (reference library)
│   │   └── hero-2026-04-10.svg
│   └── output/                   ← SVGs של היום
│       └── hero-today.svg
├── src/
│   ├── svg_generator.py          ← SVG Agent orchestrator
│   ├── svg_validator.py          ← XML + visual validation
│   └── svg_templates.py          ← Template engine
└── prompts/
    └── svg_agent_prompt.md       ← Agent prompt (Section 5 above)
```

---

## 8. WhatsApp Group vs Individual — ניתוח

### המצב הנוכחי (Spec)
שליחה לכל בן משפחה בנפרד (per-phone template message)

### האלטרנטיבה — שליחה לקבוצה

| Aspect | Individual | Group |
|--------|-----------|-------|
| **פרסונליזציה** | מלאה — כל אחד מקבל תוכן שונה | חלקית — כולם רואים אותו דבר |
| **WhatsApp API** | Template messages (approved) | Group API (limited in Business API) |
| **עלות** | לפי הודעה (per-message pricing) | הודעה אחת (חסכון) |
| **חוויה** | אישי, "הניוזלטר שלך" | משפחתי, "דף שלנו" |
| **משוב** | סקר 1-on-1 | תגובות בקבוצה (organic!) |
| **טכני** | Twilio/Meta Business API | Bot in existing group / new group |

### המלצה: **Hybrid Model**

```
שליחה לקבוצה המשפחתית:
  - הודעת בוקר עם קישור לניוזלטר (אחד לכולם)
  - הניוזלטר עצמו הוא פרסונלי (sections per member)
  - כולם רואים את כל הסקשנים (discovery מובנה!)

+ שליחה אישית (אופציונלי):
  - סקר משוב בערב (1-on-1, לא בקבוצה)
  - אלרטים ספציפיים ("יויו — CNAC פתחו הרשמה!")
```

### יתרונות Hybrid:
1. **קבוצה = שיחה** — בני המשפחה מגיבים, משתפים, מדברים על התכנים
2. **ניוזלטר אחד = כולם** — כל אחד רואה את הסקשן שלו + של האחרים
3. **משוב אישי = פרטי** — סקר בערב בהודעה אישית
4. **חסכון** — הודעה אחת במקום 5

### Implementation (WhatsApp Group):

**אפשרות א': WhatsApp Business API — Send to Group**
- Meta Business API תומך בשליחת הודעות לקבוצות (מוגבל)
- צריך שה-bot יהיה admin בקבוצה
- Template messages לא עובדים בקבוצות — צריך regular messages

**אפשרות ב': Green API / wwebjs**
- ספריות שמחברות ל-WhatsApp Web
- יותר גמישות, פחות רשמי
- סיכון: WhatsApp יכולים לחסום

**אפשרות ג': קבוצת WhatsApp ייעודית + Bot**
- יצירת קבוצה "הניוזלטר המשפחתי"
- Bot נכנס כ-admin
- שולח הודעת בוקר + link
- מקבל תגובות (organic feedback!)

---

## 9. ספריית הספרים — תיעוד

15 ספרים מהמדף המשפחתי (צולמו 2026-04-10):

| # | Title (HE) | Author | Original Title | Category |
|---|-----------|--------|---------------|----------|
| 1 | חולית | פרנק הרברט | Dune | Sci-Fi |
| 2 | זבל אנושי | ג'וזף ג'נקינס | The Humanure Handbook | Sustainability |
| 3 | חקלאות ביו-דינמית | רודולף שטיינר | Agriculture Course | Biodynamic / Steiner |
| 4 | סופה של אליס | גלית דהן קרליבך | — (Israeli) | Israeli Literature |
| 5 | כיצד קונים דעת העולמות העליונים? | רודולף שטיינר | How to Know Higher Worlds? | Anthroposophy |
| 6 | גוף, נפש, רוח | רודולף שטיינר | Body, Soul, Spirit (Theosophy) | Anthroposophy |
| 7 | קטן זה יפה | א.פ. שומאכר | Small is Beautiful | Economics / Sustainability |
| 8 | טוטם הזאב | ג'יאנג רונג | Wolf Totem | Chinese Literature |
| 9 | הקשת | פאולו קואלו | The Archer | Spirituality |
| 10 | גינת בר | מאיר שלו (ציורים: רפאלה שיר) | My Wild Garden | Nature / Israeli |
| 11 | חמשת האנשים שתפגוש בגן-עדן | מיצ'י אלבום | The Five People You Meet in Heaven | Fiction |
| 12 | דבורים | רודולף שטיינר | Bees | Biodynamic / Steiner |
| 13 | היסטוריה של מהירות | עמית נויפלד | — (Israeli) | Philosophy / Slowness |
| 14 | ארבע ההסכמות | דון מיגל רואיס | The Four Agreements | Spirituality |
| 15 | ורד הכלב | עליזה גלקין-סמית | Dog Rose | Botanical / Nature |

### Profile Insights (מה הספרים מגלים):

**נושאים דומיננטיים:**
- **אנתרופוסופיה / שטיינר** (4 ספרים!) — חקלאות, דבורים, רוחניות, ידע עליון
- **קיימות וטבע** — הומנור, ביו-דינמי, קטן זה יפה, גינת בר, ורד הכלב
- **רוחניות / פילוסופיה** — ארבע ההסכמות, הקשת, שטיינר
- **ספרות** — חולית, טוטם הזאב, סופה של אליס, חמשת האנשים
- **Slow Living** — היסטוריה של מהירות (מדריך להאטה)

**רלוונטיות לפרופילי המשפחה:**
- מיכל ← שטיינר (חינוך אנתרופוסופי), ארכיטקטורה ירוקה, טבע
- נימרוד ← קיימות, גידול מזון, ביו-דינמי, דבורים
- כולם ← ספרות, רוחניות, טבע

### שימוש בניוזלטר:
אפשר להשתמש בספרים כ:
1. **"מהמדף שלנו"** — מדור שבועי שמציג ספר מהמדף + רלוונטיות היום
2. **Hero content** — "חולית" + חדשות מדע = hero אפי
3. **Discovery** — "צליל, את אוהבת חידות? בספר 'חולית' יש..."
4. **Visual elements** — עטיפות הספרים כטקסטורה ב-SVG
