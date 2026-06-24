"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // In production this would report to an error tracker (e.g. Sentry).
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="card max-w-md">
        <h1 className="text-2xl font-bold">Something went wrong</h1>
        <p className="mt-2 text-sm text-gray-400">
          An unexpected error occurred. You can try again — if it persists, please come back later.
        </p>
        <button className="btn-primary mt-6" onClick={reset}>
          Try again
        </button>
      </div>
    </main>
  );
}
