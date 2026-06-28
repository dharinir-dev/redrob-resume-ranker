import CandidateCard from './CandidateCard';

export default function RankingResults({ results, stats, jobId, onDownload, onCopyMetadata }) {
  if (!results?.length) return null;

  return (
    <section className="rounded-xl border border-white/10 bg-navy-card p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-teal">Results</h2>
          <p className="text-sm text-white/50">
            {stats?.total?.toLocaleString()} processed · {stats?.disqualified?.toLocaleString()} disqualified · {results.length} shortlisted
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCopyMetadata}
            className="rounded-lg border border-white/20 px-4 py-2 text-sm text-white/80 hover:bg-white/5"
          >
            Copy metadata
          </button>
          <button
            type="button"
            onClick={onDownload}
            className="rounded-lg bg-teal px-4 py-2 text-sm font-semibold text-navy hover:bg-teal/90"
          >
            Download CSV
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {results.map((r) => (
          <CandidateCard key={r.candidate_id} result={r} />
        ))}
      </div>
    </section>
  );
}
