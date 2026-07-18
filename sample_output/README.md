# Sample Output — Cached Analysis Data

This directory contains cached review data and analysis results for the demo app:

**App**: Workout for Women: Home Gym  
**App ID**: 839285684  
**Store**: CN (China) — US storefront was not accessible from the development environment  
**Collected**: July 2026

> ⚠️ **Note to reviewers**: This cached data is provided for offline review only.  
> The application can process any App Store URL or imported dataset when network and LLM access are available.

## Contents

| File | Description |
|------|-------------|
| `reviews.json` | 8 raw reviews collected from the App Store CN product page |
| `analysis_result.json` | Full analysis pipeline output (findings, PRD, test cases, validation) |

## How to Use

### Option 1: Upload via Import tab

1. Start the app (backend + frontend)
2. Click **Import Data** tab
3. Upload `reviews.json` — select JSON format
4. The system will run the full AI pipeline on this data

### Option 2: Review cached result directly

Open `analysis_result.json` to see the complete pipeline output without running the app.

## Data Notes

- **Source**: App Store CN product page HTML extraction
- **Method**: `collector.py` — regex extraction of embedded JSON review objects
- **Limitations**: Only 8 reviews (initial page load). US storefront was not accessible from the development environment; per assessment guidelines, US data is preferred when available.
