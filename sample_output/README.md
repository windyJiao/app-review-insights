# Sample Output — Cached Review Data

This directory contains review data for the demo app:

**App**: Workout for Women: Home Gym
**App ID**: 839285684
**Collected**: July 2026

## Contents

| File | Source | Count | Description |
|------|--------|-------|-------------|
| `reviews.json` | App Store CN product page HTML extraction | 8 | Reviews from China storefront |
| `reviews_us.json` | App Store US product page (via Crawlbase proxy) | 4 | Reviews from US storefront |
| `reviews_merged.json` | Combined CN + US | 12 | All reviews merged for import |

## Data Collection Notes

### CN Data (reviews.json)
Collected via `collector.py` — regex extraction of embedded `{"$kind":"Review",...}` JSON objects from the App Store CN product page HTML. Only ~8 reviews are embedded in the initial server-rendered HTML; additional reviews require browser automation that was not implemented for this assessment.

### US Data (reviews_us.json)
Collected via Crawlbase proxy service — the US App Store product page was fetched through a US residential IP. Apple only renders a handful of "featured" reviews in the initial HTML. The iTunes RSS customer reviews endpoint (`itunes.apple.com/rss/customerreviews/...`) no longer returns review data as of 2026 — it has been deprecated by Apple globally.

## Limitations

1. **Data volume is limited** — only 12 reviews total. Apple's review data is primarily served through internal AJAX APIs that are not accessible via simple HTTP requests. The iTunes RSS feed that historically provided up to 500 reviews has been discontinued.

2. **US storefront access** — the development environment is in China and cannot directly access `apps.apple.com/us`. A third-party proxy service (Crawlbase) was used to retrieve the 4 US reviews.

3. **Review IDs** — CN reviews have real App Store review IDs extracted from the page. US reviews have synthetic IDs (prefixed `us-`) because the Crawlbase text-mode response did not include structured ID fields. Rating and date information for US reviews was extracted from visible page text where available.

4. **Rating bias** — all 12 collected reviews are 4-5 stars. Apple's embedded reviews tend to favor positive feedback. A production system would need to collect reviews across the full rating spectrum.

## How to Use

### Import merged data via the app
1. Start the app (backend + frontend)
2. Click **Import Data** tab
3. Upload `reviews_merged.json` — select JSON format
4. The system will run the full AI pipeline (topic discovery → findings → PRD → test cases → validation)

### Import format

The app accepts JSON arrays of review objects with this structure:
```json
[
  {
    "id": "string",
    "rating": 1-5,
    "title": "review title",
    "content": "review body text",
    "author": "reviewer name",
    "version": "app version or null",
    "date": "ISO date string"
  }
]
```

CSV format is also supported with columns: `id, rating, title, content, author, version, date`.

## Transparency

Per assessment requirements: "If the amount of available data is limited or data collection is constrained, state this transparently in the results. Do not fabricate data."

This dataset is small but authentic. The application's analysis pipeline is designed to handle this — when evidence is thin (<20 reviews), the LLM prompts automatically constrain output scope (fewer versions, fewer requirements, explicit assumption marking) and the validation stage downgrades confidence for findings with insufficient supporting reviews.
