"use client";

import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Don't hard-crash the whole app at import time on a missing env var; log a
  // clear warning and fall back to harmless placeholders so pages still render
  // (auth calls will fail gracefully and surface an error in the UI instead).
  // eslint-disable-next-line no-console
  console.warn(
    "Supabase env vars missing (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY).",
  );
}

/**
 * Browser Supabase client. Uses the public anon key + the signed-in user's JWT.
 * The service-role key lives only on the backend and is never imported here.
 */
export const supabase = createClient(url ?? "http://localhost:54321", anonKey ?? "public-anon-key", {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
