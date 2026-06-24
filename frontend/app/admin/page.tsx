"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RequireAuth } from "@/components/RequireAuth";
import { NavBar } from "@/components/NavBar";
import { getAdminAnalytics, type AdminAnalytics } from "@/lib/api";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card text-center">
      <div className="text-3xl font-extrabold text-brand-light">{value}</div>
      <div className="mt-1 text-xs text-gray-400">{label}</div>
    </div>
  );
}

function Bars({ title, rows }: { title: string; rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      {rows.length === 0 && <p className="text-sm text-gray-400">No data yet.</p>}
      <div className="space-y-2">
        {rows.map(([name, count]) => (
          <div key={name} className="flex items-center gap-3 text-sm">
            <span className="w-32 truncate text-gray-300">{name}</span>
            <div className="h-3 flex-1 rounded bg-white/5">
              <div className="h-3 rounded bg-brand" style={{ width: `${(count / max) * 100}%` }} />
            </div>
            <span className="w-8 text-right text-gray-400">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AdminInner() {
  const [data, setData] = useState<AdminAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminAnalytics().then(setData).catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="card text-center">
          <h1 className="text-xl font-bold">Admin analytics</h1>
          <p className="mt-2 text-sm text-red-300">{error}</p>
          <p className="mt-2 text-xs text-gray-500">
            Set <code>ADMIN_EMAILS</code> on the backend to include your account.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-3xl font-bold">Admin Analytics</h1>
      <p className="mt-1 text-gray-400">Usage, engagement, and LLM cost across the platform.</p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Total users" value={data?.total_users ?? "—"} />
        <Metric label="Active (7d)" value={data?.active_users_7d ?? "—"} />
        <Metric label="AI requests" value={data?.ai_requests ?? "—"} />
        <Metric label="Tool calls" value={data?.tool_calls ?? "—"} />
        <Metric label="Resumes analyzed" value={data?.resume_analyses ?? "—"} />
        <Metric label="Roadmaps" value={data?.roadmaps_generated ?? "—"} />
        <Metric label="Quiz attempts" value={data?.quiz_attempts ?? "—"} />
        <Metric label="Tokens used" value={data?.tokens_total?.toLocaleString() ?? "—"} />
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Metric label="Cost today (USD)" value={`$${data?.cost_today_usd ?? 0}`} />
        <Metric label="Cost this month (USD)" value={`$${data?.cost_month_usd ?? 0}`} />
        <Metric label="Cost all-time (USD)" value={`$${data?.cost_total_usd ?? 0}`} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Bars title="Most-used agents" rows={data?.top_agents ?? []} />
        <Bars title="Most-used tools" rows={data?.top_tools ?? []} />
      </div>

      <div className="card mt-6">
        <h2 className="mb-4 text-lg font-semibold">Daily cost (last 14 days)</h2>
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <AreaChart data={data?.daily_cost ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={11} />
              <YAxis stroke="#9ca3af" fontSize={11} />
              <Tooltip contentStyle={{ background: "#1f1f2e", border: "none", borderRadius: 8 }} />
              <Area type="monotone" dataKey="cost" stroke="#a78bfa" fill="#6d28d9" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <p className="mt-6 text-xs text-gray-500">
        Cost figures use configurable per-model estimates (see <code>app/analytics.py</code>).
      </p>
    </main>
  );
}

export default function AdminPage() {
  return (
    <RequireAuth>
      <NavBar />
      <AdminInner />
    </RequireAuth>
  );
}
