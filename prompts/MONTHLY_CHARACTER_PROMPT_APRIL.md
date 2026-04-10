# Monthly Character Generation Prompt
## April 2026 — Cat in the Hat (Dr. Seuss style)

**Target Engine:** Midjourney / DALL-E / Stable Diffusion / Any illustration AI
**Output Format:** PNG with transparent background, 1024x1024px minimum
**Style Reference:** Dr. Seuss "The Cat in the Hat" — simplified, bold lines, whimsical

---

## Character Description

**Name:** The Newsletter Cat (חתול הניוזלטר)
**Style:** Dr. Seuss illustration — tall striped red-and-white hat, white fur, bold black outlines, whimsical proportions, expressive eyes, mischievous grin
**Outfit:** Tall red-and-white striped stovepipe hat, red bow tie
**Personality:** Cheerful, playful, curious, slightly mischievous
**Color Palette:**
- Body: white with black outlines
- Hat: alternating red (#c0392b) and white stripes
- Bow tie: red (#c0392b)
- Eyes: large, white sclera, black pupils
- Accent: yellow/gold (#f39c12) for highlights

---

## Required Poses (6 variants)

### Pose 1: HERO — Greeting/Welcome (Large, prominent)
```
Prompt: A whimsical Dr. Seuss-style cat character standing tall, wearing a tall red-and-white striped hat, waving one paw enthusiastically in greeting. The other paw holds a rolled-up newspaper. Full body visible. White background. Bold black outlines, flat colors, playful cartoon style. Expressive wide smile. Hebrew-friendly (faces right for RTL layout).

Size: Full body, standing, facing right
Use: Main hero section of newsletter
Dimensions: at least 400x600px
```

### Pose 2: READING — Holding a book/newspaper
```
Prompt: A whimsical Dr. Seuss-style cat character sitting cross-legged, wearing a tall red-and-white striped hat, reading a newspaper/book with an interested expression. Eyes looking down at the text. Bold black outlines, flat colors. White background.

Size: Sitting, medium size
Use: Content sections, article headers
Dimensions: at least 300x400px
```

### Pose 3: THINKING — Puzzle/riddle pose
```
Prompt: A whimsical Dr. Seuss-style cat character with chin resting on one paw, looking upward thoughtfully. Tall red-and-white striped hat tilted slightly. Question marks floating above. Bold black outlines, flat colors. White background.

Size: Upper body/bust
Use: Puzzle section, trivia
Dimensions: at least 200x300px
```

### Pose 4: POINTING — Discovery/surprise
```
Prompt: A whimsical Dr. Seuss-style cat character pointing excitedly to the right with one paw, eyes wide with surprise/excitement. Tall red-and-white striped hat, red bow tie. An exclamation mark near the pointing paw. Bold black outlines, flat colors. White background.

Size: Upper body with extended arm
Use: Discovery section, alerts
Dimensions: at least 300x300px
```

### Pose 5: WAVING GOODBYE — Closer
```
Prompt: A whimsical Dr. Seuss-style cat character waving goodbye with one paw while tipping the tall red-and-white striped hat with the other. Warm smile. Small hearts or stars around. Bold black outlines, flat colors. White background.

Size: Full body
Use: Newsletter closing section
Dimensions: at least 300x500px
```

### Pose 6: MINI ICON — Tiny mascot for inline use
```
Prompt: A tiny simplified icon version of a Dr. Seuss-style cat face — just the face with the tall red-and-white striped hat, big eyes, and smile. Minimal details, works at small sizes. Bold black outlines. White background.

Size: Face only, circular crop friendly
Use: Inline decorations, bullet points, section markers
Dimensions: at least 120x120px
```

---

## Scene Variants (Optional, for Hero backgrounds)

### Scene A: Sailing/Sea Theme (for Nimrod's content)
```
Prompt: A whimsical Dr. Seuss-style cat character standing at the helm of a cartoon sailboat, wearing a tall red-and-white striped hat and a captain's jacket. Stylized waves, seagulls, and Mediterranean coastline in background. Bold black outlines, flat bright colors, playful composition.
```

### Scene B: Architecture/Nature Theme (for Michal's content)
```
Prompt: A whimsical Dr. Seuss-style cat character standing next to a quirky organic-shaped green building surrounded by plants and trees. Wearing a hard hat over the striped hat. Holding blueprints. Bold black outlines, flat colors.
```

### Scene C: Circus Theme (for Maayan's content)
```
Prompt: A whimsical Dr. Seuss-style cat character hanging from a trapeze under a circus tent, wearing the tall striped hat (somehow staying on!). Spotlights, stars, and circus decorations. Bold black outlines, flat bright colors.
```

### Scene D: Science/Lab Theme (for Shaked's content)
```
Prompt: A whimsical Dr. Seuss-style cat character in a laboratory, wearing the striped hat and lab goggles. Holding a bubbling flask. Molecular structures and equations float around. Bold black outlines, flat colors. LTR orientation.
```

### Scene E: Math/Puzzle Theme (for Tzlil's content)
```
Prompt: A whimsical Dr. Seuss-style cat character surrounded by floating numbers, geometric shapes, and mathematical symbols. Wearing the striped hat and glasses. Looking clever and contemplative. Bold black outlines, flat colors.
```

### Scene F: Family/Shared Theme
```
Prompt: A whimsical Dr. Seuss-style cat character in a cozy living room setting, surrounded by board games, a bookshelf, and potted plants. Welcoming pose. Warm colors. Bold black outlines, flat colors.
```

---

## Technical Requirements

1. **Transparent background** — all character images must have transparent/removable background
2. **Consistent style** — all 6 poses must look like the same character
3. **Bold outlines** — 3-4px black outlines for comic feel
4. **RTL-friendly** — character generally faces right (for Hebrew newsletter layout)
5. **Scalable** — images should work from 60px to 400px width
6. **High contrast** — readable when placed over any background

---

## Integration Instructions

After generating images, save them to:
```
famely-neuslettr/
└── assets/
    └── characters/
        └── 2026-04/
            ├── cat-hero-greeting.png
            ├── cat-reading.png
            ├── cat-thinking.png
            ├── cat-pointing.png
            ├── cat-goodbye.png
            ├── cat-icon.png
            ├── scene-sailing.png    (optional)
            ├── scene-architecture.png (optional)
            ├── scene-circus.png     (optional)
            ├── scene-science.png    (optional)
            ├── scene-math.png       (optional)
            └── scene-family.png     (optional)
```

The newsletter builder (`src/builder.py`) will look for these assets at build time and embed them in the HTML. Character placeholders (🎩 emoji) will be replaced with actual images.

---

## Next Month (May 2026): Popeye

The May character should follow this same template format but with:
- **Style:** Classic Popeye comic strip — strong jaw, pipe, spinach, anchor tattoo
- **Poses:** Same 6 poses adapted to Popeye's character
- **Scenes:** Adapted to family topics with Popeye's nautical theme
