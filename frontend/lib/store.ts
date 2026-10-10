"use client";
import {create} from "zustand";import {persist} from "zustand/middleware";
import {Cfg,byId,fits,isCorrect,planMissions} from "./engine";
export type Status="idle"|"active"|"success"|"time"|"abandoned";
type S={cfg:Cfg|null;order:string[];startedAt:number;endedAt:number;simMin:number;idx:number;phase:"clue"|"revealed";
 hints:number;hintsHere:number;spent:number;solved:string[];verified:Record<string,"gps"|"demo">;status:Status;
 start:(c:Cfg)=>boolean;submit:(a:string)=>"ok"|"wrong"|"empty";hint:()=>void;verify:(k:"gps"|"demo")=>void;end:(s:Status)=>void;reset:()=>void};
const INIT={cfg:null,order:[],startedAt:0,endedAt:0,simMin:0,idx:0,phase:"clue" as const,hints:0,hintsHere:0,spent:0,solved:[],verified:{},status:"idle" as Status};
// Time used = real elapsed + minutes simulated by demo verification (kept explicit so demo != real visit).
export const usedSec=(s:S,now:number)=>((s.endedAt||now)-s.startedAt)/1000+s.simMin*60;
export const useGame=create<S>()(persist((set,get)=>({...INIT,
 start:c=>{const order=planMissions(c);if(!order.length)return false;set({...INIT,cfg:c,order,startedAt:Date.now(),status:"active"});return true},
 submit:a=>{const s=get();if(!a.trim())return"empty";if(s.status!=="active"||s.phase!=="clue")return"wrong";
  if(!isCorrect(byId(s.order[s.idx]),a))return"wrong";set({phase:"revealed",solved:[...s.solved,s.order[s.idx]]});return"ok"},
 hint:()=>{const s=get(),d=byId(s.order[s.idx]);if(s.status==="active"&&s.phase==="clue"&&s.hintsHere<d.hints.length)set({hints:s.hints+1,hintsHere:s.hintsHere+1})},
 verify:k=>{const s=get();if(s.status!=="active"||s.phase!=="revealed"||!s.cfg)return;const d=byId(s.order[s.idx]),now=Date.now();
  const simMin=s.simMin+(k==="demo"?d.travelMin+d.visitMin:0),spent=s.spent+d.cost,verified={...s.verified,[d.id]:k};
  const left=s.cfg.minutes-((now-s.startedAt)/1000+simMin*60)/60,next=s.order[s.idx+1];
  if(!next)return set({simMin,spent,verified,status:"success",endedAt:now});
  if(!fits(byId(next),left,s.cfg.budget-spent,s.cfg.buffer))return set({simMin,spent,verified,status:"time",endedAt:now});
  set({simMin,spent,verified,idx:s.idx+1,phase:"clue",hintsHere:0})},
 end:st=>{if(get().status==="active")set({status:st,endedAt:Date.now()})},
 reset:()=>set(INIT)}),
 {name:"layover-v1",version:1,
  merge:(p:any,c)=>p&&typeof p==="object"&&Array.isArray(p.order)&&typeof p.startedAt==="number"?{...c,...p}:c,
  partialize:s=>({cfg:s.cfg,order:s.order,startedAt:s.startedAt,endedAt:s.endedAt,simMin:s.simMin,idx:s.idx,phase:s.phase,hints:s.hints,hintsHere:s.hintsHere,spent:s.spent,solved:s.solved,verified:s.verified,status:s.status})}));
