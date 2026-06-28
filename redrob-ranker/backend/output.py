"""CSV generation — full export and hackathon submission format."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

FULL_CSV_HEADER = [
    "rank", "candidate_id", "name", "current_title", "years_experience", "location",
    "overall_score", "skill_match_score", "career_quality_score", "behavioral_score",
    "availability_score", "evidence_1", "evidence_2", "evidence_3",
    "inferred_skills", "key_gaps", "recruiter_rationale",
    "notice_period_days", "last_active_date", "open_to_work",
    "disqualified", "disqualify_reason",
]

HACKATHON_HEADER = ["candidate_id", "rank", "score", "reasoning"]


def _row_from_result(row: dict[str, Any]) -> dict[str, str]:
    candidate = row.get("candidate") or {}
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}
    bd = row.get("breakdown") or {}
    gap = bd.get("gap_analysis") or {}
    evidence = bd.get("evidence_trail") or bd.get("llm_evidence") or []
    inferred = bd.get("inferred_skills") or bd.get("llm_inferred_skills") or []
    key_gaps = bd.get("key_gaps") or gap.get("genuine_gap") or []
    rationale = bd.get("recruiter_rationale") or row.get("reasoning", "")

    if isinstance(inferred, list):
        inferred_str = "; ".join(inferred)
    else:
        inferred_str = str(inferred)

    if isinstance(key_gaps, list):
        gaps_str = "; ".join(key_gaps)
    else:
        gaps_str = str(key_gaps)

    return {
        "rank": str(row.get("rank", "")),
        "candidate_id": row.get("candidate_id", ""),
        "name": profile.get("anonymized_name", ""),
        "current_title": profile.get("current_title", ""),
        "years_experience": str(profile.get("years_of_experience", "")),
        "location": profile.get("location", ""),
        "overall_score": f"{bd.get('total_score', row.get('score', 0) * 10):.2f}",
        "skill_match_score": f"{bd.get('skill_match_score', 0):.2f}",
        "career_quality_score": f"{bd.get('career_quality_score', 0):.2f}",
        "behavioral_score": f"{bd.get('behavioral_score', 0):.2f}",
        "availability_score": f"{bd.get('availability_score', 0):.2f}",
        "evidence_1": evidence[0] if len(evidence) > 0 else "",
        "evidence_2": evidence[1] if len(evidence) > 1 else "",
        "evidence_3": evidence[2] if len(evidence) > 2 else "",
        "inferred_skills": inferred_str,
        "key_gaps": gaps_str,
        "recruiter_rationale": rationale,
        "notice_period_days": str(signals.get("notice_period_days", "")),
        "last_active_date": signals.get("last_active_date", ""),
        "open_to_work": str(signals.get("open_to_work_flag", "")),
        "disqualified": str(bd.get("disqualified", False)),
        "disqualify_reason": bd.get("disqualify_reason") or "",
    }


def write_full_csv(results: list[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FULL_CSV_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow(_row_from_result(row))


def write_submission_csv(results: list[dict[str, Any]], output_path: str | Path) -> None:
    """Hackathon format: candidate_id, rank, score, reasoning."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HACKATHON_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow({
                "candidate_id": row["candidate_id"],
                "rank": row["rank"],
                "score": f"{row['score']:.4f}",
                "reasoning": row.get("reasoning", ""),
            })


def full_csv_bytes(results: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FULL_CSV_HEADER, lineterminator="\n")
    writer.writeheader()
    for row in results:
        writer.writerow(_row_from_result(row))
    return buffer.getvalue().encode("utf-8")


def submission_csv_bytes(results: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HACKATHON_HEADER, lineterminator="\n")
    writer.writeheader()
    for row in results:
        writer.writerow({
            "candidate_id": row["candidate_id"],
            "rank": row["rank"],
            "score": f"{row['score']:.4f}",
            "reasoning": row.get("reasoning", ""),
        })
    return buffer.getvalue().encode("utf-8")
