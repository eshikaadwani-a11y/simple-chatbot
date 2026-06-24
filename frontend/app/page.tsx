import Link from "next/link";

const FEATURES = [
  { icon: "🧭", title: "Multi-Agent Orchestration", body: "A supervisor delegates to Tutor, Quiz, Roadmap, Resume, and Interview agents." },
  { icon: "🛠️", title: "Tool-Using ReAct Agents", body: "Agents reason, call tools (search, YouTube, quizzes, roadmaps…), then answer." },
  { icon: "🧠", title: "Long-Term Memory", body: "Goals, completed topics, quiz history, and preferences persist across sessions." },
  { icon: "⚡", title: "Streaming Responses", body: "Token-by-token answers over Server-Sent Events for a live, fast feel." },
  { icon: "🔐", title: "Human-in-the-Loop", body: "Approval checkpoints for high-impact actions via LangGraph interrupts." },
  { icon: "📈", title: "Observability", body: "LangSmith tracing for every agent run, tool call, and routing decision." },
];

const AGENTS = [
  { name: "Tutor", desc: "Explains concepts, generates notes & resources." },
  { name: "Quiz", desc: "Adaptive quizzes, grading, weak-area detection." },
  { name: "Roadmap", desc: "Dependency-ordered learning plans for your goals." },
  { name: "Resume", desc: "ATS scoring, skill-gap analysis, bullet rewrites." },
  { name: "Interview", desc: "Mock interviews with rubrics and follow-ups." },
];

const STEPS = ["Plan", "Route", "Use tools", "Analyze", "Remember", "Respond"];

const STACK = ["GPT-5", "LangGraph", "FastAPI", "Next.js", "Supabase", "Railway", "Vercel", "LangSmith"];

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

      {/* Hero */}
      <section className="mt-20 text-center">
        <p className="mb-3 animate-fade-up text-sm uppercase tracking-widest text-brand-light">
          GPT-5 · LangGraph · FastAPI · Next.js · Supabase
        </p>
        <h1 className="mx-auto max-w-3xl animate-fade-up text-4xl font-extrabold leading-tight sm:text-5xl">
          Your multi-agent AI mentor for{" "}
          <span className="text-brand-light">learning anything</span>.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl animate-fade-up text-base text-gray-300 sm:text-lg">
          Not a chatbot — a true agentic platform. Specialized agents reason, use tools,
          remember your progress, and build a personalized path to your goals.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-4 sm:flex-row">
          <Link href="/signup" className="btn-primary text-lg">Start learning free</Link>
          <Link href="/chat" className="btn-ghost text-lg">Try the agent</Link>
        </div>
      </section>

      {/* Agent flow */}
      <section className="mt-20">
        <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">{s}</span>
              {i < STEPS.length - 1 && <span className="text-brand-light">→</span>}
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-xs text-gray-500">
          The LangGraph workflow every request flows through.
        </p>
      </section>

      {/* Agents */}
      <section className="mt-20">
        <h2 className="text-center text-2xl font-bold">A team of specialized agents</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a) => (
            <div key={a.name} className="card transition hover:border-brand/50 hover:bg-white/10">
              <h3 className="text-lg font-semibold text-brand-light">{a.name} Agent</h3>
              <p className="mt-2 text-sm text-gray-300">{a.desc}</p>
            </div>
          ))}
          <div className="card flex items-center justify-center text-center text-sm text-gray-400">
            …all coordinated by a <span className="mx-1 font-semibold text-brand-light">Supervisor</span>.
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mt-20">
        <h2 className="text-center text-2xl font-bold">Built like a production system</h2>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card">
              <div className="text-2xl">{f.icon}</div>
              <h3 className="mt-2 text-lg font-semibold text-brand-light">{f.title}</h3>
              <p className="mt-2 text-sm text-gray-300">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech stack */}
      <section className="mt-20 text-center">
        <h2 className="text-2xl font-bold">Tech stack</h2>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {STACK.map((t) => (
            <span key={t} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm">
              {t}
            </span>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mt-20">
        <div className="card bg-gradient-to-br from-brand/20 to-transparent text-center">
          <h2 className="text-2xl font-bold">Ready to learn faster?</h2>
          <p className="mt-2 text-gray-300">Create an account and let the agents build your path.</p>
          <Link href="/signup" className="btn-primary mt-6 inline-block text-lg">Get started</Link>
        </div>
      </section>

      <footer className="mt-20 border-t border-white/10 py-8 text-center text-sm text-gray-500">
        Built with GPT-5, LangGraph, FastAPI, Next.js, Supabase &amp; Railway.
      </footer>
    </main>
  );
}
