export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center text-gray-400">
      <div className="flex items-center gap-3">
        <span className="h-3 w-3 animate-bounce rounded-full bg-brand-light [animation-delay:-0.3s]" />
        <span className="h-3 w-3 animate-bounce rounded-full bg-brand-light [animation-delay:-0.15s]" />
        <span className="h-3 w-3 animate-bounce rounded-full bg-brand-light" />
      </div>
    </div>
  );
}
