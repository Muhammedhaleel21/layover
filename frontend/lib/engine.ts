import { DESTS, Dest } from "./data";
export type Cfg = {
  start: string;
  minutes: number;
  budget: number;
  buffer: number;
  mode: string;
  style: string;
  difficulty: string;
};
export const norm = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
export const isCorrect = (d: Dest, input: string) =>
  d.answers.map(norm).includes(norm(input));
// Can mission fit given remaining time/budget AND still protect the return buffer?
export const fits = (
  d: Dest,
  remMin: number,
  remBudget: number,
  buffer: number,
) =>
  d.travelMin + d.visitMin + d.returnMin + buffer <= remMin &&
  d.cost <= remBudget;
// Greedy in curated order; stops at first mission that does not fit (no silent overrun).
export function planMissions(cfg: Cfg): string[] {
  let t = 0,
    c = 0;
  const out: string[] = [];
  for (const d of DESTS) {
    if (!fits(d, cfg.minutes - t, cfg.budget - c, cfg.buffer)) break;
    out.push(d.id);
    t += d.travelMin + d.visitMin;
    c += d.cost;
  }
  return out;
}
export const byId = (id: string) => DESTS.find((d) => d.id === id)!;
export function haversineM(a: number, b: number, c: number, d: number) {
  const r = (x: number) => (x * Math.PI) / 180,
    R = 6371000;
  const h =
    Math.sin(r(c - a) / 2) ** 2 +
    Math.cos(r(a)) * Math.cos(r(c)) * Math.sin(r(d - b) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
export type Score = {
  solved: number;
  verified: number;
  hints: number;
  budgetBonus: number;
  timeBonus: number;
  total: number;
};
export function score(
  solved: number,
  verified: number,
  hints: number,
  budgetLeft: number,
  onTime: boolean,
): Score {
  const budgetBonus = Math.min(30, Math.floor(Math.max(0, budgetLeft) / 10)),
    timeBonus = onTime ? 50 : 0;
  const total = Math.max(
    0,
    solved * 100 + verified * 50 - hints * 15 + budgetBonus + timeBonus,
  );
  return { solved, verified, hints, budgetBonus, timeBonus, total };
}
export const rank = (s: number) =>
  s >= 450
    ? "Master Detective"
    : s >= 300
      ? "Field Agent"
      : s >= 150
        ? "Rookie Sleuth"
        : "Wanderer";
export const mmss = (sec: number) => {
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
