export default function UploadPanel({ file, onFileChange, onUseSample, disabled, totalCandidates }) {
  return (
    <section className="rounded-xl border border-white/10 bg-navy-card p-6">
      <h2 className="text-lg font-semibold text-teal">Upload & Configure</h2>
      <p className="mt-1 text-sm text-white/60">Upload candidates.jsonl.gz or use the demo sample</p>

      <div
        className={`relative mt-4 flex flex-col items-center rounded-lg border-2 border-dashed px-6 py-10 transition ${
          disabled ? 'opacity-50' : 'border-white/20 hover:border-teal/50'
        }`}
      >
        {file ? (
          <p className="font-medium text-teal">{file.name}</p>
        ) : (
          <>
            <p className="text-white/80">Drop JSON / JSONL / .gz file here</p>
            <p className="mt-1 text-xs text-white/40">or click to browse</p>
          </>
        )}
        <input
          type="file"
          accept=".json,.jsonl,.gz"
          disabled={disabled}
          onChange={(e) => e.target.files?.[0] && onFileChange(e.target.files[0])}
          className="absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
      </div>

      {totalCandidates > 0 && (
        <p className="mt-2 text-sm text-white/50">{totalCandidates.toLocaleString()} candidates detected</p>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={onUseSample}
        className="mt-4 w-full rounded-lg border border-teal/40 py-2.5 text-sm font-medium text-teal transition hover:bg-teal/10 disabled:opacity-50"
      >
        Use sample dataset (50 candidates)
      </button>
    </section>
  );
}
