"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

export function NavBar() {
  const { user, signOut } = useAuth();
  const router = useRouter();

  return (
    <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
      <Link href="/dashboard" className="text-lg font-bold">🧠 LearnGraph</Link>
      <nav className="flex items-center gap-4 text-sm">
        <Link href="/dashboard" className="hover:text-brand-light">Dashboard</Link>
        <Link href="/chat" className="hover:text-brand-light">AI Mentor</Link>
        <span className="hidden text-gray-500 sm:inline">{user?.email}</span>
        <button
          className="btn-ghost"
          onClick={async () => {
            await signOut();
            router.replace("/login");
          }}
        >
          Sign out
        </button>
      </nav>
    </header>
  );
}
