# 🚀 Redrob Resume Ranker

<div align="center">

# AI-Powered Candidate Ranking & Explainable Hiring Platform

**Built for the Redrob AI Hiring Hackathon**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge\&logo=react\&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge\&logo=vite\&logoColor=white)

### Intelligent, Explainable Resume Ranking using Deterministic AI + Semantic Analysis

*A transparent hiring assistant that ranks candidates against a Job Description using multi-signal scoring, evidence extraction, and optional LLM-generated recruiter insights.*

</div>

---

# 📖 Overview

Recruiters often spend hours manually screening resumes, while traditional ATS systems rely heavily on keyword matching and provide little explanation for ranking decisions.

**Redrob Resume Ranker** solves this by combining deterministic scoring, semantic resume understanding, and explainable AI. Instead of simply matching keywords, the system evaluates multiple candidate signals, extracts supporting evidence, and generates transparent recruiter-friendly reasoning.

The ranking engine remains fully reproducible while optionally enhancing recruiter insights with an LLM.

---

# ✨ Features

* 📄 Upload candidate datasets (JSON)
* 📝 Upload or edit Job Descriptions
* ⚡ FastAPI REST backend
* 💻 React + Vite frontend
* 🧠 Deterministic multi-signal ranking engine
* 🔍 Semantic skill inference
* 🚫 Rule-based disqualification
* 🛡️ Honeypot & profile validation
* 📊 Explainable recruiter reasoning
* 📥 CSV export
* 🤖 Optional AI-generated summaries

---

# 🏗️ Architecture

```text
                   React + Vite Frontend
          Upload Candidates & Job Description
                         │
                    REST API Requests
                         │
                         ▼
                FastAPI Backend (main.py)
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
 Resume Parsing                  Schema Validation
        │                                 │
        ▼                                 ▼
 Skill Extraction             Candidate Validation
        │                                 │
        └───────────────┬─────────────────┘
                        ▼
              Multi-Signal Ranking Engine
                        │
       ┌────────────────┼────────────────┐
       │                │                │
       ▼                ▼                ▼
 Skill Score     Experience Score   Rule Engine
                        │
                        ▼
             Final Weighted Candidate Score
                        │
                        ▼
          Evidence + Recruiter Reasoning
                        │
                        ▼
              Ranked Results + CSV Export
```

---

# 🎯 Ranking Methodology

Each candidate receives a deterministic score based on multiple evaluation signals.

| Dimension                         | Weight  |
| --------------------------------- | ------- |
| Skill Match                       | **40%** |
| Experience Relevance              | **30%** |
| Resume Quality & Evidence         | **20%** |
| Profile Validation & Availability | **10%** |

Final Score:

```
Final Score =
0.40 × Skill Match
+ 0.30 × Experience
+ 0.20 × Resume Evidence
+ 0.10 × Profile Quality
```

Candidates are then ranked in descending order.

---

# 🔍 Ranking Pipeline

### 1. Candidate Validation

* Schema validation
* Required fields verification
* Data normalization

---

### 2. Resume Understanding

The engine extracts:

* Technical skills
* Career history
* Experience
* Education
* Resume summaries

---

### 3. Skill Matching

Skills are identified using:

* Explicit skills
* Resume summaries
* Project descriptions
* Career history

---

### 4. Rule-Based Screening

Automatically detects:

* Non-relevant profiles
* Keyword stuffing
* Timeline inconsistencies
* Suspicious resumes
* Honeypot responses

---

### 5. Multi-Signal Scoring

The final score combines:

* Skill relevance
* Experience
* Career progression
* Resume evidence
* Behavioral indicators
* Availability

---

### 6. Explainability

Every candidate receives:

* Score breakdown
* Supporting evidence
* Recruiter-friendly explanation
* Strengths
* Missing requirements

---

### 7. Optional AI Enrichment

If an OpenAI API key is configured, the application generates concise recruiter summaries while preserving deterministic ranking.

---

# 📂 Project Structure

```text
redrob-ranker/
│
├── backend/
│   ├── main.py
│   ├── ranker.py
│   ├── inferencer.py
│   ├── disqualifier.py
│   ├── signals.py
│   ├── schema.py
│   ├── output.py
│   ├── rank.py
│   ├── requirements.txt
│   ├── runtime.txt
│   └── static/
│
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
│
├── candidate_schema.json
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

# 🚀 Run Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend:

```
http://127.0.0.1:8000
```

API Documentation:

```
http://127.0.0.1:8000/docs
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# ☁️ Deploy on HuggingFace Spaces

1. Create a new **Docker Space**.
2. Upload the repository.
3. Ensure `Dockerfile` and `requirements.txt` are included.
4. Add any required environment variables (e.g., `OPENAI_API_KEY`) if AI summaries are enabled.
5. Deploy the Space.

---

# 📊 Output CSV

The application exports ranked candidates in CSV format.

| Column       | Description                   |
| ------------ | ----------------------------- |
| candidate_id | Candidate identifier          |
| rank         | Candidate rank                |
| score        | Final weighted score          |
| reasoning    | Explainable recruiter summary |

---

# 🛡️ Explainability

Unlike traditional ATS systems, every ranking is backed by transparent evidence.

The system explains:

* Why a candidate ranked highly
* Matching skills
* Relevant experience
* Resume evidence
* Validation checks
* Missing requirements

This enables recruiters to trust and verify every recommendation.

---

# ⚙️ Tech Stack

### Backend

* Python 3.11
* FastAPI
* Uvicorn
* Pydantic
* HTTPX

### Frontend

* React
* Vite
* JavaScript
* Tailwind CSS

---

# 🌐 Deployment

Deploy the backend on Render.

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Root Directory**

```
backend
```

---

# 🐳 Docker Support

Docker configuration files are included for containerized deployment.

```bash
docker-compose up --build
```

---

# 📸 Screenshots

Add screenshots before submission.

* 🏠 Home Page
* 📄 Candidate Upload
* 📝 Job Description Editor
* 📊 Ranked Candidates
* 👤 Candidate Details
* 📥 CSV Export

---

# 🚀 Future Improvements

* Semantic vector search
* Batch resume processing
* Recruiter analytics dashboard
* Multi-job comparison
* Resume PDF parsing
* AI interview question generation
* Cloud-native deployment
* Candidate recommendation engine

---

# 👩‍💻 Authors

**Dharini R ,**
**Divya Dharshni V**

Developed for the **Redrob AI Hiring Hackathon**.

---

<div align="center">

⭐ If you found this project helpful, consider giving the repository a star!

</div>
