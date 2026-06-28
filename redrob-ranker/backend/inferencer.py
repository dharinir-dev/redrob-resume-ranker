"""Skill inference from profiles — local heuristics with optional LLM enrichment."""

from __future__ import annotations

import os
import re
from typing import Any

from disqualifier import CONSULTING_COMPANIES

PROFICIENCY_WEIGHT = {"beginner": 0.25, "intermediate": 0.55, "advanced": 0.8, "expert": 1.0}

MUST_HAVE_SKILLS = [
    "embeddings", "embedding", "sentence-transformers", "sentence transformers",
    "vector database", "vector db", "pinecone", "weaviate", "qdrant", "milvus",
    "faiss", "opensearch", "elasticsearch", "retrieval", "semantic search",
    "ranking", "information retrieval", "hybrid search",
    "evaluation framework", "ndcg", "mrr", "map", "a/b testing", "ab testing",
    "python",
]

NICE_TO_HAVE_SKILLS = [
    "lora", "qlora", "peft", "fine-tuning", "fine tuning", "finetuning",
    "learning to rank", "ltr", "xgboost",
    "distributed systems", "large-scale inference",
    "open source", "github",
    "recommendation system", "search", "nlp", "llm", "rag",
]

DISQUALIFYING_SKILL_CONTEXTS = [
    "computer vision only", "speech recognition only", "robotics",
    "image classification", "object detection",
]

NLP_IR_SKILLS = [
    "nlp", "llm", "rag", "retrieval", "information retrieval", "search",
    "ranking", "semantic search", "hybrid search", "embedding", "embeddings",
    "transformer", "language model",
]

# Non-overlapping must-have groups for coverage scoring (0–10)
MUST_HAVE_GROUPS: list[tuple[str, list[str]]] = [
    ("embeddings", ["embeddings", "embedding", "sentence-transformers", "sentence transformers"]),
    ("vector_db", ["vector database", "vector db", "pinecone", "weaviate", "qdrant", "milvus", "faiss", "opensearch", "elasticsearch"]),
    ("retrieval", ["retrieval", "semantic search", "information retrieval", "hybrid search"]),
    ("ranking_eval", ["ranking", "evaluation framework", "ndcg", "mrr", "map", "a/b testing", "ab testing"]),
    ("python", ["python"]),
]

MUST_HAVE_GROUP_LABELS = {
    "embeddings": "Production embeddings / sentence-transformers",
    "vector_db": "Vector database or hybrid search infrastructure",
    "retrieval": "Retrieval / semantic search / information retrieval",
    "ranking_eval": "Ranking systems and evaluation (NDCG, MRR, MAP)",
    "python": "Strong Python production experience",
}

CORE_JD_SKILLS = {
    "python": {"python"},
    "embeddings": {"embedding", "embeddings", "sentence-transformers", "sentence transformers", "bge", "e5"},
    "retrieval": {"retrieval", "information retrieval", "vector search", "semantic search", "rag", "hybrid search"},
    "vector_db": {"pinecone", "weaviate", "qdrant", "milvus", "faiss", "elasticsearch", "opensearch", "vector database"},
    "ranking": {"ranking", "learning to rank", "ltr", "recommendation", "search ranking", "ndcg", "map", "mrr"},
    "llm": {"llm", "large language model", "gpt", "transformer", "fine-tuning", "fine tuning", "lora", "qlora", "peft"},
    "ml_ops": {"mlflow", "kubeflow", "model serving", "feature store", "ml pipeline", "ml platform"},
    "evaluation": {"ndcg", "mrr", "map", "a/b test", "offline evaluation", "benchmark", "evaluation framework"},
}

IMPLIED_SKILL_PATTERNS: dict[str, list[str]] = {
    "retrieval": [
        r"\b(retrieval|search engine|recommendation system|vector search|semantic search)\b",
        r"\b(bm25|dense retrieval|hybrid search|rerank)\b",
    ],
    "embeddings": [r"\b(embedding|sentence.?transformer|vector index|similarity search)\b"],
    "ranking": [r"\b(ranking|learning to rank|recommendation|ndcg|search quality)\b"],
    "llm": [r"\b(llm|language model|fine.?tun|lora|qlora|prompt engineering)\b"],
    "python": [r"\b(python|pyspark|fastapi|django|flask)\b"],
}

