"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { NavBar } from "@/components/NavBar";
import { analyzeResume, type ResumeAnalysis } from "@/lib/api";

function ScoreRing({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const color = pct >= 75 ? "#34d399" : pct >= 50 ? "#fbbf24" : "#f87171";
  return (
    <div
      className="flex h-28 w-28 items-center justify-center rounded-full"
      style={{ background: `conic-gradient(${color} ${pct * 3.6}deg, rgba(255,255,255,0.08) 0deg)` }}
    >
      <div className="flex h-20 w-20 flex-col items-center justify-center rounded-full bg-[#0b0b12]">
        <span className="text-2xl font-bold">{pct}</span>
        <span className="text-[10px] text-gray-400">ATS</span>
      </div>
    </div>
  );
}

function List({ title, items, tone }: { title: string; items?: string[]; tone: "good" | "bad" | "info" }) {
  if (!items?.length) return null;
  const cls =
    tone === "good"
      ? "bg-green-500/10 text-green-200"
      : tone === "bad"
        ? "bg-red-500/10 text-red-200"
        : "bg-white/5 text-gray-200";
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-gray-300">{title}</h3>
      <ul className="space-y-2">
        {items.map((it, i) => (
          <li key={i} className={`rounded-lg px-3 py-2 text-sm ${cls}`}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

function ResumeInner() {
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState("Software Engineer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeAnalysis | null>(null);

  async function submit() {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await analyzeResume(file, role));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const a = result?.analysis;

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="text-3xl font-bold">Resume Review</h1>
      <p className="mt-1 text-gray-400">
        Upload a PDF resume. The Resume agent returns an ATS score, a skill gap, and
        quantified bullet rewrites tailored to your target role.
      </p>

      <div className="card mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm">Target role</label>
          <input className="input" value={role} onChange={(e) => setRole(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-sm">Resume (PDF, max 5 MB)</label>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-300 file:mr-4 file:rounded-lg file:border-0 file:bg-brand file:px-4 file:py-2 file:text-white hover:file:bg-brand-dark"
          />
        </div>
        <button className="btn-primary" onClick={submit} disabled={!file || busy}>
          {busy ? "Analyzing…" : "Analyze resume"}
        </button>
        {error && <p className="rounded bg-red-500/10 p-2 text-sm text-red-300">{error}</p>}
      </div>

      {busy && (
        <div className="card mt-6 animate-pulse text-center text-gray-400">
          Reading your resume and scoring it against “{role}”…
        </div>
      )}

      {a && (
        <div className="card mt-6">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
            {typeof a.ats_score === "number" && <ScoreRing score={a.ats_score} />}
            <div className="flex-1">
              {a.summary && <p className="text-sm text-gray-200">{a.summary}</p>}
              <p className="mt-2 text-xs text-gray-500">
                Parsed {result?.characters_extracted} characters · target: {result?.target_role}
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <List title="Strengths" items={a.strengths} tone="good" />
            <List title="Weaknesses" items={a.weaknesses} tone="bad" />
            <List title="Skill gap / missing keywords" items={a.missing_keywords} tone="info" />
          </div>

          {a.bullet_rewrites?.length ? (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-gray-300">Suggested bullet rewrites</h3>
              <div className="space-y-3">
                {a.bullet_rewrites.map((b, i) => (
                  <div key={i} className="rounded-lg border border-white/10 p-3 text-sm">
                    <p className="text-red-300">− {b.before}</p>
                    <p className="mt-1 text-green-300">+ {b.after}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {a.raw && <pre className="mt-4 whitespace-pre-wrap text-xs text-gray-400">{a.raw}</pre>}
        </div>
      )}
    </main>
  );
}

export default function ResumePage() {
  return (
    <RequireAuth>
      <NavBar />
      <ResumeInner />
    </RequireAuth>
  );
}
