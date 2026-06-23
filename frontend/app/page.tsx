import Link from "next/link";

const FEATURES = [
  { title: "Multi-Agent Orchestration", body: "A supervisor delegates to Tutor, Quiz, Roadmap, Resume, and Interview agents." },
  { title: "Tool-Using ReAct Agents", body: "Agents reason, call tools (search, YouTube, quizzes, roadmaps…), then answer." },
  { title: "Long-Term Memory", body: "Goals, completed topics, quiz history, and preferences persist across sessions." },
  { title: "Streaming Responses", body: "Token-by-token answers over Server-Sent Events for a live feel." },
  { title: "Human-in-the-Loop", body: "Approval checkpoints for high-impact actions via LangGraph interrupts." },
  { title: "Observability", body: "LangSmith tracing for every agent run, tool call, and decision." },
];

const AGENTS = ["Tutor", "Quiz", "Roadmap", "Resume", "Interview", "DSA Mentor"];

export default function Landing() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <nav className="flex items-center justify-between">
        <span className="text-xl font-bold">🧠 LearnGraph</span>
        <div className="flex gap-3">
          <Link href="/login" className="btn-ghost">Log in</Link>
          <Link href="/signup" className="btn-primary">Get started</Link>
        </div>
      </nav>

      <section className="mt-20 text-center">
        <p className="mb-3 text-sm uppercase tracking-widest text-brand-light">
          GPT-5 · LangGraph · FastAPI · Next.js · Supabase
        </p>
        <h1 className="mx-auto max-w-3xl text-5xl font-extrabold leading-tight">
          Your multi-agent AI mentor for{" "}
          <span className="text-brand-light">learning anything</span>.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-300">
          Not a chatbot — a true agentic platform. Specialized agents reason, use
          tools, remember your progress, and build a personalized path to your goals.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/signup" className="btn-primary text-lg">Start learning free</Link>
          <Link href="/chat" className="btn-ghost text-lg">Try the agent</Link>
        </div>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {AGENTS.map((a) => (
            <span key={a} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm">
              {a} Agent
            </span>
          ))}
        </div>
      </section>

      <section className="mt-24 grid gap-6 md:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="card">
            <h3 className="text-lg font-semibold text-brand-light">{f.title}</h3>
            <p className="mt-2 text-sm text-gray-300">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="mt-24 border-t border-white/10 py-8 text-center text-sm text-gray-500">
        Built with GPT-5, LangGraph, FastAPI, Next.js, Supabase & Railway.
      </footer>
    </main>
  );
}