RELEVANT_TITLE_KEYWORDS = {
    "ai", "ml", "machine learning", "deep learning", "nlp", "data scientist",
    "applied scientist", "research engineer", "search", "recommendation",
}

SIZE_SCORE_MAP = {
    "1-10": 9, "11-50": 9, "51-200": 8, "201-500": 8,
    "501-1000": 7, "1001-5000": 6, "5001-10000": 5, "10001+": 4,
}

SENIORITY_KEYWORDS = ["senior", "lead", "principal", "staff", "head", "director"]


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _career_text(candidate: dict[str, Any]) -> str:
    """Summary + career_history descriptions and titles."""
    profile = candidate.get("profile") or {}
    parts = [profile.get("summary", ""), profile.get("headline", "")]
    for job in candidate.get("career_history") or []:
        parts.extend([job.get("description", ""), job.get("title", "")])
    return _normalize(" ".join(parts))


def _full_profile_text(candidate: dict[str, Any]) -> str:
    """All searchable text including listed skills."""
    parts = [_career_text(candidate)]
    for skill in candidate.get("skills") or []:
        parts.append(_normalize(skill.get("name", "")))
    return " ".join(parts)


def _term_in_text(term: str, text: str) -> bool:
    return term.lower() in text


def _find_listed_skill_match(terms: list[str], candidate: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
    """Return whether any term matches the skills list and the best matching skill meta."""
    best_meta: dict[str, Any] | None = None
    matched = False
    for skill in candidate.get("skills") or []:
        name = _normalize(skill.get("name", ""))
        if any(term in name or name in term for term in terms):
            matched = True
            meta = {
                "name": skill.get("name", ""),
                "proficiency": skill.get("proficiency", "intermediate"),
                "endorsements": skill.get("endorsements", 0),
                "duration_months": skill.get("duration_months", 0),
            }
            if best_meta is None or PROFICIENCY_WEIGHT.get(meta["proficiency"], 0) > PROFICIENCY_WEIGHT.get(best_meta["proficiency"], 0):
                best_meta = meta
    return matched, best_meta


def _group_match_weight(terms: list[str], career_text: str, candidate: dict[str, Any]) -> tuple[float, str | None]:
    """
    Score one must-have group with evidence weighting:
    - Career-only match: 1.2x
    - Listed beginner + endorsements < 5: 0.5x
    - Otherwise: 1.0x (career match takes 1.2x when present)
    """
    in_career = any(_term_in_text(term, career_text) for term in terms)
    in_skills, meta = _find_listed_skill_match(terms, candidate)

    if not in_career and not in_skills:
        return 0.0, None

    weight = 1.0
    matched_label = next((t for t in terms if _term_in_text(t, career_text)), terms[0])

    if in_career:
        weight = 1.2
        matched_label = next((t for t in terms if _term_in_text(t, career_text)), matched_label)
    if in_skills and meta:
        if meta["proficiency"] == "beginner" and meta["endorsements"] < 5:
            weight = 0.5 if not in_career else 1.2
        elif in_career:
            weight = 1.2
        matched_label = meta["name"]

    return weight, matched_label


def check_disqualifying_skill_context(candidate: dict[str, Any]) -> tuple[bool, str | None]:
    """Disqualify CV/speech-primary profiles with no NLP/IR exposure."""
    cv_terms = [
        "computer vision", "speech recognition", "robotics",
        "image classification", "object detection", "speech synthesis", "tts", "asr",
    ]
    all_text = _full_profile_text(candidate)

    primary_cv = sum(
        1 for s in candidate.get("skills") or []
        if any(t in _normalize(s.get("name", "")) for t in cv_terms)
        and s.get("proficiency") in ("advanced", "expert")
    )
    has_nlp_ir = any(_term_in_text(term, all_text) for term in NLP_IR_SKILLS)

    if primary_cv >= 2 and not has_nlp_ir:
        return True, "Primary computer vision/speech skills without NLP/IR exposure"
    return False, None


def extract_skill_names(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build skill map from explicit skills list."""
    result: dict[str, dict[str, Any]] = {}
    for skill in candidate.get("skills") or []:
        name = _normalize(skill.get("name", ""))
        if name:
            result[name] = {
                "proficiency": skill.get("proficiency", "intermediate"),
                "duration_months": skill.get("duration_months", 0),
                "endorsements": skill.get("endorsements", 0),
                "source": "explicit",
            }
    return result


def infer_skills_from_text(candidate: dict[str, Any]) -> dict[str, float]:
    """Infer implied skill confidence from career history and summary."""
    parts: list[str] = []
    profile = candidate.get("profile", {})
    parts.extend([profile.get("summary", ""), profile.get("headline", "")])
    for job in candidate.get("career_history", []):
        parts.extend([job.get("description", ""), job.get("title", "")])
    for cert in candidate.get("certifications") or []:
        parts.append(cert.get("name", ""))

    text = " ".join(parts).lower()
    inferred: dict[str, float] = {}

    for category, patterns in IMPLIED_SKILL_PATTERNS.items():
        hits = 0
        for pattern in patterns:
            hits += len(re.findall(pattern, text, re.IGNORECASE))
        if hits:
            inferred[category] = min(1.0, 0.3 + hits * 0.15)

    return inferred


def score_skill_match(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Must-have coverage 0–10 plus nice-to-have bonus up to 2 points.
    Checks skills list, career_history descriptions, and summary.
    """
    career_text = _career_text(candidate)
    full_text = _full_profile_text(candidate)
    n_groups = len(MUST_HAVE_GROUPS)
    points_per_group = 10.0 / n_groups

    group_contributions: list[float] = []
    matched_skills: list[str] = []
    inferred_from_career: list[str] = []

    for group_name, terms in MUST_HAVE_GROUPS:
        weight, label = _group_match_weight(terms, career_text, candidate)
        if weight > 0:
            group_contributions.append(points_per_group * weight)
            if label:
                matched_skills.append(label)
            in_skills, _ = _find_listed_skill_match(terms, candidate)
            in_career = any(_term_in_text(t, career_text) for t in terms)
            if in_career and not in_skills and label:
                inferred_from_career.append(label)

    must_have_score = min(10.0, sum(group_contributions))

    nice_matches = sum(1 for term in NICE_TO_HAVE_SKILLS if _term_in_text(term, full_text))
    nice_bonus = min(2.0, nice_matches * 0.25)

    skill_disqualified, skill_dq_reason = check_disqualifying_skill_context(candidate)
    total = 0.0 if skill_disqualified else min(10.0, must_have_score + nice_bonus)

    return {
        "score": round(total, 2),
        "must_have_score": round(must_have_score, 2),
        "nice_to_have_bonus": round(nice_bonus, 2),
        "must_have_coverage": round(must_have_score / 10.0, 3),
        "nice_matches": nice_matches,
        "matched_skills": matched_skills,
        "inferred_from_career": inferred_from_career,
        "core_skill_count": sum(1 for g in group_contributions if g > 0),
        "skill_disqualified": skill_disqualified,
        "skill_disqualify_reason": skill_dq_reason,
        "composite": total / 10.0,
        "category_scores": {},
        "inferred": infer_skills_from_text(candidate),
    }


def score_core_skills(candidate: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible wrapper — delegates to score_skill_match."""
    return score_skill_match(candidate)


def score_title_relevance(candidate: dict[str, Any]) -> float:
    """Score how relevant the candidate's title/career is to the AI Engineer role."""
    profile = candidate.get("profile", {})
    title = _normalize(profile.get("current_title", ""))
    headline = _normalize(profile.get("headline", ""))

    score = 0.0
    combined = f"{title} {headline}"

    for kw in RELEVANT_TITLE_KEYWORDS:
        if kw in combined:
            score = max(score, 0.7 if kw in title else 0.5)

    strong_titles = ("ai engineer", "ml engineer", "machine learning", "applied scientist", "nlp engineer")
    for st in strong_titles:
        if st in title:
            score = max(score, 0.95)

    production_keywords = ("production", "shipped", "deployed", "platform", "serving", "pipeline")
    text = _normalize(profile.get("summary", ""))
    for job in candidate.get("career_history", []):
        text += " " + _normalize(job.get("description", ""))

    if score >= 0.5 and any(pk in text for pk in production_keywords):
        score = min(1.0, score + 0.1)

    return score


def score_career_quality(candidate: dict[str, Any]) -> float:
    """Career quality score 0–10 (weighted composite)."""
    return score_career_quality_detailed(candidate)["score"]


def score_career_quality_detailed(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Career quality score 0–10:
    product company ratio (30%), tenure stability (20%), seniority (20%),
    company size (15%), years-of-experience band (15%).
    """
    career = candidate.get("career_history") or []
    profile = candidate.get("profile") or {}

    if not career:
        return {
            "score": 5.0,
            "product_score": 5.0,
            "tenure_score": 5.0,
            "seniority_score": 5.0,
            "size_score": 5.0,
            "yoe_score": 5.0,
            "product_ratio": 0.0,
            "avg_tenure_months": 0.0,
        }

    total_months = sum(r.get("duration_months", 0) for r in career)
    product_months = sum(
        r.get("duration_months", 0)
        for r in career
        if not any(c.lower() in (r.get("company") or "").lower() for c in CONSULTING_COMPANIES)
        and r.get("industry") not in ("IT Services", "Outsourcing", "BPO")
    )
    product_ratio = product_months / max(total_months, 1)
    product_score = product_ratio * 10

    avg_tenure = total_months / len(career)
    if avg_tenure < 12:
        tenure_score = 2
    elif avg_tenure < 18:
        tenure_score = 5
    elif avg_tenure < 24:
        tenure_score = 7
    else:
        tenure_score = 10

    current_title = _normalize(profile.get("current_title", ""))
    seniority_score = 8 if any(kw in current_title for kw in SENIORITY_KEYWORDS) else 5

    company_size = profile.get("current_company_size", "")
    size_score = SIZE_SCORE_MAP.get(company_size, 5)

    yoe = profile.get("years_of_experience", 0)
    if 5 <= yoe <= 9:
        yoe_score = 10
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        yoe_score = 8
    elif 3 <= yoe < 4 or 11 < yoe <= 13:
        yoe_score = 5
    else:
        yoe_score = 3

    composite = round(
        product_score * 0.30
        + tenure_score * 0.20
        + seniority_score * 0.20
        + size_score * 0.15
        + yoe_score * 0.15,
        2,
    )

    return {
        "score": composite,
        "product_score": round(product_score, 2),
        "tenure_score": tenure_score,
        "seniority_score": seniority_score,
        "size_score": size_score,
        "yoe_score": yoe_score,
        "product_ratio": round(product_ratio, 3),
        "avg_tenure_months": round(avg_tenure, 1),
    }


def score_education(candidate: dict[str, Any]) -> float:
    """Score education relevance — CS/ML field and institution tier."""
    tier_weights = {"tier_1": 1.0, "tier_2": 0.85, "tier_3": 0.65, "tier_4": 0.5, "unknown": 0.4}
    ml_fields = {
        "computer science", "machine learning", "artificial intelligence",
        "data science", "information technology", "software engineering",
        "electrical engineering", "statistics", "mathematics",
    }

    education = candidate.get("education") or []
    if not education:
        return 0.4

    best = 0.0
    for edu in education:
        field = _normalize(edu.get("field_of_study", ""))
        degree = _normalize(edu.get("degree", ""))
        tier = edu.get("tier", "unknown")
        tier_score = tier_weights.get(tier, 0.4)

        field_match = any(f in field for f in ml_fields)
        degree_bonus = 0.1 if any(d in degree for d in ("m.tech", "m.s", "ms", "m.e", "phd", "b.e", "b.tech", "b.s")) else 0.0
        field_bonus = 0.15 if field_match else 0.0

        entry_score = min(1.0, tier_score * 0.7 + field_bonus + degree_bonus)
        best = max(best, entry_score)

    cert_bonus = 0.0
    ai_cert_keywords = ("aws", "google cloud", "azure", "deeplearning", "machine learning", "tensorflow", "pytorch")
    for cert in candidate.get("certifications") or []:
        name = _normalize(cert.get("name", ""))
        if any(k in name for k in ai_cert_keywords):
            cert_bonus = max(cert_bonus, 0.08)

    return min(1.0, best + cert_bonus)


def score_experience_fit(candidate: dict[str, Any]) -> float:
    """Score years of experience against 5-9 year ideal band."""
    years = candidate.get("profile", {}).get("years_of_experience", 0)
    if 5 <= years <= 9:
        return 1.0
    if 4 <= years < 5 or 9 < years <= 11:
        return 0.75
    if 3 <= years < 4 or 11 < years <= 13:
        return 0.5
    return 0.25


def score_location(candidate: dict[str, Any]) -> float:
    """Score location fit for Pune/Noida hybrid role."""
    location = _normalize(candidate.get("profile", {}).get("location", ""))
    country = _normalize(candidate.get("profile", {}).get("country", ""))
    signals = candidate.get("redrob_signals") or {}

    tier1_cities = ("pune", "noida", "delhi", "gurgaon", "gurugram", "mumbai", "hyderabad", "bangalore", "bengaluru")
    if country and country not in ("india", "in"):
        return 0.3

    if any(c in location for c in tier1_cities):
        return 1.0
    if signals.get("willing_to_relocate"):
        return 0.75
    return 0.4


async def enrich_top_candidates_with_llm(
    candidates: list[dict[str, Any]],
    job_description: str,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Backward-compatible wrapper."""
    results = await batch_llm_inference(candidates, job_description, api_key)
    return [r["candidate"] for r in results]


INFERENCE_PROMPT = """
You are an expert technical recruiter evaluating a candidate for a Senior AI Engineer role at a Series A startup.

The role requires: production embeddings/retrieval systems, vector databases, ranking evaluation frameworks, Python, and a product-company mindset.

Candidate profile:
Career history descriptions: {career_descriptions}
Skills listed: {skills_list}

Your task:
1. Extract EVIDENCE: specific, concrete, measurable achievements (not generic claims)
2. Infer HIDDEN SKILLS: what technical competencies can be inferred from their work even if not explicitly listed?
3. Identify KEY GAPS: what required skills have no evidence?
4. Write a 2-sentence RECRUITER RATIONALE explaining why this candidate should or should not be interviewed

Return ONLY valid JSON:
{{
  "evidence": ["specific achievement 1", "specific achievement 2"],
  "inferred_skills": ["inferred skill 1", "inferred skill 2"],
  "key_gaps": ["gap 1", "gap 2"],
  "rationale": "2-sentence explanation",
  "inference_confidence": 0.0
}}
"""


def _local_inference_fallback(candidate: dict[str, Any]) -> dict[str, Any]:
    """Heuristic inference when no LLM API key is available."""
    career_parts = []
    for job in candidate.get("career_history") or []:
        career_parts.append(job.get("description", ""))
    career_text = " ".join(career_parts)
    skills_list = [s.get("name", "") for s in candidate.get("skills") or []]
    inferred = infer_skills_from_text(candidate)
    evidence: list[str] = []
    for sent in re.split(r"(?<=[.!?])\s+", career_text):
        if len(sent) > 30 and any(k in sent.lower() for k in ("production", "deploy", "built", "shipped", "scale")):
            evidence.append(sent.strip()[:200])
        if len(evidence) >= 2:
            break
    return {
        "evidence": evidence or [candidate.get("profile", {}).get("summary", "")[:200]],
        "inferred_skills": [INFERRED_SKILL_LABELS.get(k, k) for k, v in inferred.items() if v >= 0.5][:4],
        "key_gaps": [],
        "rationale": f"{candidate.get('profile', {}).get('current_title', 'Candidate')} — local scoring only (no LLM key). Skills: {', '.join(skills_list[:5])}.",
        "inference_confidence": 0.5,
    }


INFERRED_SKILL_LABELS = {
    "retrieval": "Retrieval / search systems",
    "embeddings": "Embeddings / vector search",
    "ranking": "Ranking / recommendation",
    "llm": "LLM / fine-tuning",
    "python": "Python engineering",
}


async def run_llm_inference(
    candidate: dict[str, Any],
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run LLM inference on a single candidate; falls back to heuristics."""
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _local_inference_fallback(candidate)

    career_descriptions = "\n".join(
        f"- {j.get('title', '')} at {j.get('company', '')}: {j.get('description', '')[:400]}"
        for j in candidate.get("career_history") or []
    )
    skills_list = ", ".join(
        f"{s.get('name')} ({s.get('proficiency', '')})" for s in candidate.get("skills") or []
    )
    prompt = INFERENCE_PROMPT.format(
        career_descriptions=career_descriptions[:3000],
        skills_list=skills_list[:1500],
    )

    try:
        if os.environ.get("OPENAI_API_KEY") or (key and not os.environ.get("ANTHROPIC_API_KEY")):
            import httpx
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 400,
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
        else:
            import httpx
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 400,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                text = resp.json()["content"][0]["text"]

        import json as json_mod
        data = json_mod.loads(text.strip().strip("`").removeprefix("json"))
        data["inference_confidence"] = float(data.get("inference_confidence", 0.5))
        return data
    except Exception:
        return _local_inference_fallback(candidate)


async def batch_llm_inference(
    scored_items: list[dict[str, Any]],
    job_description: str = "",
    api_key: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Run LLM inference on top-N scored items and apply 10% confidence modifier."""
    import asyncio

    subset = scored_items[:limit]
    results: list[dict[str, Any]] = []

    for item in subset:
        candidate = item["candidate"]
        inference = await run_llm_inference(candidate, api_key)
        base = item["score_result"]["total_score"]
        confidence = float(inference.get("inference_confidence", 0.5))
        adjusted = round(base * (0.9 + 0.1 * confidence), 2)

        sr = dict(item["score_result"])
        sr["total_score"] = adjusted
        sr["llm_evidence"] = inference.get("evidence", [])
        sr["llm_inferred_skills"] = inference.get("inferred_skills", [])
        sr["key_gaps"] = inference.get("key_gaps", [])
        sr["recruiter_rationale"] = inference.get("rationale", "")
        sr["inference_confidence"] = confidence
        if inference.get("inferred_skills"):
            sr["inferred_skills"] = list(dict.fromkeys(
                sr.get("inferred_skills", []) + inference["inferred_skills"]
            ))
        if inference.get("evidence"):
            sr["evidence_trail"] = inference["evidence"][:6]

        results.append({
            **item,
            "score": round(adjusted / 10.0, 6),
            "score_result": sr,
            "reasoning": inference.get("rationale", ""),
        })
        await asyncio.sleep(0)  # yield for async fairness

    results.extend(scored_items[limit:])
    return results


async def _llm_summarize_fit(
    candidate: dict[str, Any],
    job_description: str,
    api_key: str,
    provider: str,
) -> str:
    profile = candidate.get("profile", {})
    prompt = (
        f"Job: Senior AI Engineer\n\n"
        f"Candidate: {profile.get('current_title')} with {profile.get('years_of_experience')} years\n"
        f"Summary: {profile.get('summary', '')[:500]}\n\n"
        f"In 1-2 sentences, explain fit for this role using ONLY facts from the profile. "
        f"Mention any concerns honestly.\n\nJD excerpt:\n{job_description[:800]}"
    )

    if provider == "openai":
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
