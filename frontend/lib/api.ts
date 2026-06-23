"use client";

import { supabase } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface AgentEvent {
  type: "token" | "tool" | "route" | "interrupt" | "resumed" | "error" | "done";
  content?: string;
  name?: string;
  route?: string;
  approved?: boolean;
  payload?: { action?: string; route?: string; message?: string };
}

/**
 * Internal: stream and parse a Server-Sent Events response body, dispatching
 * each parsed event to `onEvent`.
 */
async function consumeSSE(res: Response, onEvent: (e: AgentEvent) => void): Promise<void> {
  if (!res.ok || !res.body) {
    onEvent({ type: "error", content: `Request failed (${res.status})` });
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      try {
        onEvent(JSON.parse(dataLine.slice(5).trim()) as AgentEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}

/**
 * Stream a chat turn from the agent. Renders tokens, tool calls, routing, and
 * surfaces human-in-the-loop interrupts live.
 */
export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (e: AgentEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  await consumeSSE(res, onEvent);
}

/** Resume an interrupted (human-in-the-loop) run after approval/rejection. */
export async function resumeChat(
  threadId: string,
  approved: boolean,
  onEvent: (e: AgentEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: JSON.stringify({ thread_id: threadId, approved }),
  });
  await consumeSSE(res, onEvent);
}

export interface Analytics {
  user_id: string;
  xp: number;
  streak_days: number;
  topics_completed: number;
  quizzes_taken: number;
  average_quiz_score: number | null;
  weak_areas: string[];
  goals: string[];
}

export async function getAnalytics(): Promise<Analytics> {
  const res = await fetch(`${API_BASE}/progress/summary`, {
    headers: await authHeader(),
  });
  if (!res.ok) throw new Error(`Analytics failed (${res.status})`);
  return res.json();
}

export async function recordEvent(event: Record<string, unknown>): Promise<void> {
  await fetch(`${API_BASE}/progress/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeader()) },
    body: JSON.stringify(event),
  });
}
