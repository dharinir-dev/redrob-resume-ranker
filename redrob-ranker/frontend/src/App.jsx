import { useCallback, useEffect, useState } from 'react';
import UploadPanel from './components/UploadPanel';
import JobDescriptionPanel from './components/JobDescriptionPanel';
import ProgressBar from './components/ProgressBar';
import RankingResults from './components/RankingResults';

const API = import.meta.env.VITE_API_URL || '';

export default function App() {
  const [jobDescription, setJobDescription] = useState('');
  const [file, setFile] = useState(null);
  const [totalCandidates, setTotalCandidates] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/default-jd`)
      .then((r) => r.json())
      .then((d) => setJobDescription(d.job_description || ''))
      .catch(() => setError('Failed to load job description'));
  }, []);

  const estimateCount = useCallback(async (f) => {
    if (!f) { setTotalCandidates(0); return; }
    if (f.name.endsWith('.json')) {
      const t = await f.text();
      const d = JSON.parse(t);
      setTotalCandidates(Array.isArray(d) ? d.length : 1);
    } else if (!f.name.endsWith('.gz')) {
      const t = await f.text();
      setTotalCandidates(t.split('\n').filter((l) => l.trim()).length);
    } else setTotalCandidates(0);
  }, []);

  const poll = useCallback(async (id) => {
    const resp = await fetch(`${API}/api/status/${id}`);
    const data = await resp.json();
    setStatus(data);
    setStats(data.stats);
    if (data.status === 'completed') {
      const r = await fetch(`${API}/api/results/${id}`);
      const rd = await r.json();
      setResults(rd.results);
      setStats(rd.stats);
      setRunning(false);
    } else if (data.status === 'failed') {
      setError(data.message);
      setRunning(false);
    }
  }, []);

  useEffect(() => {
    if (!jobId || !running) return;
    const iv = setInterval(() => poll(jobId), 800);
    return () => clearInterval(iv);
  }, [jobId, running, poll]);

  const startRank = async (formData, sample = false) => {
    setError(null);
    setResults(null);
    setRunning(true);
    try {
      const url = sample ? `${API}/api/rank-sample` : `${API}/api/rank`;
      const resp = await fetch(url, { method: 'POST', body: formData });
      if (!resp.ok) throw new Error((await resp.json()).detail || 'Rank failed');
      const { job_id } = await resp.json();
      setJobId(job_id);
      setStatus({ status: 'running', progress: 0, message: 'Starting...', total_candidates: totalCandidates });
    } catch (e) {
      setError(e.message);
      setRunning(false);
    }
  };

  const handleStart = () => {
    if (!file) { setError('Upload a file or use the sample dataset'); return; }
    const fd = new FormData();
    fd.append('candidates_file', file);
    fd.append('job_description', jobDescription);
    fd.append('use_llm', 'true');
    fd.append('top_k', '100');
    startRank(fd);
  };

  const handleSample = () => {
    setIsDemoMode(true);
    const fd = new FormData();
    fd.append('use_llm', 'true');
    startRank(fd, true);
  };

  const handleDownload = () => window.open(`${API}/api/download/${jobId}?format=full`, '_blank');

  const handleCopyMetadata = () => {
    const meta = {
      job_id: jobId,
      total: stats?.total,
      disqualified: stats?.disqualified,
      shortlisted: results?.length,
      top_candidate: results?.[0]?.candidate_id,
      generated_at: new Date().toISOString(),
    };
    navigator.clipboard.writeText(JSON.stringify(meta, null, 2));
  };

  return (
    <div className="min-h-screen bg-navy font-sans text-white">
      <header className="border-b border-white/10 px-6 py-5">
        <h1 className="text-2xl font-bold">
          <span className="text-teal">Redrob</span> Candidate Ranker
        </h1>
        <p className="text-sm text-white/50">Intelligent Candidate Discovery & Ranking · Hackathon Demo</p>
        {isDemoMode && (
          <div className="mt-2 inline-flex items-center rounded-full bg-amber-500/20 px-3 py-1 text-xs font-medium text-amber-300 border border-amber-500/30">
            ⚠️ Running in DEMO MODE (50 candidates)
          </div>
        )}
        {!isDemoMode && totalCandidates > 0 && (
          <div className="mt-2 inline-flex items-center rounded-full bg-green-500/20 px-3 py-1 text-xs font-medium text-green-300 border border-green-500/30">
            ✓ Full dataset loaded ({totalCandidates.toLocaleString()} candidates)
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <UploadPanel
            file={file}
            onFileChange={(f) => { setFile(f); estimateCount(f); }}
            onUseSample={handleSample}
            disabled={running}
            totalCandidates={totalCandidates}
          />
          <JobDescriptionPanel jobDescription={jobDescription} />
        </div>

        <div className="flex justify-center">
          <button
            type="button"
            disabled={running || !file}
            onClick={handleStart}
            className="rounded-xl bg-teal px-10 py-3 text-lg font-semibold text-navy shadow-lg shadow-teal/20 transition hover:bg-teal/90 disabled:opacity-40"
          >
            {running ? 'Ranking...' : 'Start Ranking'}
          </button>
        </div>

        {(running || status) && (
          <ProgressBar
            progress={status?.progress}
            message={status?.message}
            status={status?.status}
            processed={status?.processed}
            total={status?.total_candidates}
            stats={stats}
          />
        )}

        {results && (
          <RankingResults
            results={results}
            stats={stats}
            jobId={jobId}
            onDownload={handleDownload}
            onCopyMetadata={handleCopyMetadata}
          />
        )}
      </main>
    </div>
  );
}
