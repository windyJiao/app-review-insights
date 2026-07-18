# App Store Review Analyzer

AI-powered iOS App Store review analysis tool. Collects reviews, discovers topics, generates evidence-grounded findings, produces a PRD with version planning, and creates traceable test cases — all through a web UI.

## Features

- **Review Collection**: Fetches reviews via Apple's official iTunes RSS feed (no scraping)
- **Data Cleaning**: Exact + fuzzy deduplication, quality flagging, language detection
- **AI Topic Discovery**: LLM-powered dynamic topic clustering (no fixed keyword maps)
- **Evidence-Grounded Findings**: Every finding includes source reviews, confidence scores, conflicting evidence, and uncertainty notes
- **PRD Generation**: Multi-version product plan with traceable requirements, assumptions explicitly marked
- **Test Case Generation**: Executable test cases linked to requirements and source reviews
- **Traceability Validation**: Deterministic chain verification from reviews → findings → requirements → test cases
- **Data Import**: Supports JSON and CSV review datasets for offline analysis

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SSE streaming |
| AI/LLM | OpenAI-compatible API (structured outputs) |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Data | App Store RSS feeds (XML) |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (or compatible provider)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/windyJiao/app-review-insights.git
cd app-review-insights

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY
```

### 2. Setup Frontend

```bash
cd ../frontend
npm install
```

### 3. Run

Terminal 1 — Backend:
```bash
cd backend
python -m app.main
# or: uvicorn app.main:app --reload --port 8000
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## Usage

### Analyze from App Store

1. Enter an App Store URL (defaults to the workout app example)
2. Optionally set an analysis goal (e.g., "focus on subscription conversion")
3. Click **Start Analysis**
4. Watch real-time progress through the 7-stage pipeline
5. Browse results across 7 tabs: Overview, Reviews, Topics, Findings, PRD, Test Cases, Traceability

### Import Review Data

1. Switch to **Import Data** tab
2. Upload a JSON or CSV file

**JSON format:**
```json
[
  {
    "id": "123",
    "rating": 4,
    "title": "Great app",
    "content": "Love the workouts...",
    "author": "User123",
    "version": "2.5.0",
    "date": "2024-01-15"
  }
]
```

**CSV format:**
```csv
id,rating,title,content,author,version,date
123,4,Great app,Love the workouts...,User123,2.5.0,2024-01-15
```

## Architecture

```
reviews (RSS feed / import)
    │
    ▼
[Collect] ─── App Store RSS XML parser
    │
    ▼
[Clean] ───── MD5 dedup + n-gram fuzzy matching + quality heuristics
    │
    ▼
[Classify] ── LLM topic discovery (batch + merge)  ← AI
    │
    ▼
[Analyze] ─── LLM findings with evidence grounding  ← AI
    │
    ▼
[PRD] ─────── LLM version planning + requirements    ← AI
    │
    ▼
[Tests] ───── LLM test case generation               ← AI
    │
    ▼
[Validate] ── Deterministic traceability check
```

## Design Decisions: Rules vs AI

| Stage | Method | Rationale |
|-------|--------|-----------|
| Collection | **Deterministic** | RSS feed parsing is well-defined |
| Cleaning/Dedup | **Deterministic** | Exact solutions exist (hashing, n-grams) |
| Topic Discovery | **LLM** | Topics vary by app; need semantic understanding |
| Finding Analysis | **LLM** | Requires synthesis, confidence assessment, contradiction detection |
| PRD Generation | **LLM** | Strategic planning needs domain reasoning |
| Test Case Gen | **LLM** | Creative edge-case design from abstract requirements |
| Validation | **Deterministic** | Reference checking is rule-based |

## Data Source

Reviews are collected from Apple's official iTunes RSS feed:
```
https://itunes.apple.com/{country}/rss/customerreviews/id{app_id}/xml
```

**Limitations:**
- Max ~500 reviews (10 pages × 50 per page)
- Only most recent reviews available
- No historical data beyond what the feed provides
- XML format requires parsing (JSON endpoint lacks pagination)

## Model Configuration

The application uses OpenAI-compatible APIs. Configure via `.env`:

```
OPENAI_API_KEY=your-key        # Required
OPENAI_BASE_URL=...             # Default: https://api.openai.com/v1
OPENAI_MODEL=gpt-4o             # Default: gpt-4o
```

**Hallucination reduction:**
- All LLM calls use structured output (function calling with JSON schema)
- Post-generation validation checks review IDs against actual dataset
- Unsupported findings are removed; unreferenced requirements marked as assumptions
- Model-generated conclusions are distinguished from deterministic statistics

**Model-agnostic:** Works with any OpenAI-compatible provider (Azure, Ollama, local models, etc.)

## Project Structure

```
app-review-insights/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── models/schemas.py       # Pydantic data models
│   │   ├── routes/
│   │   │   ├── analyze.py          # Main SSE streaming endpoint
│   │   │   └── import_data.py      # File import endpoint
│   │   ├── services/
│   │   │   ├── collector.py        # App Store RSS feed collector
│   │   │   ├── cleaner.py          # Dedup & quality flagging
│   │   │   ├── classifier.py       # LLM topic discovery
│   │   │   ├── analyzer.py         # LLM findings generation
│   │   │   ├── prd_generator.py    # LLM PRD generation
│   │   │   ├── testcase_gen.py     # LLM test case generation
│   │   │   └── validator.py        # Traceability validation
│   │   └── utils/
│   │       └── llm.py              # OpenAI client abstraction
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── InputForm.tsx
│   │   │   ├── ImportPanel.tsx
│   │   │   ├── ProgressPanel.tsx
│   │   │   └── ResultsTabs.tsx
│   │   ├── hooks/useAnalysis.ts
│   │   ├── types/index.ts
│   │   └── utils/api.ts
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```
