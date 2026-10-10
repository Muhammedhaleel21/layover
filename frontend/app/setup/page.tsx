"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { useGame } from "@/lib/store";
import { planMissions } from "@/lib/engine";
import { byId } from "@/lib/engine";
const schema = z.object({
  start: z.string().trim().min(2, "Enter a starting point."),
  minutes: z.coerce
    .number()
    .int()
    .min(30, "At least 30 minutes.")
    .max(720, "At most 12 hours."),
  budget: z.coerce
    .number()
    .int()
    .min(0, "Budget cannot be negative.")
    .max(20000),
  buffer: z.coerce
    .number()
    .int()
    .min(10, "Keep a buffer of at least 10 minutes.")
    .max(180),
  mode: z.enum(["walk", "transit", "both"]),
  style: z.enum(["history", "food", "culture", "nature", "mixed"]),
  difficulty: z.enum(["easy", "medium", "challenging"]),
});
const init = {
  start: "Kozhikode Railway Station",
  minutes: "180",
  budget: "300",
  buffer: "30",
  mode: "both",
  style: "mixed",
  difficulty: "medium",
};
export default function Setup() {
  const r = useRouter(),
    start = useGame((s) => s.start);
  const [f, setF] = useState(init);
  const [err, setErr] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const set =
    (k: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setF({ ...f, [k]: e.target.value });
  const parsed = schema.safeParse(f);
  const plan = parsed.success
    ? planMissions({ ...parsed.data, minutes: parsed.data.minutes })
    : [];
  const go = (e: React.FormEvent) => {
    e.preventDefault();
    const p = schema.safeParse(f);
    if (!p.success) {
      const o: Record<string, string> = {};
      p.error.issues.forEach((i) => (o[String(i.path[0])] = i.message));
      setErr(o);
      return;
    }
    setErr({});
    if (!start(p.data)) {
      setMsg(
        "Not enough time or budget for even one mission. Add time, budget, or reduce the buffer.",
      );
      return;
    }
    r.push("/play");
  };
  const L = ({
    k,
    label,
    children,
  }: {
    k: string;
    label: string;
    children: React.ReactNode;
  }) => (
    <div>
      <label htmlFor={k} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      {children}
      {err[k] && (
        <p role="alert" className="mt-1 text-sm text-amber">
          {err[k]}
        </p>
      )}
    </div>
  );
  return (
    <main className="mx-auto max-w-2xl px-5 py-10">
      <h1 className="font-display text-3xl">Set up your layover</h1>
      <p className="mt-2 text-mist">
        Pre-filled with the Kozhikode sample. Edit anything.
      </p>
      <form onSubmit={go} className="mt-6 grid gap-4 md:grid-cols-2" noValidate>
        <div className="md:col-span-2">
          <L k="start" label="Starting location">
            <input
              id="start"
              className="field"
              value={f.start}
              onChange={set("start")}
            />
          </L>
        </div>
        <L k="minutes" label="Available time (minutes)">
          <input
            id="minutes"
            inputMode="numeric"
            className="field"
            value={f.minutes}
            onChange={set("minutes")}
          />
        </L>
        <L k="budget" label="Budget (₹)">
          <input
            id="budget"
            inputMode="numeric"
            className="field"
            value={f.budget}
            onChange={set("budget")}
          />
        </L>
        <L k="mode" label="Travel mode">
          <select
            id="mode"
            className="field"
            value={f.mode}
            onChange={set("mode")}
          >
            <option value="walk">Walking</option>
            <option value="transit">Public transport</option>
            <option value="both">Walking + public transport</option>
          </select>
        </L>
        <L k="style" label="Adventure style">
          <select
            id="style"
            className="field"
            value={f.style}
            onChange={set("style")}
          >
            {["history", "food", "culture", "nature", "mixed"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </L>
        <L k="difficulty" label="Difficulty">
          <select
            id="difficulty"
            className="field"
            value={f.difficulty}
            onChange={set("difficulty")}
          >
            {["easy", "medium", "challenging"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </L>
        <L k="buffer" label="Return buffer (minutes, always protected)">
          <input
            id="buffer"
            inputMode="numeric"
            className="field"
            value={f.buffer}
            onChange={set("buffer")}
          />
        </L>
        <section
          aria-live="polite"
          className="md:col-span-2 border border-mist/40 p-4"
        >
          <h2 className="font-semibold">Summary</h2>
          {parsed.success ? (
            <p className="text-mist">
              {parsed.data.start} · {parsed.data.minutes} min · ₹
              {parsed.data.budget} · {plan.length} mission
              {plan.length === 1 ? "" : "s"} fit:{" "}
              {plan.map((i) => byId(i).name).join(" → ") || "none"}. Travel and
              visit times are curated estimates, not live data. Style and
              difficulty are saved but do not change the demo missions yet.
            </p>
          ) : (
            <p className="text-mist">Fix the highlighted fields.</p>
          )}
          {msg && (
            <p role="alert" className="mt-2 text-amber">
              {msg}
            </p>
          )}
        </section>
        <button className="btn-p md:col-span-2" type="submit">
          Generate adventure
        </button>
      </form>
    </main>
  );
}
