function scoreColor(score) {
  if (score >= 8) return 'text-teal';
  if (score >= 6) return 'text-yellow-400';
  return 'text-orange-400';
}

function ScoreBar({ label, value, max = 10 }) {
  const pct = Math.round(((value || 0) / max) * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-white/50">
        <span>{label}</span>
        <span>{(value ?? 0).toFixed(1)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-black/40">
        <div className="h-full rounded-full bg-teal" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CandidateCard({ result }) {
  const { rank, profile, breakdown, signals, reasoning } = result;
  const total = breakdown?.total_score ?? result.score * 10;
  const bd = breakdown || {};
  const evidence = bd.evidence_trail || [];
  const gaps = bd.key_gaps?.length ? bd.key_gaps : bd.gap_analysis?.genuine_gap || [];

  return (
    <article className="rounded-xl border border-white/10 bg-navy-card p-5">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-teal/20 text-2xl font-bold text-teal">
          #{rank}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-white">
            {profile?.anonymized_name || 'Candidate'}
            <span className="ml-2 text-base font-normal text-white/60">{profile?.current_title}</span>
          </h3>
          <p className="text-sm text-white/50">{profile?.location} · {profile?.years_of_experience} yrs</p>
          <p className={`mt-1 text-2xl font-bold ${scoreColor(total)}`}>{total.toFixed(1)}/10</p>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <ScoreBar label="Skill Match" value={bd.skill_match_score} />
        <ScoreBar label="Career Quality" value={bd.career_quality_score} />
        <ScoreBar label="Behavioral" value={bd.behavioral_score} />
        <ScoreBar label="Availability" value={bd.availability_score} />
      </div>

      {evidence.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-white/40">Evidence</p>
          <ul className="list-inside list-disc space-y-1 text-sm text-white/70">
            {evidence.slice(0, 3).map((e) => (
              <li key={e} className="line-clamp-2">{e}</li>
            ))}
          </ul>
        </div>
      )}

      {bd.inferred_skills?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {bd.inferred_skills.map((s) => (
            <span key={s} className="rounded-full bg-teal/20 px-2.5 py-0.5 text-xs text-teal">{s}</span>
          ))}
        </div>
      )}

      {gaps.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {gaps.slice(0, 4).map((g) => (
            <span key={g} className="rounded-full bg-orange-500/20 px-2 py-0.5 text-xs text-orange-300">⚠ {g}</span>
          ))}
        </div>
      )}

      <p className="mt-3 text-sm italic text-white/60">{bd.recruiter_rationale || reasoning}</p>

      {signals && (
        <p className="mt-2 text-xs text-white/40">
          Last active: {signals.last_active_date} · Response: {((signals.recruiter_response_rate || 0) * 100).toFixed(0)}% · Notice: {signals.notice_period_days}d
        </p>
      )}
    </article>
  );
}
