"""Core multi-signal scoring engine — CPU-only, no network during ranking."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path
from typing import Any, Callable

from disqualifier import check_disqualifiers
from inferencer import (
    CORE_JD_SKILLS,
    MUST_HAVE_GROUP_LABELS,
    MUST_HAVE_GROUPS,
    _career_text,
    _find_listed_skill_match,
    extract_skill_names,
    infer_skills_from_text,
    score_career_quality_detailed,
    score_skill_match,
)
from schema import build_candidate_document, validate_candidate
from signals import (
    compute_final_score,
    score_availability,
    score_behavioral,
    score_behavioral_detailed,
)

ProgressCallback = Callable[[float, str], None] | None

JD_KEYWORDS = {
    "embedding", "retrieval", "ranking", "vector", "llm", "python", "ndcg",
    "search", "recommendation", "fine-tuning", "rag", "production", "ml",
    "nlp", "transformer", "evaluation", "hybrid", "semantic", "pinecone",
    "faiss", "elasticsearch", "sentence-transformer", "learning to rank",
    "mrr", "map", "weaviate", "qdrant", "milvus", "lora", "peft",
}

JD_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "embeddings_retrieval": {
        "label": "Production embeddings-based retrieval systems",
        "skill_categories": ("embeddings", "retrieval"),
        "infer_patterns": [r"\b(embedding|retrieval|vector search|semantic search|rag)\b"],
        "shift_terms": {"search", "nlp", "recommendation", "similarity"},
    },
    "vector_db": {
        "label": "Vector databases or hybrid search infrastructure",
        "skill_categories": ("vector_db",),
        "infer_patterns": [r"\b(pinecone|faiss|elasticsearch|weaviate|qdrant|milvus|vector database)\b"],
        "shift_terms": {"database", "index", "opensearch"},
    },
    "python": {
        "label": "Strong Python production experience",
        "skill_categories": ("python",),
        "infer_patterns": [r"\b(python|pyspark|fastapi|django|flask)\b"],
        "shift_terms": {"backend", "scripting", "data pipeline"},
    },
    "ranking_eval": {
        "label": "Evaluation frameworks for ranking systems (NDCG, MRR, MAP)",
        "skill_categories": ("evaluation", "ranking"),
        "infer_patterns": [r"\b(ndcg|mrr|map|a/b test|offline evaluation|learning to rank)\b"],
        "shift_terms": {"metrics", "benchmark", "experiment"},
    },
    "llm_production": {
        "label": "LLM integration and fine-tuning in production",
        "skill_categories": ("llm",),
        "infer_patterns": [r"\b(llm|fine.?tun|lora|qlora|language model|transformer)\b"],
        "shift_terms": {"nlp", "gpt", "prompt"},
    },
    "production_ml": {
        "label": "Production ML deployment and serving",
        "skill_categories": ("ml_ops",),
        "infer_patterns": [r"\b(production|deployed|shipped|model serving|ml platform|pipeline)\b"],
        "shift_terms": {"mlflow", "kubeflow", "serving", "inference"},
    },
}

INFERRED_SKILL_LABELS = {
    "retrieval": "Retrieval / search systems",
    "embeddings": "Embeddings / vector search",
    "ranking": "Ranking / recommendation",
    "llm": "LLM / fine-tuning",
    "python": "Python engineering",
    "vector_db": "Vector database operations",
    "evaluation": "Ranking evaluation (NDCG/MAP)",
    "ml_ops": "ML platform / serving",
}


def _to_ten(value: float) -> float:
    return round(max(0.0, min(10.0, value * 10.0)), 2)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.-]+", text.lower()))


def build_jd_context(job_description: str) -> dict[str, Any]:
    """Build shared JD context for batch ranking."""
    return {
        "text": job_description,
        "tokens": _tokenize(job_description),
        "keywords": JD_KEYWORDS,
        "requirements": JD_REQUIREMENTS,
        "target_skills": {k.lower() for k in JD_KEYWORDS},
    }


def load_candidates(path: str | Path) -> list[dict[str, Any]]:
    """Load candidates from JSON, JSONL, or gzipped JSONL."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Candidates file not found: {path}")

    if path.suffix == ".gz" or path.name.endswith(".jsonl.gz"):
        opener = gzip.open
        mode = "rt"
        actual_path = path
    elif path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data if isinstance(data, list) else [data]
        for i, record in enumerate(records, start=1):
            errors = validate_candidate(record, line_no=i)
            if errors:
                raise ValueError(errors[0])
        return records
    else:
        opener = open
        mode = "r"
        actual_path = path

    candidates: list[dict[str, Any]] = []
    with opener(actual_path, mode, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            errors = validate_candidate(record, line_no=line_no)
            if errors:
                raise ValueError(errors[0])
            candidates.append(record)
    return candidates


def _collect_profile_sentences(candidate: dict[str, Any]) -> list[str]:
    sentences: list[str] = []
    profile = candidate.get("profile") or {}

    for text in (profile.get("summary", ""), profile.get("headline", "")):
        for part in re.split(r"(?<=[.!?])\s+", text):
            part = part.strip()
            if len(part) > 20:
                sentences.append(part)

    for job in candidate.get("career_history") or []:
        for part in re.split(r"(?<=[.!?])\s+", job.get("description", "")):
            part = part.strip()
            if len(part) > 20:
                sentences.append(part)

    return sentences


def _build_evidence_trail(candidate: dict[str, Any], jd_context: dict[str, Any]) -> list[str]:
    """Extract profile sentences that justify the score."""
    keywords = jd_context.get("keywords", JD_KEYWORDS)
    evidence: list[str] = []

    for sentence in _collect_profile_sentences(candidate):
        lower = sentence.lower()
        if any(kw in lower for kw in keywords):
            evidence.append(sentence)
        if len(evidence) >= 6:
            break

    if not evidence:
        profile = candidate.get("profile") or {}
        summary = profile.get("summary", "").strip()
        if summary:
            evidence.append(summary[:240] + ("..." if len(summary) > 240 else ""))

    return evidence[:6]


def _build_inferred_skills(candidate: dict[str, Any]) -> list[str]:
    """Skills inferred from career descriptions, not explicitly listed."""
    skill_result = score_skill_match(candidate)
    inferred = list(skill_result.get("inferred_from_career", []))

    for category, confidence in infer_skills_from_text(candidate).items():
        if confidence < 0.45:
            continue
        label = INFERRED_SKILL_LABELS.get(category, category.replace("_", " ").title())
        if label not in inferred:
            explicit = set(extract_skill_names(candidate).keys())
            aliases = CORE_JD_SKILLS.get(category, set())
            if not any(any(alias in skill for alias in aliases) for skill in explicit):
                inferred.append(label)

    return inferred


def _requirement_text(candidate: dict[str, Any]) -> str:
    profile = candidate.get("profile") or {}
    parts = [profile.get("summary", ""), profile.get("headline", "")]
    for job in candidate.get("career_history") or []:
        parts.extend([job.get("description", ""), job.get("title", "")])
    for skill in candidate.get("skills") or []:
        parts.append(skill.get("name", ""))
    return " ".join(parts).lower()


def _build_gap_analysis(candidate: dict[str, Any], jd_context: dict[str, Any]) -> dict[str, list[str]]:
    """Classify each must-have skill group by match quality."""
    gap: dict[str, list[str]] = {
        "zero_gap": [],
        "inferrable": [],
        "domain_shift": [],
        "genuine_gap": [],
    }

    career_text = _career_text(candidate)
    full_text = _requirement_text(candidate)
    skills_result = score_skill_match(candidate)

    for group_name, terms in MUST_HAVE_GROUPS:
        label = MUST_HAVE_GROUP_LABELS.get(group_name, group_name)
        in_career = any(term in career_text for term in terms)
        in_skills, meta = _find_listed_skill_match(terms, candidate)

        if in_skills and meta:
            weak_listed = meta["proficiency"] == "beginner" and meta["endorsements"] < 5
            if weak_listed and not in_career:
                gap["domain_shift"].append(label)
            else:
                gap["zero_gap"].append(label)
        elif in_career:
            gap["inferrable"].append(label)
        elif any(term in full_text for term in terms):
            gap["domain_shift"].append(label)
        else:
            gap["genuine_gap"].append(label)

    return gap


def _jd_lexical_score(jd_tokens: set[str], doc_tokens: set[str]) -> float:
    if not jd_tokens:
        return 0.0
    overlap = len(jd_tokens & doc_tokens)
    keyword_overlap = len(doc_tokens & JD_KEYWORDS)
    base = overlap / max(len(jd_tokens), 1)
    keyword_bonus = min(0.3, keyword_overlap * 0.03)
    return min(1.0, base * 0.5 + keyword_bonus)


def score_candidate(candidate: dict[str, Any], jd_context: dict[str, Any]) -> dict[str, Any]:
    """
    Score one candidate against the JD.

    Returns scores on 0–10 scale plus evidence, inferred skills, and gap analysis.
    Hard-disqualified candidates receive all-zero scores.
    """
    disqualified, disqualify_reason = check_disqualifiers(candidate)
    target_skills = jd_context.get("target_skills", set())

    inferred_skills = _build_inferred_skills(candidate)
    gap_analysis = _build_gap_analysis(candidate, jd_context)
    evidence_trail = _build_evidence_trail(candidate, jd_context)

    skills = score_skill_match(candidate)

    if skills.get("skill_disqualified"):
        disqualified = True
        disqualify_reason = skills.get("skill_disqualify_reason")

    if disqualified:
        return {
            "total_score": 0.0,
            "skill_match_score": 0.0,
            "career_quality_score": 0.0,
            "behavioral_score": 0.0,
            "availability_score": 0.0,
            "disqualified": True,
            "disqualify_reason": disqualify_reason,
            "evidence_trail": evidence_trail,
            "inferred_skills": inferred_skills,
            "gap_analysis": gap_analysis,
        }

    skill_match_score = skills["score"]
    career_detail = score_career_quality_detailed(candidate)
    career_quality_score = career_detail["score"]

    behavioral_detail = score_behavioral_detailed(candidate)
    behavioral_score = behavioral_detail["score"]
    availability_score = score_availability(candidate)

    total_score = compute_final_score(
        skill_match_score,
        career_quality_score,
        behavioral_score,
        availability_score,
        disqualified=False,
    )

    return {
        "total_score": total_score,
        "skill_match_score": skill_match_score,
        "career_quality_score": career_quality_score,
        "behavioral_score": behavioral_score,
        "availability_score": availability_score,
        "disqualified": False,
        "disqualify_reason": None,
        "evidence_trail": evidence_trail,
        "inferred_skills": inferred_skills,
        "gap_analysis": gap_analysis,
        "_internal": {
            "core_skill_count": skills["core_skill_count"],
            "matched_skills": skills["matched_skills"][:8],
            "must_have_score": skills["must_have_score"],
            "nice_to_have_bonus": skills["nice_to_have_bonus"],
            "must_have_coverage": skills["must_have_coverage"],
            "career_detail": career_detail,
            "behavioral_detail": behavioral_detail,
        },
    }


def generate_reasoning(candidate: dict[str, Any], score_result: dict[str, Any]) -> str:
    """Generate honest, fact-based reasoning from score output."""
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}

    if score_result.get("disqualified"):
        title = profile.get("current_title", "Unknown")
        years = profile.get("years_of_experience", 0)
        return f"{title} with {years:.1f} yrs — disqualified: {score_result.get('disqualify_reason')}."

    title = profile.get("current_title", "Unknown")
    years = profile.get("years_of_experience", 0)
    response_rate = signals.get("recruiter_response_rate", 0)
    notice = signals.get("notice_period_days", 0)

    strengths: list[str] = []
    concerns: list[str] = []

    gap = score_result.get("gap_analysis", {})
    if gap.get("zero_gap"):
        strengths.append(f"direct match on {gap['zero_gap'][0]}")
    if gap.get("inferrable"):
        strengths.append(f"inferrable fit: {gap['inferrable'][0]}")
    if score_result.get("inferred_skills"):
        strengths.append(f"inferred {score_result['inferred_skills'][0]} from career history")

    if gap.get("genuine_gap"):
        concerns.append(f"gaps in {', '.join(gap['genuine_gap'][:2])}")

    if score_result.get("skill_match_score", 0) >= 7:
        internal = score_result.get("_internal", {})
        strengths.append(
            f"skill match {score_result['skill_match_score']:.1f}/10 "
            f"(must-have {internal.get('must_have_score', 0):.1f}"
            f"+ bonus {internal.get('nice_to_have_bonus', 0):.1f})"
        )
    elif score_result.get("skill_match_score", 0) < 4:
        concerns.append(f"weak skill match ({score_result['skill_match_score']:.1f}/10)")

    if 5 <= years <= 9:
        strengths.append(f"{years:.1f} yrs in target band")
    elif years < 5:
        concerns.append(f"{years:.1f} yrs below ideal band")

    if response_rate >= 0.6:
        strengths.append(f"response rate {response_rate:.0%}")
    elif response_rate < 0.3:
        concerns.append(f"low response rate ({response_rate:.0%})")

    if notice > 60:
        concerns.append(f"{notice}-day notice period")

    if score_result.get("availability_score", 0) < 4:
        concerns.append("low availability signals")

    strength_text = "; ".join(strengths[:2]) if strengths else "some adjacent skills"
    if concerns:
        return f"{title} with {years:.1f} yrs — {strength_text}. Concerns: {'; '.join(concerns[:2])}."
    return f"{title} with {years:.1f} yrs — {strength_text}; response rate {response_rate:.0%}."


