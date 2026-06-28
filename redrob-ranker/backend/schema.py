"""Candidate data schema — validation and field accessors for JSONL records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")

REQUIRED_ROOT = ("candidate_id", "profile", "career_history", "education", "skills", "redrob_signals")

REQUIRED_PROFILE = (
    "anonymized_name", "headline", "summary", "location", "country",
    "years_of_experience", "current_title", "current_company",
    "current_company_size", "current_industry",
)

REQUIRED_SIGNALS = (
    "profile_completeness_score", "signup_date", "last_active_date",
    "open_to_work_flag", "profile_views_received_30d", "applications_submitted_30d",
    "recruiter_response_rate", "avg_response_time_hours", "skill_assessment_scores",
    "connection_count", "endorsements_received", "notice_period_days",
    "expected_salary_range_inr_lpa", "preferred_work_mode", "willing_to_relocate",
    "github_activity_score", "search_appearance_30d", "saved_by_recruiters_30d",
    "interview_completion_rate", "offer_acceptance_rate", "verified_email",
    "verified_phone", "linkedin_connected",
)

PROFICIENCY_LEVELS = frozenset({"beginner", "intermediate", "advanced", "expert"})
WORK_MODES = frozenset({"remote", "hybrid", "onsite", "flexible"})
EDUCATION_TIERS = frozenset({"tier_1", "tier_2", "tier_3", "tier_4", "unknown"})
COMPANY_SIZES = frozenset({
    "1-10", "11-50", "51-200", "201-500", "501-1000",
    "1001-5000", "5001-10000", "10001+",
})

SCHEMA_PATH = Path(__file__).parent.parent / "candidate_schema.json"
BUNDLE_SCHEMA_PATH = Path(__file__).parent.parent.parent / "candidate_schema.json"


def get_schema_path() -> Path | None:
    for path in (SCHEMA_PATH, BUNDLE_SCHEMA_PATH):
        if path.exists():
            return path
    return None


def load_schema() -> dict[str, Any]:
    path = get_schema_path()
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate(candidate: dict[str, Any], line_no: int | None = None) -> list[str]:
    """Validate a single candidate record against the hackathon schema."""
    errors: list[str] = []
    prefix = f"Line {line_no}: " if line_no else ""

    if not isinstance(candidate, dict):
        return [f"{prefix}Candidate must be a JSON object"]

    for field in REQUIRED_ROOT:
        if field not in candidate:
            errors.append(f"{prefix}Missing required field '{field}'")

    cid = candidate.get("candidate_id")
    if cid and not CANDIDATE_ID_PATTERN.match(str(cid)):
        errors.append(f"{prefix}Invalid candidate_id '{cid}' — expected CAND_XXXXXXX")

    profile = candidate.get("profile")
    if isinstance(profile, dict):
        for field in REQUIRED_PROFILE:
            if field not in profile:
                errors.append(f"{prefix}profile.{field} is required")
        yoe = profile.get("years_of_experience")
        if yoe is not None and not isinstance(yoe, (int, float)):
            errors.append(f"{prefix}profile.years_of_experience must be numeric")
        size = profile.get("current_company_size")
        if size and size not in COMPANY_SIZES:
            errors.append(f"{prefix}Invalid profile.current_company_size '{size}'")

    skills = candidate.get("skills")
    if isinstance(skills, list):
        for i, skill in enumerate(skills):
            if not isinstance(skill, dict):
                continue
            prof = skill.get("proficiency")
            if prof and prof not in PROFICIENCY_LEVELS:
                errors.append(f"{prefix}skills[{i}].proficiency invalid: '{prof}'")

    signals = candidate.get("redrob_signals")
    if isinstance(signals, dict):
        for field in REQUIRED_SIGNALS:
            if field not in signals:
                errors.append(f"{prefix}redrob_signals.{field} is required")
        mode = signals.get("preferred_work_mode")
        if mode and mode not in WORK_MODES:
            errors.append(f"{prefix}Invalid preferred_work_mode '{mode}'")
        salary = signals.get("expected_salary_range_inr_lpa")
        if isinstance(salary, dict):
            if "min" not in salary or "max" not in salary:
                errors.append(f"{prefix}expected_salary_range_inr_lpa requires min and max")

    education = candidate.get("education")
    if isinstance(education, list):
        for i, edu in enumerate(education):
            if not isinstance(edu, dict):
                continue
            tier = edu.get("tier")
            if tier and tier not in EDUCATION_TIERS:
                errors.append(f"{prefix}education[{i}].tier invalid: '{tier}'")

    return errors


def validate_candidates(candidates: list[dict[str, Any]], max_errors: int = 10) -> tuple[list[dict], list[str]]:
    """Validate a list of candidates; return valid records and error messages."""
    valid: list[dict] = []
    errors: list[str] = []

    for i, candidate in enumerate(candidates, start=1):
        row_errors = validate_candidate(candidate, line_no=i)
        if row_errors:
            errors.extend(row_errors[:max_errors - len(errors)] if max_errors else row_errors)
            if max_errors and len(errors) >= max_errors:
                break
        else:
            valid.append(candidate)

    return valid, errors


def build_candidate_document(candidate: dict[str, Any]) -> str:
    """Flatten all schema fields into searchable text for lexical matching."""
    profile = candidate.get("profile") or {}
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_company", ""),
        profile.get("current_industry", ""),
        profile.get("current_company_size", ""),
        profile.get("location", ""),
        profile.get("country", ""),
    ]

    for job in candidate.get("career_history") or []:
        parts.extend([
            job.get("title", ""),
            job.get("company", ""),
            job.get("industry", ""),
            job.get("company_size", ""),
            job.get("description", ""),
        ])

    for edu in candidate.get("education") or []:
        parts.extend([
            edu.get("institution", ""),
            edu.get("degree", ""),
            edu.get("field_of_study", ""),
            edu.get("tier", ""),
        ])

    for skill in candidate.get("skills") or []:
        parts.append(
            f"{skill.get('name', '')} {skill.get('proficiency', '')} "
            f"{skill.get('duration_months', '')}mo"
        )

    for cert in candidate.get("certifications") or []:
        parts.extend([cert.get("name", ""), cert.get("issuer", "")])

    for lang in candidate.get("languages") or []:
        parts.append(f"{lang.get('language', '')} {lang.get('proficiency', '')}")

    assessments = (candidate.get("redrob_signals") or {}).get("skill_assessment_scores") or {}
    for skill_name, score in assessments.items():
        parts.append(f"{skill_name} assessment {score}")

    return " ".join(str(p) for p in parts if p)
