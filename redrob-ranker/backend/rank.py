#!/usr/bin/env python3
"""CLI entry point for hackathon submission reproduction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from output import write_submission_csv
from ranker import finalize_rank_results, load_candidates, rank_candidates


def load_default_jd() -> str:
    jd_paths = [
        Path(__file__).parent / "default_jd.txt",
        Path(__file__).parent.parent.parent / "job_description.txt",
    ]
    for p in jd_paths:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "Senior AI Engineer — embeddings, retrieval, ranking, LLMs, Python, evaluation frameworks."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rank candidates against the Redrob Senior AI Engineer JD"
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to candidates.jsonl or candidates.jsonl.gz",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output submission CSV path",
    )
    parser.add_argument(
        "--jd",
        default=None,
        help="Optional path to job description text file",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="Number of candidates to rank (default: 100)",
    )
    args = parser.parse_args()

    if args.jd:
        job_description = Path(args.jd).read_text(encoding="utf-8")
    else:
        job_description = load_default_jd()

    print(f"Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates)
    print(f"Loaded {len(candidates):,} candidates")

    def progress(pct: float, msg: str) -> None:
        print(f"  [{pct * 100:5.1f}%] {msg}")

    print("Ranking...")
    scored, stats = rank_candidates(
        candidates, job_description, top_k=args.top_k, progress_callback=progress, use_llm=False
    )
    print(f"  Disqualified: {stats.get('disqualified', 0):,}")
    results = finalize_rank_results(scored, top_k=args.top_k)

    print(f"Writing submission to {args.out}...")
    write_submission_csv(results, args.out)
    print(f"Done. Top candidate: {results[0]['candidate_id']} (score={results[0]['score']:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
