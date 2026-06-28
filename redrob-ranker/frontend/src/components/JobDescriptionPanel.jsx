export default function JobDescriptionPanel({ jobDescription }) {
  return (
    <section className="rounded-xl border border-white/10 bg-navy-card p-6">
      <h2 className="text-lg font-semibold text-teal">Job Description</h2>
      <p className="text-sm text-white/50">Senior AI Engineer — Founding Team (read-only)</p>
      <pre className="mt-4 max-h-64 overflow-auto rounded-lg bg-black/30 p-4 text-xs leading-relaxed text-white/80 whitespace-pre-wrap font-mono">
        {jobDescription || 'Loading...'}
      </pre>
    </section>
  );
}
