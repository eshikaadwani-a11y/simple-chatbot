"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RequireAuth } from "@/components/RequireAuth";
import { NavBar } from "@/components/NavBar";
import { getAnalytics, type Analytics } from "@/lib/api";

function Stat({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="card text-center">
      <div className={`text-4xl font-extrabold ${accent ? "text-brand-light" : ""}`}>{value}</div>
      <div className="mt-1 text-sm text-gray-400">{label}</div>
    </div>
  );
}

function DashboardInner() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics().then(setData).catch((e) => setError(String(e)));
  }, []);

  const chartData = [
    { name: "XP", value: data?.xp ?? 0 },
    { name: "Topics", value: data?.topics_completed ?? 0 },
    { name: "Quizzes", value: data?.quizzes_taken ?? 0 },
    { name: "Streak", value: data?.streak_days ?? 0 },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-3xl font-bold">Your Learning Dashboard</h1>
      <p className="mt-1 text-gray-400">Track XP, streaks, mastery, and weak areas.</p>

      {error && <p className="mt-4 rounded bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total XP" value={data?.xp ?? "—"} accent />
        <Stat label="Day Streak 🔥" value={data?.streak_days ?? "—"} />
        <Stat label="Topics Completed" value={data?.topics_completed ?? "—"} />
        <Stat
          label="Avg Quiz Score"
          value={data?.average_quiz_score != null ? `${Math.round(data.average_quiz_score * 100)}%` : "—"}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold">Progress overview</h2>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip contentStyle={{ background: "#1f1f2e", border: "none", borderRadius: 8 }} />
                <Bar dataKey="value" fill="#a78bfa" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h2 className="mb-3 text-lg font-semibold">Focus areas</h2>
          {data?.weak_areas?.length ? (
            <ul className="space-y-2">
              {data.weak_areas.map((w) => (
                <li key={w} className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-200">{w}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No weak areas detected yet. Take a quiz!</p>
          )}

          <h2 className="mb-3 mt-6 text-lg font-semibold">Your goals</h2>
          {data?.goals?.length ? (
            <ul className="space-y-2">
              {data.goals.map((g) => (
                <li key={g} className="rounded-lg bg-white/5 px-3 py-2 text-sm">{g}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">Tell the AI mentor your goals to see them here.</p>
          )}
        </div>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <NavBar />
      <DashboardInner />
    </RequireAuth>
  );
}
