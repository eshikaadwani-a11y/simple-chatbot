"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <form onSubmit={handleSubmit} className="card w-full max-w-md">
        <h1 className="text-2xl font-bold">Welcome back</h1>
        <p className="mt-1 text-sm text-gray-400">Log in to continue learning.</p>

        {error && <p className="mt-4 rounded bg-red-500/10 p-2 text-sm text-red-300">{error}</p>}

        <label className="mt-6 block text-sm">Email</label>
        <input className="input mt-1" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} required />

        <label className="mt-4 block text-sm">Password</label>
        <input className="input mt-1" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} required />

        <button className="btn-primary mt-6 w-full" disabled={loading}>
          {loading ? "Signing in…" : "Log in"}
        </button>

        <p className="mt-4 text-center text-sm text-gray-400">
          No account? <Link href="/signup" className="text-brand-light">Sign up</Link>
        </p>
      </form>
    </main>
  );
}
