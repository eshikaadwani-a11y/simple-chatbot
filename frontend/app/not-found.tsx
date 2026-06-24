import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="card max-w-md">
        <p className="text-5xl font-extrabold text-brand-light">404</p>
        <h1 className="mt-3 text-xl font-bold">Page not found</h1>
        <p className="mt-2 text-sm text-gray-400">
          The page you’re looking for doesn’t exist or has moved.
        </p>
        <Link href="/" className="btn-primary mt-6 inline-block">
          Back to home
        </Link>
      </div>
    </main>
  );
}
