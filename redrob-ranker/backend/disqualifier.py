"""Hard disqualifier logic for Senior AI Engineer JD."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

CONSULTING_COMPANIES = [
    "TCS", "Tata Consultancy", "Infosys", "Wipro", "Accenture",
    "Cognizant", "Capgemini", "HCL Technologies", "HCL", "Tech Mahindra",
    "Mphasis", "Hexaware", "Mindtree", "LTIMindtree", "LTI",
]

PRODUCT_SIZES = {"1-10", "11-50", "51-200", "201-500", "501-1000"}
INDIA_COUNTRY_VALUES = {"india", "in"}


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _is_consulting_company(company: str) -> bool:
    company_lower = company or ""
    return any(c.lower() in company_lower.lower() for c in CONSULTING_COMPANIES)


def _is_product_company(job: dict[str, Any]) -> bool:
    industry = _normalize(job.get("industry", ""))
    size = job.get("company_size", "")
    company = _normalize(job.get("company", ""))
    if _is_consulting_company(job.get("company", "")):
        return False
    return size in PRODUCT_SIZES or "product" in industry or "saas" in industry


def check_honeypot(candidate: dict[str, Any]) -> tuple[bool, str | None]:
    """Detect subtly impossible profiles (honeypots)."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    career_history = candidate.get("career_history", [])

    # Impossibility 1: years_of_experience > career span
    if career_history:
        try:
            career_start = min(r["start_date"] for r in career_history if r.get("start_date"))
            actual_years = (datetime.today() - datetime.fromisoformat(career_start)).days / 365
            if profile.get("years_of_experience", 0) > actual_years + 3:
                return True, f"Years of experience ({profile.get('years_of_experience')}) exceeds career span ({actual_years:.1f} years)"
        except (ValueError, KeyError):
            pass

    # Impossibility 2: skill duration_months > total career months
    if career_history:
        total_career_months = sum(r.get("duration_months", 0) for r in career_history)
        for skill in skills:
            skill_duration = skill.get("duration_months", 0)
            if skill_duration > total_career_months + 12:
                return True, f"Skill '{skill.get('name')}' duration ({skill_duration} months) exceeds total career ({total_career_months} months)"

    # Impossibility 3: profile_completeness_score == 100 but missing key fields
    if signals.get("profile_completeness_score") == 100.0:
        if not candidate.get("education") or not candidate.get("certifications"):
            missing = []
            if not candidate.get("education"):
                missing.append("education")
            if not candidate.get("certifications"):
                missing.append("certifications")
            return True, f"Profile completeness 100% but missing: {', '.join(missing)}"

    # Impossibility 4: last_active_date in the future
    try:
        last_active = datetime.fromisoformat(signals["last_active_date"])
        if last_active > datetime.today():
            return True, f"Last active date ({signals['last_active_date']}) is in the future"
    except (ValueError, KeyError):
        pass

    return False, None


def check_disqualifiers(candidate: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Hard disqualifiers — return (True, reason) to zero-score the candidate.
    """
    career = candidate.get("career_history") or []
    profile = candidate.get("profile") or {}
    signals = candidate.get("redrob_signals") or {}

    # Honeypot profiles
    triggered, reason = check_honeypot(candidate)
    if triggered:
        return True, reason

    # Rule 1: Entire career at consulting firms only
    if len(career) >= 2:
        all_consulting = all(
            _is_consulting_company(role.get("company", ""))
            for role in career
        )
        if all_consulting:
            return True, "Entire career at IT services/consulting firms"

    # Rule 2: Current company is consulting AND no prior product company
    current_company = profile.get("current_company", "")
    if _is_consulting_company(current_company):
        prior_product = any(
            _is_product_company(role)
            for role in career
            if not role.get("is_current")
        )
        if not prior_product:
            return True, "Currently at consulting firm with no prior product company experience"

    # Rule 3: Country not India — must be willing to relocate
    country = _normalize(profile.get("country", ""))
    if country and country not in INDIA_COUNTRY_VALUES:
        if not signals.get("willing_to_relocate"):
            return True, "Located outside India, not willing to relocate"

    # Rule 4: Extreme experience outliers
    yoe = profile.get("years_of_experience", 0)
    if yoe < 3:
        return True, "Insufficient experience (< 3 years)"
    if yoe > 15:
        return True, "Experience exceeds role band (> 15 years)"

    # Keyword-stuffer trap: irrelevant title with stuffed AI skills
    title = _normalize(profile.get("current_title", ""))
    irrelevant_titles = (
        "hr manager", "marketing manager", "content writer", "graphic designer",
        "accountant", "sales executive", "customer support", "civil engineer",
        "mechanical engineer", "operations manager",
    )
    ai_skill_count = sum(
        1 for s in candidate.get("skills", [])
        if any(k in _normalize(s.get("name", "")) for k in ("ml", "ai", "nlp", "llm", "pytorch"))
    )
    if any(t in title for t in irrelevant_titles) and ai_skill_count >= 5:
        return True, f"Irrelevant title '{profile.get('current_title')}' with keyword-stuffed AI skills"

    return False, None
