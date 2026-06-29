# 🚀 Redrob Candidate Ranker

> **Intelligent Candidate Discovery & Ranking System**  
> An automated, multi-signal candidate screening engine designed to evaluate, filter, and rank resume profiles against a Senior AI Engineer job description. Built with a local-first CPU scoring pipeline and an optional LLM enrichment layer.

---

## 📌 Table of Contents
- [Core Overview](#-core-overview)
- [System Architecture](#%EF%B8%8F-system-architecture)
- [Multi-Signal Scoring Pipeline](#-multi-signal-scoring-pipeline)
- [Honeypots & Hard Disqualifiers](#-honeypots--hard-disqualifiers)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
  - [Prerequisites](#prerequisites)
  - [Run via CLI](#1-run-via-cli)
  - [Run API Backend](#2-run-api-backend-locally)
  - [Run Frontend](#3-run-frontend-locally)
  - [Run with Docker Compose](#4-run-with-docker-compose)
- [API Documentation](#-api-documentation)
- [Input Data Schema](#-input-data-schema)

---

## 🔍 Core Overview

The **Redrob Candidate Ranker** solves the problem of high-volume candidate screening by combining deterministic heuristics with optional AI-driven reasoning. It is designed to work in constraints where network calls are prohibited during core ranking, running a high-speed local CPU-based evaluation first, and only applying LLM analysis to top-tier candidates if API keys are provided.

### Key Capabilities
*   **Fast CLI Processing:** Process and rank thousands of candidates from `.jsonl` or `.jsonl.gz` formats in seconds.
*   **Interactive Web UI:** Upload candidate files, visualize rankings, inspect detailed score breakdowns, and export shortlisted results.
*   **Anti-Gaming / Fraud Detection:** Built-in "Honeypot" and keyword-stuffing triggers to automatically weed out synthetic or fake profiles.
*   **Multi-Signal Evaluation:** Balanced scoring that factors in technical skills, career progression, behavioral platform signals, and logistics fit.

---

## ⚙️ System Architecture

```mermaid
graph TD
    A[Input Candidate Profiles] --> B[Schema Validation]
    B --> C[Disqualification & Honeypot Check]
    C -- Disqualified --> D[Score = 0.0]
    C -- Validated --> E[Heuristic Scoring Engine]
    E --> F1[Skill Match Score 30%]
    E --> F2[Career Quality Score 25%]
    E --> F3[Behavioral Score 25%]
    E --> F4[Availability Score 20%]
    F1 & F2 & F3 & F4 --> G[Composite Weighted Score]
    G --> H[Sort & Filter Top K]
    H --> I[Optional: LLM Enrichment Layer]
    I --> J[Final Rank Results & CSV Export]
