# App Store Review Analyzer

AI-powered iOS App Store review analysis tool. Collects reviews, discovers topics, generates evidence-grounded findings, produces a PRD with version planning, and creates traceable test cases — all through a web UI.

## Features

- **Review Collection**: Extracts review data embedded in the App Store product page HTML
- **Data Cleaning**: Exact + fuzzy deduplication, quality flagging, language detection
- **AI Topic Discovery**: LLM-powered dynamic topic clustering (no fixed keyword maps)
- **Evidence-Grounded Findings**: Every finding includes source reviews, confidence scores, conflicting evidence, and uncertainty notes
- **PRD Generation**: Multi-version product plan with traceable requirements, assumptions explicitly marked
- **Test Case Generation**: Executable test cases linked to requirements and source reviews
- **Traceability Validation**: Deterministic chain verification from reviews → findings → requirements → test cases
- **Data Import**: Supports JSON and CSV review datasets for offline analysis
- **Bilingual UI**: Chinese/English toggle for interface and AI-generated content

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SSE streaming |
| AI/LLM | OpenAI-compatible API with structured outputs |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Data | App Store product page HTML extraction |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI-compatible API key (DeepSeek, OpenAI, or any compatible provider)

### 1. Backend Setup

```bash
git clone https://github.com/windyJiao/app-review-insights.git
cd app-review-insights/backend

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY, BASE_URL, and MODEL
```

### 2. Frontend Setup

```bash
cd ../frontend
npm install
```

### 3. Run

Terminal 1 — Backend:
```bash
cd backend
python -m app.main
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## Usage

### Analyze from App Store

1. Enter an App Store URL (default: workout-for-women-home-gym)
2. Optionally set an analysis goal (e.g., "focus on subscription conversion")
3. Click **Start Analysis**
4. Watch real-time progress through the 7-stage pipeline
5. Browse results across 7 tabs: Overview, Reviews, Topics, Insights, PRD, Test Cases, Traceability

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

## Data Collection Method

Reviews are collected by fetching the App Store product page and extracting embedded JSON review data from the page HTML. Apple embeds review objects (`{"$kind":"Review",...}`) in the server-rendered page for SEO and initial display.

**Why this approach:**
- Apple's iTunes RSS feed no longer returns review data (endpoint deprecated)
- Third-party libraries (`app_store_scraper`) rely on private APIs that have changed
- Direct HTML extraction uses only publicly accessible page content

**Limitations:**
- Only the first ~8-10 reviews are embedded in the initial page load; additional reviews load via XHR and require browser automation
- Page structure may change with Apple updates
- US storefront data is prioritized per assessment requirements; other storefronts may return different results
- Use with reasonable rate limits — avoid excessive requests

**Network considerations:**
- The collector requests the product page (`apps.apple.com/{country}/app/id{id}`) with a standard browser User-Agent header
- No authentication or scraping of authenticated content
- Data is sourced from the App Store's public web presence

## Architecture

```
App Store product page HTML
    │
    ▼
[Collect] ─── Regex extract {"$kind":"Review",...} JSON objects
    │
    ▼
[Clean] ───── MD5 exact dedup + n-gram fuzzy similarity + quality heuristics
    │
    ▼
[Classify] ── LLM topic discovery (batch reviews → topics → merge overlaps)  ← AI
    │
    ▼
[Analyze] ─── LLM findings with evidence grounding, confidence scoring        ← AI
    │
    ▼
[PRD] ─────── LLM version planning + requirements, assumptions marked         ← AI
    │
    ▼
[Tests] ───── LLM test case generation linked to requirements & reviews       ← AI
    │
    ▼
[Validate] ── Deterministic traceability check: review→finding→req→test
```

## Design Decisions: Rules vs AI

| Stage | Method | Rationale |
|-------|--------|-----------|
| Collection | **Deterministic** | String pattern matching on public HTML is well-defined |
| Cleaning/Dedup | **Deterministic** | Exact solutions exist (MD5 hashing, n-gram Jaccard similarity) |
| Topic Discovery | **LLM** | Topics vary by app category; need semantic understanding, no predefined taxonomy |
| Finding Analysis | **LLM** | Requires evidence synthesis, confidence assessment, contradiction detection across reviews |
| PRD Generation | **LLM** | Strategic scope planning requires reasoning about dependencies, priorities, and user impact |
| Test Case Gen | **LLM** | Edge-case design and test-step authoring from abstract requirements need domain knowledge |
| Validation | **Deterministic** | Checking whether review IDs exist in the dataset is a mechanical reference check |

## Model & Provider

This application uses **OpenAI-compatible APIs** with **structured output** (function calling / tool use with JSON Schema) for all LLM tasks. The default configuration targets **DeepSeek** (`deepseek-chat`), but any compatible provider works.

Configure via `backend/.env`:
```
OPENAI_API_KEY=your-key          # Required
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### Prompt Strategy

Each AI task uses a focused system prompt with explicit constraints:

| Task | Prompt Strategy | Key Constraints |
|------|----------------|-----------------|
| **Topic Discovery** | Product analyst role; "be thorough and specific" | Must cite review IDs; <2 reviews → merge topic |
| **Topic Merge** | Semantic dedup across batches | Target 5-15 well-defined topics |
| **Finding Analysis** | Senior product analyst; "never fabricate data" | Every finding requires supporting review IDs + excerpts |
| **PRD Generation** | Senior product manager; "mark assumptions explicitly" | <20 reviews → 1 version max, 2-4 requirements; evidence <5 → assumption |
| **Test Case Gen** | QA engineer; "traceable to user feedback" | <20 reviews → 8 tests max; every test needs linked_review_ids |

### Hallucination Reduction

1. **Structured output (JSON Schema)**: All LLM calls use function calling with strict JSON schemas — the model must conform to the requested structure rather than generating free text
2. **Source ID validation**: Post-generation, all cited review IDs are checked against the actual dataset; findings referencing non-existent reviews are removed
3. **Evidence quantity gating**: Confidence is downgraded when supporting reviews <3; findings with 0 valid reviews are automatically removed
4. **Assumption marking**: Requirements without direct review evidence are marked `is_assumption=true` with rationale
5. **Distinct labels**: Model-generated conclusions are tagged `source: "model"`; deterministic statistics are computed separately and labeled `is_model_generated: true`
6. **Output scope adapts to input**: Prompts explicitly constrain output volume based on available review count to reduce fabrication when data is scarce

### Failure Handling

- **Collection failure**: If the primary country storefront returns no reviews, the system notes the limitation in warnings and continues with available data
- **LLM call failure**: Each AI stage is wrapped in try/except; failures log the error and continue the pipeline (e.g., if classification fails, findings still run with basic topic data)
- **Empty data graceful exit**: If 0 reviews are collected or all reviews are cleaned away, the pipeline stops early with a clear message
- **SSE transport**: Streaming events use manual formatting to avoid library compatibility issues

## Sample Data

For offline review, cached review data and analysis results are available in `sample_output/`. See [sample_output/README.md](sample_output/README.md) for details.

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
│   │   │   ├── collector.py        # HTML review extractor
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
│   │   ├── i18n/
│   │   │   ├── LanguageContext.tsx
│   │   │   └── translations.ts
│   │   ├── types/index.ts
│   │   └── utils/api.ts
│   ├── package.json
│   └── vite.config.ts
├── sample_output/                  # Cached data for offline review
├── .gitignore
└── README.md
```
