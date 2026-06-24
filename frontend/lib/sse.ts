import type { AgentEvent } from "./types";

/**
 * Parse a Server-Sent Events text buffer into complete events plus any
 * trailing partial frame. Pure and side-effect free so it is easy to unit test.
 *
 * SSE frames are separated by a blank line; we read the `data:` line of each.
 */
export function parseSSEBuffer(buffer: string): {
  events: AgentEvent[];
  remainder: string;
} {
  const frames = buffer.split("\n\n");
  // The final element may be an incomplete frame still being streamed.
  const remainder = frames.pop() ?? "";
  const events: AgentEvent[] = [];

  for (const frame of frames) {
    const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
    if (!dataLine) continue;
    try {
      events.push(JSON.parse(dataLine.slice(5).trim()) as AgentEvent);
    } catch {
      /* ignore malformed frame */
    }
  }
  return { events, remainder };
}
