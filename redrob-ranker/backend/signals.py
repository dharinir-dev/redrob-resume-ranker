"""Behavioral and availability signal scoring (0–10 scale)."""

from __future__ import annotations

import datetime
from typing import Any

PREFERRED_LOCATIONS = [
    "pune", "noida", "delhi", "ncr", "gurugram", "gurgaon", "mumbai",
    "bangalore", "bengaluru", "hyderabad", "chennai", "india",
]

REFERENCE_DATE = datetime.date(2026, 6, 28)


def score_behavioral(candidate: dict[str, Any], today: datetime.date | None = None) -> float:
    """
    Behavioral signal score 0–10.
    Recency (30%), response rate (20%), open-to-work (15%), interview completion (15%),
    notice period (10%), GitHub (10%).
    """
    sig = candidate.get("redrob_signals") or {}
    ref = today or REFERENCE_DATE

    try:
        last_active = datetime.date.fromisoformat(sig["last_active_date"])
        days_inactive = (ref - last_active).days
    except (KeyError, ValueError, TypeError):
        days_inactive = 365

    if days_inactive <= 7:
        recency_score = 10
    elif days_inactive <= 30:
        recency_score = 8
    elif days_inactive <= 90:
        recency_score = 5
    elif days_inactive <= 180:
        recency_score = 2
    else:
        recency_score = 0

    rrr = float(sig.get("recruiter_response_rate", 0))
    if rrr >= 0.7:
        response_score = 10
    elif rrr >= 0.5:
        response_score = 7
    elif rrr >= 0.3:
        response_score = 4
    else:
        response_score = 1

    otw_score = 10 if sig.get("open_to_work_flag") else 3

    icr = float(sig.get("interview_completion_rate", 0))
    icr_score = icr * 10

    np_days = int(sig.get("notice_period_days", 90))
    if np_days <= 30:
        np_score = 10
    elif np_days <= 60:
        np_score = 6
    elif np_days <= 90:
        np_score = 3
    else:
        np_score = 1

    gh = sig.get("github_activity_score", -1)
    if gh is None or float(gh) == -1:
        gh_score = 4
    else:
        gh_score = float(gh) / 10

    return round(
        recency_score * 0.30
        + response_score * 0.20
        + otw_score * 0.15
        + icr_score * 0.15
        + np_score * 0.10
        + gh_score * 0.10,
        2,
    )


def score_behavioral_detailed(candidate: dict[str, Any], today: datetime.date | None = None) -> dict[str, Any]:
    """Behavioral score with component breakdown."""
    sig = candidate.get("redrob_signals") or {}
    ref = today or REFERENCE_DATE

    try:
        last_active = datetime.date.fromisoformat(sig["last_active_date"])
        days_inactive = (ref - last_active).days
    except (KeyError, ValueError, TypeError):
        days_inactive = 365
        last_active = None

    if days_inactive <= 7:
        recency_score = 10
    elif days_inactive <= 30:
        recency_score = 8
    elif days_inactive <= 90:
        recency_score = 5
    elif days_inactive <= 180:
        recency_score = 2
    else:
        recency_score = 0

    rrr = float(sig.get("recruiter_response_rate", 0))
    if rrr >= 0.7:
        response_score = 10
    elif rrr >= 0.5:
        response_score = 7
    elif rrr >= 0.3:
        response_score = 4
    else:
        response_score = 1

    otw_score = 10 if sig.get("open_to_work_flag") else 3
    icr_score = float(sig.get("interview_completion_rate", 0)) * 10

    np_days = int(sig.get("notice_period_days", 90))
    if np_days <= 30:
        np_score = 10
    elif np_days <= 60:
        np_score = 6
    elif np_days <= 90:
        np_score = 3
    else:
        np_score = 1

    gh = sig.get("github_activity_score", -1)
    gh_score = 4 if gh is None or float(gh) == -1 else float(gh) / 10

    composite = round(
        recency_score * 0.30 + response_score * 0.20 + otw_score * 0.15
        + icr_score * 0.15 + np_score * 0.10 + gh_score * 0.10,
        2,
    )

    return {
        "score": composite,
        "recency_score": recency_score,
        "response_score": response_score,
        "open_to_work_score": otw_score,
        "interview_completion_score": round(icr_score, 2),
        "notice_period_score": np_score,
        "github_score": round(gh_score, 2),
        "days_inactive": days_inactive,
        "last_active_date": sig.get("last_active_date"),
        "recruiter_response_rate": rrr,
        "notice_period_days": np_days,
        "open_to_work": bool(sig.get("open_to_work_flag")),
    }


def score_availability(candidate: dict[str, Any]) -> float:
    """
    Availability score 0–10.
    Location (40%), work mode (25%), salary fit (20%), verification (15%).
    """
    sig = candidate.get("redrob_signals") or {}
    profile = candidate.get("profile") or {}

    location = (profile.get("location") or "").lower()
    country = (profile.get("country") or "").lower()

    if country in ("india", "in"):
        if any(city in location for city in PREFERRED_LOCATIONS):
            location_score = 10
        else:
            location_score = 7 if sig.get("willing_to_relocate") else 4
    else:
        location_score = 2 if sig.get("willing_to_relocate") else 0

    wm = sig.get("preferred_work_mode", "")
    wm_score = {"hybrid": 10, "flexible": 9, "onsite": 7, "remote": 4}.get(wm, 5)

    sal = sig.get("expected_salary_range_inr_lpa") or {}
    sal_min = float(sal.get("min", 0))
    sal_max = float(sal.get("max", 0))
    if sal_max <= 80 and sal_min >= 20:
        salary_score = 10
    elif sal_min > 80:
        salary_score = 4
    else:
        salary_score = 7

    verified = (bool(sig.get("verified_email")) + bool(sig.get("verified_phone"))) * 2.5

    return round(
        location_score * 0.40
        + wm_score * 0.25
        + salary_score * 0.20
        + verified * 0.15,
        2,
    )


def compute_final_score(
    skill: float,
    career: float,
    behavioral: float,
    availability: float,
    disqualified: bool,
) -> float:
    """Final weighted score 0–10."""
    if disqualified:
        return 0.0
    return round(
        skill * 0.30 + career * 0.25 + behavioral * 0.25 + availability * 0.20,
        2,
    )
