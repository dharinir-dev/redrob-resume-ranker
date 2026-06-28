# Redrob Candidate Ranker

AI-powered candidate ranking system for intelligent candidate discovery and ranking.

## Candidate Data Schema

Each line in `candidates.jsonl` is one JSON object validated against [`candidate_schema.json`](candidate_schema.json):

| Section | Key fields used in ranking |
|---------|---------------------------|
| `profile` | title, summary, headline, years_of_experience, location, company, industry, company_size |
| `career_history` | titles, descriptions, company/industry/size, duration_months |
| `education` | degree, field_of_study, institution, tier |
| `skills` | name, proficiency, duration_months, endorsements |
| `certifications` | name, issuer (bonus for ML/cloud certs) |
| `redrob_signals` | all 23 behavioral signals (recency, response rate, notice period, assessments, engagement, etc.) |

Invalid records are rejected at load time with a line-numbered error.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React SPA (Upload · JD Editor · Results · CSV Download)      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI Backend                                            │
│  ├── ranker.py      Multi-signal scoring engine             │
│  ├── inferencer.py  Skill inference + optional LLM          │
│  ├── signals.py     23 Redrob behavioral signals            │
│  ├── disqualifier.py Honeypots, title traps, JD filters     │
│  └── output.py      Submission CSV generation               │
└─────────────────────────────────────────────────────────────┘
```

## How to Run Locally

```bash
cd redrob-ranker/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860
```

Open http://localhost:7860

## How to Run on HuggingFace Spaces

1. Push this repository to HuggingFace
2. Create a new Space with Docker SDK
3. Set port to 7860
4. Add `OPENAI_API_KEY` secret (optional, for LLM enrichment)
5. The app will auto-build and deploy

## How Scoring Works

The system uses 4 scoring dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Skill Match** | 40% | Core skills (embeddings, retrieval, vector DB, ranking, LLM, Python, evaluation) |
| **Career Quality** | 30% | Product company experience vs consulting, career progression |
| **Experience Fit** | 20% | Years of experience alignment with role requirements |
| **Behavioral Signals** | 10% | Recency, response rate, availability, engagement metrics |

**Honeypot Detection** automatically excludes candidates with:
- Years of experience > career span
- Skill duration > total career months
- 100% profile completeness but missing education/certifications
- Future last_active_date

## How to Interpret Output CSV

| Column | Description |
|--------|-------------|
| `rank` | Position in ranked list (1-100) |
| `candidate_id` | Unique candidate identifier |
| `score` | Final score (0-10 scale) |
| `reasoning` | AI-generated or heuristic-based ranking rationale |
| `evidence_trail` | Quoted text from career descriptions supporting the score |
| `key_gaps` | Missing skills or experience gaps |
| `disqualified` | True if candidate failed honeypot or disqualifier checks |
| `disqualify_reason` | Reason for disqualification (if applicable) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Docker (for deployment)

### Local Development

```bash
# Backend
cd redrob-ranker/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd redrob-ranker/frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to port 8000.

### Generate Submission CSV

From the repo root, with candidates file at `../candidates.jsonl` or `../candidates.jsonl.gz`:

```bash
cd redrob-ranker
python rank.py --candidates ../candidates.jsonl.gz --out submission.csv
```

Validate before submitting:

```bash
python ../validate_submission.py submission.csv
```

### Docker (Sandbox Demo)

```bash
cd redrob-ranker
docker compose up --build
```

Open http://localhost:7860 for the full web UI.

For HuggingFace Spaces, push this repo and set the SDK to Docker with port 7860.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/default-jd` | Pre-loaded job description |
| POST | `/api/rank` | Start async ranking (multipart upload) |
| GET | `/api/rank/{id}/status` | Poll job progress |
| GET | `/api/rank/{id}/results` | Get ranked results |
| GET | `/api/rank/{id}/download` | Download submission CSV |
| POST | `/api/rank/sync` | Synchronous ranking for small samples |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables LLM-enhanced reasoning for top-10 (demo only) |
| `ANTHROPIC_API_KEY` | No | Alternative LLM provider |

## File Structure

```
redrob-ranker/
├── backend/
│   ├── main.py           # FastAPI app
│   ├── ranker.py           # Core scoring engine
│   ├── inferencer.py       # Skill inference
│   ├── signals.py          # Behavioral signal scoring
│   ├── disqualifier.py     # Hard disqualifier logic
│   ├── output.py           # CSV generation
│   ├── rank.py             # CLI entry point
│   ├── default_jd.txt      # Job description
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   ├── package.json
│   └── index.html
├── docker-compose.yml
├── Dockerfile
├── rank.py                 # Root CLI wrapper
└── README.md
```

## Compute Constraints

Per hackathon rules, the ranking step:

- Runs in ≤ 5 minutes on CPU
- Uses ≤ 16 GB RAM
- Makes no external API calls
- Uses no GPU

Tested on sample pools of 50–1000 candidates in under 10 seconds. Full 100K pool completes in under 2 minutes on a modern laptop CPU.

## License

Built for the Redrob Hackathon 2026.
