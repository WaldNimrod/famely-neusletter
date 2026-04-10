# Pilot report — Family Newsletter v3.0.0 (2026-04-10)

## Status: **PARTIAL — not production-ready**

Automated run on **2026-04-10** (local). **M2 + weather + HTML render succeeded.** **All Anthropic API calls failed** with **HTTP 401 Unauthorized** (key present in `.env` but **rejected by the API** — invalid, revoked, or typo). The pipeline **does not** emit `[Mock response …]` in this failure mode; [`m3_normalizer.py`](src/m3_normalizer.py) **catch** blocks supply **static fallbacks** (short greeting, titles/raw text for summaries, generic opener copy, etc.) — editorial quality is **not** full Claude.

**Distribution:** `weekly-send` **failed**: FTP **`530 Login incorrect`** after 3 retries (credentials in `.env` do not authenticate to `UPRESS_SFTP_HOST`). Emails were **not** sent (M5 aborts when FTP fails).

---

## Run metadata (2026-04-10)

| Field | Value |
|-------|--------|
| `weekly-build` start | ~14:24 local |
| `weekly-build` duration | ~301 s (Anthropic retries per operation) |
| HTML output | `data/archive/html/2026-04-10.html` — **40,602** bytes |
| Footer | `v3.0.0 • built 2026-04-10 14:29:47` |
| M2 items fetched | **160** |
| Items selected | **10** (5 member + 5 discovery) |
| Token cost (DB) | **$0.00** (no successful billed calls) |
| `anthropic` SDK | Installed in `venv`; added to [`requirements.txt`](requirements.txt) (was optional/commented) |

---

## Anthropic API (blocking)

- **Symptom:** Every `tt.generate` call: `401 Client Error: Unauthorized` for `https://api.anthropic.com/v1/messages`.
- **Intermittent:** `Network is unreachable` (errno 51) on some retries — secondary.
- **Action required:** In [Anthropic Console](https://console.anthropic.com/), verify the key, billing, and project access; **replace** `ANTHROPIC_API_KEY` in `.env` if needed; **rotate** if the key was ever exposed.

---

## Git state (reference)

| Item | Value |
|------|--------|
| Tag | `v3.0.0` → `7ab2b14` |
| Later commits | e.g. mock greeting `f9b9dc5`, handoff/docs — see `git log` |

---

## Environment (names only; no secrets)

| Variable | Note |
|----------|------|
| `ANTHROPIC_API_KEY` | Set in `.env`; **API returns 401** — treat as **invalid until fixed** |
| `UPRESS_SFTP_*` | Host/user set; **login rejected (530)** on `weekly-send` |
| SMTP | Present in `.env`; not exercised after FTP failure |

---

## Build (`weekly-build`, no `--mock`)

- **M2:** 160 NCIs; sources include Yachting World, ArchDaily, Numberphile, etc. Known issues: Cirque du Soleil channel ID unresolved; Aerial Expo Blog connection refused.
- **M3:** Curated 10 items; **Claude** steps all failed → fallbacks used.
- **Weather (Open-Meteo):** Pardes Hanna ~20°; Basel ~17° (from log).
- **M4:** Rendered HTML as above.

---

## Validation (local `2026-04-10.html`)

| Check | Result |
|-------|--------|
| File size | 40,602 bytes (> 10 KB) |
| `example.com` | 0 |
| `Mock response` | **0** (failures use **fallback** strings, not mock placeholders) |
| `placeholder` (grep) | Matches **CSS** `character-placeholder` + visible template text (known template issue) |
| `בית ולד` | Present |
| `v3.0.0` in footer | Present |
| `hero-visual` / `feat-visual` | Present |
| `weather-section`, opener block | Present |

**Link HEAD sample (not exhaustive):** some sources return **403** to automated HEAD — see earlier mandate notes.

---

## Distribution (`weekly-send`)

| Step | Result |
|------|--------|
| FTP upload | **Failed** — `530 Login incorrect` (×3) |
| Public URL update | N/A |
| Email to family | **Not sent** (blocked by FTP failure in current M5 flow) |

---

## Public URL (intended)

https://www.nimrod.bio/agents/newsletter/2026-04-10/index.html

*(Live page will not match this local build until a **successful** upload uses correct FTP credentials and paths.)*

---

## Recommended next steps

1. **Fix Anthropic key** — confirm **401** resolved with a one-off `curl` or tiny script; then rebuild (`rm` DB + date HTML first).
2. **Fix FTP** — confirm uPress username/password (panel); test FTP from same machine; align `UPRESS_UPLOAD_PATH` + `UPRESS_PUBLIC_BASE` with the real folder for `agents/newsletter/...`.
3. Re-run **`weekly-build`** → **`weekly-send`** → `curl` 200 + spot-check in browser.
4. **Sunday target:** once 1–2 succeed, send edition; adjust cron if product wants **Sunday** vs documented **Friday** schedule.

---

## Claude API cost (this run)

**$0.00** — no successful Anthropic completions logged to `token_usage`.
