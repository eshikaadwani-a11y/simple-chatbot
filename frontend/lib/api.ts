"use client";

import { supabase } from "./supabase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface AgentEvent {
  type: "token" | "tool" | "route" | "interrupt" | "error" | "done";
  content?: string;
  name?: string;
  route?: string;
  payload?: unknown;
}

/**
 * Stream a chat turn from the agent. Parses the Server-Sent Events response
 * body manually so we can render tokens, tool calls, and routing live.
 */
export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (e: AgentEvent) => void,
): Promise<void> {
  const headers = {
    "Content-Type": "application/json",
    ...(await authHeader()),
  };

  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ thread_id: threadId, message }),
  });

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

    // SSE frames are separated by a blank line.
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
