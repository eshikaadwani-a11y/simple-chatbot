"use client";

import { supabase } from "./supabase";
import { parseSSEBuffer } from "./sse";
import type { AgentEvent, Analytics, ResumeAnalysis } from "./types";

export type { AgentEvent, Analytics, ResumeAnalysis } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
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
    const { events, remainder } = parseSSEBuffer(buffer);
    buffer = remainder;
    for (const event of events) onEvent(event);
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

export interface AdminAnalytics {
  total_users: number;
  active_users_7d: number;
  ai_requests: number;
  tool_calls: number;
  resume_analyses: number;
  roadmaps_generated: number;
  quiz_attempts: number;
  top_agents: [string, number][];
  top_tools: [string, number][];
  tokens_total: number;
  cost_total_usd: number;
  cost_today_usd: number;
  cost_month_usd: number;
  daily_cost: { date: string; cost: number }[];
}

export async function getAdminAnalytics(): Promise<AdminAnalytics> {
  const res = await fetch(`${API_BASE}/admin/analytics`, { headers: await authHeader() });
  if (res.status === 403) throw new Error("Admin access required.");
  if (!res.ok) throw new Error(`Admin analytics failed (${res.status})`);
  return res.json();
}

/** Upload a PDF resume for ATS analysis by the Resume agent. */
export async function analyzeResume(file: File, targetRole: string): Promise<ResumeAnalysis> {
  const form = new FormData();
  form.append("file", file);
  form.append("target_role", targetRole);

  // Note: do NOT set Content-Type manually; the browser adds the multipart
  // boundary. We only attach the auth header.
  const res = await fetch(`${API_BASE}/resume/analyze`, {
    method: "POST",
    headers: { ...(await authHeader()) },
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Analysis failed (${res.status})`);
  }
  return res.json();
}
