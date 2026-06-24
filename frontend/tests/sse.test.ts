import { describe, expect, it } from "vitest";
import { parseSSEBuffer } from "@/lib/sse";

describe("parseSSEBuffer", () => {
  it("parses complete frames and returns the trailing partial", () => {
    const buffer =
      'event: token\ndata: {"type":"token","content":"He"}\n\n' +
      'event: token\ndata: {"type":"token","content":"llo"}\n\n' +
      "event: token\ndata: {partial";
    const { events, remainder } = parseSSEBuffer(buffer);
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ type: "token", content: "He" });
    expect(events[1].content).toBe("llo");
    expect(remainder).toContain("partial");
  });

  it("ignores malformed JSON frames", () => {
    const { events } = parseSSEBuffer("data: not-json\n\n");
    expect(events).toHaveLength(0);
  });

  it("handles route and interrupt events", () => {
    const buffer =
      'data: {"type":"route","route":"roadmap"}\n\n' +
      'data: {"type":"interrupt","payload":{"message":"Approve?"}}\n\n';
    const { events } = parseSSEBuffer(buffer);
    expect(events[0]).toEqual({ type: "route", route: "roadmap" });
    expect(events[1].payload?.message).toBe("Approve?");
  });

  it("returns empty results for an empty buffer", () => {
    const { events, remainder } = parseSSEBuffer("");
    expect(events).toHaveLength(0);
    expect(remainder).toBe("");
  });
});
