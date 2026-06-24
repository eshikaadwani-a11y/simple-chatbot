/** Display helpers shared by the chat and dashboard views. */

export const ROUTE_LABEL: Record<string, string> = {
  tutor: "Tutor Agent",
  quiz: "Quiz Agent",
  roadmap: "Roadmap Agent",
  resume: "Resume Agent",
  interview: "Interview Agent",
  general: "Learning Assistant",
};

/** Friendly label for a supervisor route, falling back to the raw value. */
export function routeLabel(route: string): string {
  return ROUTE_LABEL[route] ?? route;
}

/** Format a 0..1 ratio as a percentage string, or an em dash when unknown. */
export function formatPercent(ratio: number | null | undefined): string {
  if (ratio == null || Number.isNaN(ratio)) return "—";
  return `${Math.round(ratio * 100)}%`;
}

/** Simple XP -> level curve (100 XP per level). */
export function xpToLevel(xp: number | null | undefined): number {
  return Math.floor((xp ?? 0) / 100) + 1;
}