def _fast_disqualify_check(candidate: dict[str, Any]) -> tuple[bool, str | None]:
    """Quick hard disqualifier check before full scoring."""
    from inferencer import check_disqualifying_skill_context

    dq, reason = check_disqualifiers(candidate)
    if dq:
        return True, reason
    skill_dq, skill_reason = check_disqualifying_skill_context(candidate)
    if skill_dq:
        return True, skill_reason
    return False, None


def _zero_score_result(
    candidate: dict[str, Any],
    reason: str | None,
    jd_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "total_score": 0.0,
        "skill_match_score": 0.0,
        "career_quality_score": 0.0,
        "behavioral_score": 0.0,
        "availability_score": 0.0,
        "disqualified": True,
        "disqualify_reason": reason,
        "evidence_trail": _build_evidence_trail(candidate, jd_context),
        "inferred_skills": [],
        "gap_analysis": {"zero_gap": [], "inferrable": [], "domain_shift": [], "genuine_gap": []},
    }


def rank_candidates(
    candidates: list[dict[str, Any]],
    job_description: str,
    top_k: int = 100,
    progress_callback: ProgressCallback = None,
    use_llm: bool = False,
    llm_top_n: int = 200,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Fast ranking pipeline:
    1. Hard disqualifier filter
    2. Vectorized scoring for remaining candidates
    3. Optional LLM on top N (handled by caller if async)
    4. Return top K
    """
    jd_context = build_jd_context(job_description)
    total = len(candidates)
    stats = {"total": total, "disqualified": 0, "scored": 0, "shortlisted": 0}

    if progress_callback:
        progress_callback(0.02, "Filtering candidates...")

    active: list[dict[str, Any]] = []
    dq_results: list[dict[str, Any]] = []

    for candidate in candidates:
        is_dq, reason = _fast_disqualify_check(candidate)
        if is_dq:
            stats["disqualified"] += 1
            sr = _zero_score_result(candidate, reason, jd_context)
            dq_results.append({
                "candidate_id": candidate["candidate_id"],
                "score": 0.0,
                "candidate": candidate,
                "score_result": sr,
            })
        else:
            active.append(candidate)

    if progress_callback:
        progress_callback(
            0.08,
            f"Filtered {stats['disqualified']:,} disqualified — scoring {len(active):,} candidates...",
        )

    scored: list[dict[str, Any]] = list(dq_results)
    batch_size = max(1, len(active) // 20) if active else 1

    for i, candidate in enumerate(active):
        result = score_candidate(candidate, jd_context)
        scored.append({
            "candidate_id": candidate["candidate_id"],
            "score": round(result["total_score"] / 10.0, 6),
            "candidate": candidate,
            "score_result": result,
        })
        if progress_callback and (i + 1) % batch_size == 0:
            pct = 0.08 + 0.72 * ((i + 1) / max(len(active), 1))
            progress_callback(pct, f"Scored {i + 1:,} / {len(active):,} candidates")

    stats["scored"] = len(scored)

    if progress_callback:
        progress_callback(0.82, "Sorting candidates...")

    scored.sort(key=lambda x: (-round(x["score"], 4), x["candidate_id"]))

    return scored, stats


def finalize_rank_results(
    scored: list[dict[str, Any]],
    top_k: int = 100,
    progress_callback: ProgressCallback = None,
) -> list[dict[str, Any]]:
    """Build final ranked output from scored list (post-LLM re-sort)."""
    if progress_callback:
        progress_callback(0.95, "Generating output...")

    top = scored[:top_k]
    results: list[dict[str, Any]] = []

    for rank, item in enumerate(top, start=1):
        sr = item["score_result"]
        reasoning = sr.get("recruiter_rationale") or generate_reasoning(item["candidate"], sr)
        internal = sr.get("_internal", {})
        behavioral_detail = internal.get("behavioral_detail", {})
        results.append({
            "candidate_id": item["candidate_id"],
            "rank": rank,
            "score": item["score"],
            "reasoning": reasoning,
            "candidate": item["candidate"],
            "breakdown": {
                "total_score": sr["total_score"],
                "skill_match_score": sr["skill_match_score"],
                "career_quality_score": sr["career_quality_score"],
                "behavioral_score": sr["behavioral_score"],
                "availability_score": sr["availability_score"],
                "disqualified": sr["disqualified"],
                "disqualify_reason": sr["disqualify_reason"],
                "evidence_trail": sr.get("evidence_trail", []),
                "inferred_skills": sr.get("inferred_skills", []),
                "gap_analysis": sr.get("gap_analysis", {}),
                "key_gaps": sr.get("key_gaps", []),
                "recruiter_rationale": sr.get("recruiter_rationale", reasoning),
                "inference_confidence": sr.get("inference_confidence"),
                "matched_skills": internal.get("matched_skills", []),
                "must_have_score": internal.get("must_have_score"),
                "nice_to_have_bonus": internal.get("nice_to_have_bonus"),
                "career_detail": internal.get("career_detail"),
                "behavioral_detail": behavioral_detail,
            },
        })

    if progress_callback:
        progress_callback(1.0, f"Ranking complete — top {top_k} selected")

    return results
