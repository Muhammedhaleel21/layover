import Link from "next/link";import {Clock,KeyRound,MapPin,Unlock,Brain,Compass,ShieldCheck} from "lucide-react";
const steps=[[Clock,"Set your time","Tell us how long you have and what you can spend."],[KeyRound,"Receive a clue","A riddle points to a place. No name, no map."],[MapPin,"Discover the place","Solve it, reveal the story, confirm you arrived."],[Unlock,"Unlock the next chapter","Each discovery opens the next case."]] as const;
const feats=[[Brain,"Mystery Master","Verified clues now. AI-written variations plug in later."],[Clock,"Time-aware","Missions only appear if you can still get back."],[Compass,"Real discovery","Real streets in Kozhikode, curated by hand."],[ShieldCheck,"Safe return","A buffer you set is always protected."]] as const;
export default function Home(){return <main>
<header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5"><span className="font-display text-2xl tracking-wide">LAYOVER</span><a href="#how" className="underline underline-offset-4">How it works</a></header>
<section className="mx-auto grid max-w-6xl gap-10 px-5 py-12 md:grid-cols-2 md:py-20">
<div><h1 className="font-display text-4xl leading-tight md:text-6xl">Your next adventure is hiding in plain sight.</h1>
<p className="mt-5 max-w-prose text-lg text-mist">Solve clues to find real places within the time and budget you have. Explore the unknown. Beat the clock.</p>
<div className="mt-8 flex flex-wrap gap-3"><Link href="/setup" className="btn-p">Start Your Adventure</Link><a href="#how" className="btn-s">See How It Works</a></div></div>
<aside aria-label="Sample clue" className="border border-mist/40 bg-paper p-6 text-deep shadow-[8px_8px_0_#C8472F]">
<p className="text-sm font-semibold text-stamp">Case file LAY-001 · Mission 1</p><h2 className="mt-2 font-display text-2xl">The Quiet Centre</h2>
<p className="mt-3 font-display text-lg italic">“A park wraps around still water in the middle of a busy city. Where do you stand?”</p>
<p className="mt-4 border-t border-deep/30 pt-3 text-sm">Destination: <span className="bg-deep px-2 text-deep select-none">hidden hidden hidden</span></p></aside></section>
<section id="how" className="mx-auto max-w-6xl px-5 py-12"><h2 className="font-display text-3xl">Four steps per case</h2>
<ol className="mt-6 grid gap-4 md:grid-cols-4">{steps.map(([I,t,d],i)=><li key={t} className="border border-mist/40 p-4"><I aria-hidden className="text-amber"/><p className="mt-3 font-semibold">{i+1}. {t}</p><p className="mt-1 text-sm text-mist">{d}</p></li>)}</ol></section>
<section className="mx-auto max-w-6xl px-5 py-12"><h2 className="font-display text-3xl">Built for people on the move</h2>
<ul className="mt-6 grid gap-4 md:grid-cols-2">{feats.map(([I,t,d])=><li key={t} className="flex gap-3"><I aria-hidden className="mt-1 shrink-0 text-amber"/><div><p className="font-semibold">{t}</p><p className="text-mist">{d}</p></div></li>)}</ul></section>
<section className="mx-auto max-w-6xl px-5 py-12"><div className="bg-ink p-6"><h2 className="font-display text-2xl">Sample adventure: Kozhikode, 3 hours, ₹300</h2>
<p className="mt-2 text-mist">Mananchira Square → SM Street → Kozhikode Beach. Missions shrink if your time or budget does.</p></div></section>
<footer className="mx-auto flex max-w-6xl flex-wrap justify-between gap-3 px-5 py-8 text-sm text-mist"><span>LAYOVER · Explore the Unknown. Beat the Clock.</span>
<nav className="flex gap-4"><Link href="/setup" className="underline">Start</Link><a className="underline" href="https://tinkerhub.github.io/layover/">LAYOVER hackathon</a></nav></footer></main>}
