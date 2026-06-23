"use client";

import { useMemo, useRef, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { NavBar } from "@/components/NavBar";
import { streamChat, type AgentEvent } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const ROUTE_LABEL: Record<string, string> = {
  tutor: "Tutor Agent",
  quiz: "Quiz Agent",
  roadmap: "Roadmap Agent",
  resume: "Resume Agent",
  interview: "Interview Agent",
  general: "Learning Assistant",
};

function ChatInner() {
  // One LangGraph thread per browser session => short-term memory + recovery.
  const threadId = useMemo(
    () => `thread-${Math.random().toString(36).slice(2)}-${Date.now()}`,
    [],
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setActiveAgent(null);
    setActiveTool(null);

    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    scrollToBottom();

    await streamChat(threadId, text, (e: AgentEvent) => {
      if (e.type === "route" && e.route) setActiveAgent(ROUTE_LABEL[e.route] ?? e.route);
      if (e.type === "tool" && e.name) setActiveTool(e.name);
      if (e.type === "token" && e.content) {
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = {
            role: "assistant",
            content: copy[copy.length - 1].content + e.content,
          };
          return copy;
        });
        scrollToBottom();
      }
      if (e.type === "error") {
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = { role: "assistant", content: `⚠️ ${e.content}` };
          return copy;
        });
      }
      if (e.type === "done") {
        setBusy(false);
        setActiveTool(null);
      }
    });
  }

  return (
    <main className="mx-auto flex h-[calc(100vh-64px)] max-w-3xl flex-col px-4 py-4">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="card mt-10 text-center text-gray-400">
            <p className="text-lg">Ask your AI mentor anything.</p>
            <p className="mt-2 text-sm">
              “Build me an 8-week roadmap to learn backend engineering”, “Quiz me on big-O”,
              “Review my resume”, or “Run a mock interview for a backend role”.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm ${
                m.role === "user" ? "bg-brand text-white" : "border border-white/10 bg-white/5"
              }`}
            >
              {m.content || (busy ? "…" : "")}
            </div>
          </div>
        ))}
      </div>

      {(activeAgent || activeTool) && (
        <div className="mb-2 flex gap-2 text-xs text-gray-400">
          {activeAgent && <span className="rounded-full bg-brand/20 px-2 py-1">🧠 {activeAgent}</span>}
          {activeTool && <span className="rounded-full bg-white/10 px-2 py-1">🔧 {activeTool}</span>}
        </div>
      )}

      <div className="flex gap-2">
        <input
          className="input"
          placeholder="Message your AI mentor…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={busy}
        />
        <button className="btn-primary" onClick={send} disabled={busy}>
          {busy ? "…" : "Send"}
        </button>
      </div>
    </main>
  );
}

export default function ChatPage() {
  return (
    <RequireAuth>
      <NavBar />
      <ChatInner />
    </RequireAuth>
  );
}
