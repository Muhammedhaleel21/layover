"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Clock,
  Wallet,
  Lightbulb,
  Flag,
  Navigation,
  Check,
  MapPin,
  ShieldCheck,
  FlaskConical,
} from "lucide-react";
import { useGame, usedSec, byIdFromMissions } from "@/lib/store";
import { haversineM, mmss, rank, score } from "@/lib/engine";
import { START } from "@/lib/data";
const RADIUS_M = 200;
function useNow() {
  const [n, setN] = useState(Date.now());
  useEffect(() => {
    const i = setInterval(() => setN(Date.now()), 1000);
    return () => clearInterval(i);
  }, []);
  return n;
}
export default function Play() {
  const r = useRouter(),
    g = useGame(),
    now = useNow(),
    rm = useReducedMotion();
  const [ready, setReady] = useState(false),
    [ans, setAns] = useState(""),
    [fb, setFb] = useState<{ t: "ok" | "bad"; m: string } | null>(null),
    [geo, setGeo] = useState(""),
    [copied, setCopied] = useState(false),
    [replanning, setReplanning] = useState(false);
  useEffect(() => setReady(true), []);
  const remSec = g.cfg ? g.cfg.minutes * 60 - usedSec(g, now) : 0;
  // Time ending: if remaining time is down to the protected buffer, stop offering missions.
  useEffect(() => {
    if (ready && g.status === "active" && g.cfg && remSec <= g.cfg.buffer * 60)
      g.end("time");
  }, [ready, remSec, g.status, g.cfg]);
  if (!ready) return <main className="p-10">Loading your case…</main>;
  if (!g.cfg || g.status === "idle")
    return (
      <main className="mx-auto max-w-xl p-10">
        <h1 className="font-display text-3xl">No active adventure</h1>
        <Link href="/setup" className="btn-p mt-5">
          Start your adventure
        </Link>
      </main>
    );
  const cfg = g.cfg,
    d = g.missions.find(m => m.id === g.order[Math.min(g.idx, g.order.length - 1)]),
    budgetLeft = cfg?.budget ? cfg.budget - g.spent : 0,
    nV = Object.keys(g.verified).length;
  const anim = (o: object) => (rm ? {} : o);
  if (g.status !== "active") {
    const onTime = g.status === "success",
      sc = score(g.solved.length, nV, g.hints, budgetLeft, onTime),
      used = Math.round(usedSec(g, now) / 60);
    const title = {
      success: "Case closed",
      time: "Time to head back",
      abandoned: "Adventure ended early",
    }[g.status];
    const note = {
      success: "You finished every mission with your return buffer intact.",
      time: "The next mission would have cut into your return buffer, so the adventure ended here. Your buffer is protected.",
      abandoned:
        "You ended early. No penalty, and your return buffer is protected.",
    }[g.status];
    const text = `LAYOVER ${title}: ${nV} place${nV === 1 ? "" : "s"} discovered (${
      g.order
        .slice(0, nV)
        .map((i) => g.missions.find(m => m.id === i)?.name || i)
        .join(", ") || "none"
    }), ${used} min, ₹${g.spent} spent, ${g.hints} hint(s), score ${sc.total} (${rank(sc.total)}). Explore the Unknown. Beat the Clock.`;
    return (
      <motion.main
        {...anim({
          initial: { opacity: 0, y: 12 },
          animate: { opacity: 1, y: 0 },
        })}
        className="mx-auto max-w-2xl px-5 py-10"
      >
        <p className="font-semibold text-amber">Case file closed</p>
        <h1 className="font-display text-4xl">{title}</h1>
        <p className="mt-2 text-mist">{note}</p>
        <p className="mt-6 inline-block bg-paper px-4 py-2 font-display text-xl text-deep">
          {rank(sc.total)} · {sc.total} pts
        </p>
        <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
          {[
            ["Missions solved", g.solved.length],
            ["Verified discoveries", nV],
            ["Time spent", `${used} min`],
            ["Budget used / left", `₹${g.spent} / ₹${budgetLeft}`],
            ["Hints used", g.hints],
          ].map(([a, b]) => (
            <div key={String(a)} className="border border-mist/40 p-3">
              <dt className="text-mist">{a}</dt>
              <dd className="text-lg font-semibold">{b}</dd>
            </div>
          ))}
        </dl>
        <section className="mt-6 border border-mist/40 p-4">
          <h2 className="font-semibold">How your score was calculated</h2>
          <ul className="mt-2 text-mist">
            <li>
              Solved: {sc.solved} × 100 = {sc.solved * 100}
            </li>
            <li>
              Verified: {sc.verified} × 50 = {sc.verified * 50}
            </li>
            <li>
              Hints: {sc.hints} × −15 = −{sc.hints * 15}
            </li>
            <li>Budget efficiency: +{sc.budgetBonus}</li>
            <li>Finished within time: +{sc.timeBonus}</li>
          </ul>
        </section>
        <section className="mt-6">
          <h2 className="font-semibold">Recap</h2>
          <ul className="mt-2 list-disc pl-5 text-mist">
            {g.order.slice(0, nV).map((i) => {
              const mission = g.missions.find(m => m.id === i);
              return (
                <li key={i}>
                  {mission?.name || i} —{" "}
                  {g.verified[i] === "gps"
                    ? "verified on location"
                    : "demo-verified (not a real visit)"}
                </li>
              );
            })}
            {nV === 0 && <li>No places discovered this time.</li>}
          </ul>
        </section>
        <div className="mt-8 flex flex-wrap gap-3">
          <button
            className="btn-s"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(text);
                setCopied(true);
              } catch {
                window.prompt("Copy your summary:", text);
              }
            }}
          >
            {copied ? "Copied" : "Copy summary"}
          </button>
          <button
            className="btn-p"
            onClick={() => {
              g.reset();
              r.push("/setup");
            }}
          >
            Start another adventure
          </button>
        </div>
      </motion.main>
    );
  }
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await g.submit(ans);
    if (res === "empty") setFb({ t: "bad", m: "Type an answer first." });
    else if (res === "wrong")
      setFb({
        t: "bad",
        m: "Not it. Reread the clue, or take a hint (costs 15 points).",
      });
    else {
      setFb({ t: "ok", m: "Correct. Destination revealed." });
      setAns("");
    }
  };
  const verifyGps = () => {
    setGeo("");
    if (!navigator.geolocation) {
      setGeo("Location is not available here. Use demo verification below.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => {
        if (!d) return;
        const m = haversineM(
          p.coords.latitude,
          p.coords.longitude,
          d.lat,
          d.lng,
        );
        if (m <= RADIUS_M) {
          setFb(null);
          g.verify("gps");
        } else
          setGeo(
            `You are about ${Math.round(m)} m away. Get within ${RADIUS_M} m and try again.`,
          );
      },
      () =>
        setGeo(
          "Location permission denied. Allow it in browser settings, or use demo verification below.",
        ),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };
  
  const handleReplan = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is required for replanning.");
      return;
    }
    
    setReplanning(true);
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const success = await g.replan(position.coords.latitude, position.coords.longitude);
          if (!success) {
            alert("Unable to replan - no more missions fit your remaining time and budget.");
          }
        } catch (error) {
          alert("Replan failed. Please try again.");
        }
        setReplanning(false);
      },
      () => {
        alert("Location permission denied. Cannot replan without current location.");
        setReplanning(false);
      }
    );
  };
  const bb = d ? `${d.lng - 0.006},${d.lat - 0.004},${d.lng + 0.006},${d.lat + 0.004}` : '';
  return (
    <main className="mx-auto max-w-6xl px-4 py-5">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-mist/30 pb-4">
        <div>
          <p className="text-sm text-amber">
            Case LAY-{g.startedAt.toString().slice(-5)} · {cfg.start}
          </p>
          <h1 className="font-display text-2xl">
            Mission {g.idx + 1} of {g.order.length}: {d?.title}
          </h1>
        </div>
        <dl className="flex gap-5" aria-live="off">
          <div>
            <dt className="flex items-center gap-1 text-xs text-mist">
              <Clock size={14} aria-hidden />
              Left
            </dt>
            <dd className="text-xl font-semibold tabular-nums">
              {mmss(remSec)}
            </dd>
          </div>
          <div>
            <dt className="flex items-center gap-1 text-xs text-mist">
              <Wallet size={14} aria-hidden />
              Budget
            </dt>
            <dd className="text-xl font-semibold">₹{budgetLeft}</dd>
          </div>
          <div>
            <dt className="text-xs text-mist">Solved</dt>
            <dd className="text-xl font-semibold">
              {g.solved.length}/{g.order.length}
            </dd>
          </div>
        </dl>
      </header>
      <div
        className="mt-2 h-2 bg-ink"
        role="progressbar"
        aria-valuenow={nV}
        aria-valuemax={g.order.length}
        aria-label="Missions completed"
      >
        <div
          className="h-2 bg-amber transition-all"
          style={{ width: `${(nV / g.order.length) * 100}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-mist">
        Return buffer {cfg.buffer} min is protected. Travel and visit times are
        curated estimates, not live data. Difficulty: {cfg.difficulty}.
        {g.adventureSource === "api" && " 🤖 AI-curated missions"}
        {g.adventureSource === "fallback" && " 📋 Curated fallback missions"}
        {g.adventureSource === "local" && " 🏠 Offline mode: curated missions"}
        {g.apiWarnings.length > 0 && ` Warnings: ${g.apiWarnings.join(", ")}`}
      </p>
      <div className="mt-5 grid gap-6 lg:grid-cols-[3fr_2fr]">
        <section aria-label="Current mission">
          <AnimatePresence mode="wait">
            <motion.div
              key={g.idx + g.phase}
              {...anim({
                initial: { opacity: 0, y: 10 },
                animate: { opacity: 1, y: 0 },
                exit: { opacity: 0 },
              })}
            >
              {g.phase === "clue" ? (
                <div className="bg-paper p-6 text-deep">
                  <p className="italic">{d?.intro}</p>
                  <p className="mt-4 font-display text-xl leading-snug">
                    {d?.riddle}
                  </p>
                  {g.hintsHere > 0 && d && (
                    <ul className="mt-4 border-l-4 border-stamp pl-3 text-sm">
                      {d.hints.slice(0, g.hintsHere).map((h) => (
                        <li key={h}>Hint: {h}</li>
                      ))}
                    </ul>
                  )}
                  <form
                    onSubmit={submit}
                    className="mt-5 flex flex-col gap-3 sm:flex-row"
                    noValidate
                  >
                    <label htmlFor="ans" className="sr-only">
                      Your answer
                    </label>
                    <input
                      id="ans"
                      value={ans}
                      onChange={(e) => setAns(e.target.value)}
                      placeholder="Where are you headed?"
                      autoComplete="off"
                      className="field flex-1 !bg-white !text-deep"
                    />
                    <button
                      className="btn bg-deep text-paper hover:bg-stamp"
                      type="submit"
                    >
                      Submit answer
                    </button>
                  </form>
                  {fb && (
                    <p
                      role="status"
                      className={`mt-3 font-semibold ${fb.t === "ok" ? "text-green-800" : "text-stamp"}`}
                    >
                      {fb.m}
                    </p>
                  )}
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="btn border border-deep"
                      disabled={!d || g.hintsHere >= d.hints.length}
                      onClick={g.hint}
                    >
                      <Lightbulb size={16} aria-hidden />
                      Get a hint (−15)
                    </button>
                    {g.adventureId && (
                      <button
                        className="btn border border-blue-600 text-blue-600"
                        onClick={handleReplan}
                        disabled={replanning}
                      >
                        {replanning ? "Replanning..." : "Re-plan remaining missions"}
                      </button>
                    )}
                    <button
                      className="btn border border-stamp text-stamp"
                      onClick={() => {
                        if (
                          confirm(
                            "End the adventure? You keep your score so far and your return buffer stays protected.",
                          )
                        )
                          g.end("abandoned");
                      }}
                    >
                      <Flag size={16} aria-hidden />
                      Abandon adventure
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-paper p-6 text-deep">
                  <p className="flex items-center gap-2 font-semibold text-green-800">
                    <Check aria-hidden />
                    Destination revealed
                  </p>
                  <h2 className="mt-1 font-display text-3xl">{d?.name}</h2>
                  <p className="mt-3">{d?.story}</p>
                  <p className="mt-3">
                    <strong>Do here:</strong> {d?.activity}
                  </p>
                  <p className="mt-3 text-sm">
                    Estimates: travel {d?.travelMin} min · visit {d?.visitMin} min
                    · about ₹{d?.cost}
                  </p>
                  <a
                    className="btn-s mt-3 !border-deep !text-deep"
                    target="_blank"
                    rel="noreferrer"
                    href={`https://www.openstreetmap.org/directions?from=${START.lat},${START.lng}&to=${d?.lat},${d?.lng}`}
                  >
                    <Navigation size={16} aria-hidden />
                    Open directions
                  </a>
                  <div className="mt-5 border-t border-deep/30 pt-4">
                    <p className="font-semibold">Confirm discovery</p>
                    <button
                      className="btn bg-deep text-paper hover:bg-stamp mt-2"
                      onClick={verifyGps}
                    >
                      <ShieldCheck size={16} aria-hidden />
                      Verify my location (within {RADIUS_M} m)
                    </button>
                    {geo && (
                      <p role="alert" className="mt-2 text-sm text-stamp">
                        {geo}
                      </p>
                    )}
                    <div className="mt-4 border border-dashed border-stamp p-3">
                      <p className="flex items-center gap-2 text-sm font-semibold text-stamp">
                        <FlaskConical size={16} aria-hidden />
                        Demo mode
                      </p>
                      <p className="text-sm">
                        For judges who cannot travel. This is a simulation, not
                        proof of a real visit. It adds the estimated travel and
                        visit time to your clock.
                      </p>
                      <button
                        className="btn border border-stamp text-stamp mt-2"
                        onClick={() => {
                          setFb(null);
                          g.verify("demo");
                        }}
                      >
                        Confirm (demo verification)
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </section>
        <aside aria-label="Map and journey" className="space-y-4">
          <div className="border border-mist/40">
            {g.phase === "revealed" ? (
              <iframe
                title={`Map of ${d?.name || 'Location'}`}
                className="h-64 w-full"
                loading="lazy"
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${bb}&layer=mapnik&marker=${d?.lat},${d?.lng}`}
              />
            ) : (
              <div className="flex h-64 items-center justify-center p-4 text-center text-mist">
                <MapPin aria-hidden className="mr-2" />
                Location hidden until you solve the clue.
              </div>
            )}
          </div>
          <ol className="space-y-2 text-sm">
            {g.order.map((id, i) => {
              const mission = g.missions.find(m => m.id === id);
              const missionName = mission?.name || `Mission ${i + 1}`;
              
              return (
                <li
                  key={id}
                  className={`border p-2 ${i === g.idx ? "border-amber" : "border-mist/30"}`}
                >
                  {g.verified[id]
                    ? `✓ ${missionName} (${g.verified[id] === "gps" ? "verified" : "demo"})`
                    : i <= g.idx && g.solved.includes(id)
                      ? `${missionName} (solved)`
                      : `Mission ${i + 1}: locked`}
                </li>
              );
            })}
          </ol>
        </aside>
      </div>
    </main>
  );
}
