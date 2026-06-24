import { describe, expect, it } from "vitest";
import { formatPercent, routeLabel, xpToLevel } from "@/lib/format";

describe("routeLabel", () => {
  it("maps known routes to friendly labels", () => {
    expect(routeLabel("roadmap")).toBe("Roadmap Agent");
    expect(routeLabel("quiz")).toBe("Quiz Agent");
  });
  it("falls back to the raw value for unknown routes", () => {
    expect(routeLabel("mystery")).toBe("mystery");
  });
});

describe("formatPercent", () => {
  it("formats a ratio as a percentage", () => {
    expect(formatPercent(0.75)).toBe("75%");
    expect(formatPercent(1)).toBe("100%");
  });
  it("returns an em dash for null/NaN", () => {
    expect(formatPercent(null)).toBe("—");
    expect(formatPercent(undefined)).toBe("—");
    expect(formatPercent(NaN)).toBe("—");
  });
});

describe("xpToLevel", () => {
  it("computes level from xp (100 xp per level)", () => {
    expect(xpToLevel(0)).toBe(1);
    expect(xpToLevel(150)).toBe(2);
    expect(xpToLevel(1000)).toBe(11);
    expect(xpToLevel(null)).toBe(1);
  });
});
