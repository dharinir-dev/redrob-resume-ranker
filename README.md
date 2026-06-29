# AI Candidate Ranking System

An offline-first AI-powered candidate ranking system that ranks resumes against a job description using deterministic scoring with optional LLM enrichment.

---

# Architecture

```text
                  +----------------------+
                  |   React (Vite UI)    |
                  | Upload / Demo Mode   |
                  +----------+-----------+
                             |
                        REST API
                             |
                             v
                  +----------------------+
                  | FastAPI Backend      |
                  |      main.py         |
                  +----------+-----------+
                             |
                   Calls pure functions
                             |
                             v
                  +----------------------+
                  |      ranker.py       |
                  |----------------------|
                  | Resume Parsing       |
                  | Skill Matching       |
                  | Experience Scoring   |
                  | Education Scoring    |
                  | Career Progression   |
                  | Evidence Extraction  |
                  | Final Ranking        |
                  +----------+-----------+
                             |
                  Optional LLM Enrichment
                  (OPENAI_API_KEY exists)
                             |
                             v
                        OpenAI API
                             |
                             v
                     Ranked Candidates
                             |
                             v
                     Download CSV
```

---

## Clone the Repository

```bash
git clone https://github.com/<your-username>/redrob-resume-ranker.git
cd redrob-ranker
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend will be available at:

```
http://127.0.0.1:8000
```

## Frontend Setup

Open a new terminal:

```bash
cd redrob-ranker/frontend
npm install
npm run dev
```

The frontend will be available at:

```
http://localhost:5173
```

Open your browser:

```
http://localhost:8000
```

---

# Run on Hugging Face Spaces

1. Create a **Docker Space** on Hugging Face.
2. Upload the repository.
3. (Optional) Add a secret:

```
OPENAI_API_KEY=<your_api_key>
```

4. The application builds automatically.
5. Launch the Space.

If no API key is provided, the application runs completely offline using deterministic scoring.

---

# Scoring Method

Each candidate receives a score out of **100**.

| Dimension | Weight |
|-----------|--------|
| Skills Match | 40% |
| Experience | 30% |
| Education | 15% |
| Career Progression | 15% |

Final score:

```text
Final Score =
0.40 × Skill Score +
0.30 × Experience Score +
0.15 × Education Score +
0.15 × Career Progression Score
```

When `OPENAI_API_KEY` is available, an optional LLM step generates richer explanations without changing the deterministic scoring.

---

# Output CSV

The generated CSV contains one row per candidate.

| Column | Description |
|---------|-------------|
| rank | Candidate rank |
| candidate_id | Unique candidate ID |
| name | Candidate name |
| final_score | Overall score (0–100) |
| skill_score | Skill matching score |
| experience_score | Experience score |
| education_score | Education score |
| progression_score | Career progression score |
| evidence_trail | Direct quotes extracted from resume/career descriptions |
| llm_summary | Optional LLM explanation (blank in offline mode) |

Candidates are sorted in descending order of `final_score`.

---

# Features

- ✅ Offline-first ranking engine
- ✅ Optional OpenAI LLM enrichment
- ✅ Pure scoring logic in `backend/ranker.py`
- ✅ FastAPI backend
- ✅ React + Vite frontend
- ✅ Demo mode (50 candidates)
- ✅ Full dataset support (100,000 candidates)
- ✅ Download ranked CSV
- ✅ Evidence trail extracted from actual candidate text

---

# Demo Mode

The application includes a bundled `sample_candidates.json` containing **50 candidates**.

UI Banner:

```
Running in DEMO MODE (50 candidates)
```

After loading the full dataset:

```
Full dataset loaded (100,000 candidates)
```

---

# Project Structure

```text
candidate-ranking-system/
│
├── backend/
│   ├── main.py
│   ├── ranker.py
│   ├── sample_candidates.json
│   └── utils.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── dist/
│
├── outputs/
│   └── ranked_candidates.csv
│
├── requirements.txt
├── package.json
├── Dockerfile
└── README.md
```

---

# Implementation Notes

- Works without internet access during execution.
- LLM enrichment is optional and only enabled when `OPENAI_API_KEY` is configured.
- `sample_candidates.json` is bundled for demo mode.
- All ranking logic is implemented as pure functions in `backend/ranker.py`.
- `evidence_trail` contains direct quoted text extracted from candidate career descriptions using regex/substring matching.
- The frontend is built using Vite + React. Run `npm run build` to generate `frontend/dist/`, which is served by FastAPI.
