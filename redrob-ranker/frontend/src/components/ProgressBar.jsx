export default function ProgressBar({ progress, message, status, processed, total, stats }) {
  const pct = Math.round((progress || 0) * 100);
  const eta = total && progress > 0.05 ? Math.ceil((1 - progress) * (total / progress) * 0.01) : null;

  return (
    <section className="rounded-xl border border-white/10 bg-navy-card p-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-teal">Progress</h2>
        <span className="text-sm font-mono text-white/70">{status === 'failed' ? 'Error' : `${pct}%`}</span>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-black/40">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            status === 'failed' ? 'bg-red-500' : status === 'completed' ? 'bg-teal' : 'bg-teal/80'
          }`}
          style={{ width: `${status === 'failed' ? 100 : pct}%` }}
        />
      </div>

      <p className="mt-3 text-sm text-white/70">{message}</p>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/50">
        {total > 0 && <span>Processed: {processed?.toLocaleString() || 0} / {total.toLocaleString()}</span>}
        {stats?.disqualified != null && <span>Disqualified: {stats.disqualified.toLocaleString()}</span>}
        {stats?.shortlisted != null && <span>Shortlisted: {stats.shortlisted}</span>}
        {eta != null && status === 'running' && <span>ETA: ~{eta}s</span>}
      </div>
    </section>
  );
}
