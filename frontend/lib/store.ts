"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Cfg, fits, isCorrect, planMissions } from "./engine";
import { Dest, DESTS } from "./data";
import { api, ApiAdventureResponse } from "./api";

export type Status = "idle" | "active" | "success" | "time" | "abandoned";
export type AdventureSource = "local" | "api" | "fallback";

type S = {
  cfg: Cfg | null;
  order: string[];
  startedAt: number;
  endedAt: number;
  simMin: number;
  idx: number;
  phase: "clue" | "revealed";
  hints: number;
  hintsHere: number;
  spent: number;
  solved: string[];
  verified: Record<string, "gps" | "demo">;
  status: Status;
  
  // API integration
  missions: Dest[];
  adventureId: string | null;
  adventureSource: AdventureSource;
  apiWarnings: string[];
  
  start: (c: Cfg) => Promise<boolean>;
  _startLocal: (c: Cfg) => boolean;
  submit: (a: string) => Promise<"ok" | "wrong" | "empty">;
  hint: () => Promise<void>;
  verify: (k: "gps" | "demo") => void;
  end: (s: Status) => void;
  reset: () => void;
  replan: (currentLat: number, currentLng: number) => Promise<boolean>;
};
const INIT = {
  cfg: null,
  order: [],
  startedAt: 0,
  endedAt: 0,
  simMin: 0,
  idx: 0,
  phase: "clue" as const,
  hints: 0,
  hintsHere: 0,
  spent: 0,
  solved: [],
  verified: {},
  status: "idle" as Status,
  
  // API integration  
  missions: [],
  adventureId: null,
  adventureSource: "local" as AdventureSource,
  apiWarnings: [],
};
// Helper to get mission by ID from store missions  
export const byIdFromMissions = (id: string, missions: Dest[]) => missions.find((d) => d.id === id)!;
export const useGame = create<S>()(
  persist(
    (set, get) => ({
      ...INIT,
      
      start: async (c) => {
        try {
          // Try to create adventure via API
          const apiRequest = {
            start: c.start,
            minutes: c.minutes,
            budget: c.budget,
            buffer: c.buffer,
            mode: c.mode as "walk" | "transit" | "both",
            style: c.style as "history" | "food" | "culture" | "nature" | "mixed",
            difficulty: c.difficulty as "easy" | "medium" | "challenging",
          };
          
          const response = await api.createAdventure(apiRequest);
          
          if (response.missions.length === 0) {
            // API returned no missions, use local fallback
            return get()._startLocal(c);
          }
          
          // Success - use API missions
          set({
            ...INIT,
            cfg: c,
            order: response.missions.map(m => m.id),
            missions: response.missions,
            adventureId: response.id,
            adventureSource: response.source === 'ai' ? 'api' : 'fallback',
            apiWarnings: response.warnings,
            startedAt: Date.now(),
            status: "active",
          });
          
          return true;
          
        } catch (error) {
          console.warn('API adventure creation failed, using local mode:', error);
          return get()._startLocal(c);
        }
      },
      
      _startLocal: (c: Cfg) => {
        const order = planMissions(c);
        if (!order.length) return false;
        
        set({
          ...INIT,
          cfg: c,
          order,
          missions: DESTS,
          adventureSource: "local",
          startedAt: Date.now(),
          status: "active",
        });
        
        return true;
      },
      
      submit: async (a) => {
        const s = get();
        if (!a.trim()) return "empty";
        if (s.status !== "active" || s.phase !== "clue") return "wrong";
        
        const mission = s.missions.find(m => m.id === s.order[s.idx]);
        if (!mission) return "wrong";
        
        // Check answer via API if available and answers are hidden
        if (s.adventureId && mission.answers.length === 0) {
          try {
            const response = await api.checkAnswer(s.adventureId, {
              missionId: mission.id,
              answer: a,
            });
            
            if (!response.correct) return "wrong";
          } catch (error) {
            console.warn('API answer check failed, using local logic:', error);
            return "wrong"; // Conservative fallback
          }
        } else {
          // Use local answer checking
          if (!isCorrect(mission, a)) return "wrong";
        }
        
        set({ phase: "revealed", solved: [...s.solved, s.order[s.idx]] });
        return "ok";
      },
      
      hint: async () => {
        const s = get();
        const mission = s.missions.find(m => m.id === s.order[s.idx]);
        if (!mission || s.status !== "active" || s.phase !== "clue") return;
        
        // Get hint via API if available and hints are hidden
        if (s.adventureId && mission.hints.length === 0) {
          try {
            const response = await api.getHint(s.adventureId, {
              missionId: mission.id,
              level: s.hintsHere,
            });
            
            // For now, we just increment the hint counter
            // The actual hint display would need UI changes
            set({ hints: s.hints + 1, hintsHere: s.hintsHere + 1 });
          } catch (error) {
            console.warn('API hint request failed:', error);
          }
        } else {
          // Use local hint logic
          if (s.hintsHere < mission.hints.length) {
            set({ hints: s.hints + 1, hintsHere: s.hintsHere + 1 });
          }
        }
      },
      
      verify: (k) => {
        const s = get();
        if (s.status !== "active" || s.phase !== "revealed" || !s.cfg) return;
        
        const mission = s.missions.find(m => m.id === s.order[s.idx]);
        if (!mission) return;
        
        const now = Date.now();
        const simMin = s.simMin + (k === "demo" ? mission.travelMin + mission.visitMin : 0);
        const spent = s.spent + mission.cost;
        const verified = { ...s.verified, [mission.id]: k };
        
        const left = s.cfg.minutes - ((now - s.startedAt) / 1000 + simMin * 60) / 60;
        const next = s.order[s.idx + 1];
        
        if (!next) {
          return set({
            simMin,
            spent,
            verified,
            status: "success",
            endedAt: now,
          });
        }
        
        const nextMission = s.missions.find(m => m.id === next);
        if (!nextMission || !fits(nextMission, left, s.cfg.budget - spent, s.cfg.buffer)) {
          return set({ simMin, spent, verified, status: "time", endedAt: now });
        }
        
        set({
          simMin,
          spent,
          verified,
          idx: s.idx + 1,
          phase: "clue",
          hintsHere: 0,
        });
      },
      
      replan: async (currentLat: number, currentLng: number) => {
        const s = get();
        if (!s.cfg || !s.adventureId) return false;
        
        try {
          const now = Date.now();
          const usedMinutes = Math.round(((now - s.startedAt) / 1000 + s.simMin * 60) / 60);
          const remainingMinutes = s.cfg.minutes - usedMinutes;
          const remainingBudget = s.cfg.budget - s.spent;
          const completedIds = Object.keys(s.verified);
          
          const response = await api.replanAdventure(s.adventureId, {
            remainingMinutes,
            remainingBudget,
            currentLat,
            currentLng,
            completedIds,
          });
          
          if (response.missions.length === 0) {
            set({ 
              status: "time", 
              endedAt: now,
              apiWarnings: [...s.apiWarnings, "No more missions fit remaining time/budget"]
            });
            return false;
          }
          
          // Update with replanned missions
          set({
            order: response.missions.map(m => m.id),
            missions: [...s.missions, ...response.missions.filter(m => 
              !s.missions.some(existing => existing.id === m.id)
            )],
            idx: 0, // Reset to first new mission
            phase: "clue",
            hintsHere: 0,
            apiWarnings: [...s.apiWarnings, ...response.warnings],
          });
          
          return true;
          
        } catch (error) {
          console.warn('Replan failed:', error);
          return false;
        }
      },
      
      end: (st) => {
        if (get().status === "active") set({ status: st, endedAt: Date.now() });
      },
      
      reset: () => set(INIT),
    }),
    {
      name: "layover-v2", // Increment version for API integration
      version: 2,
      merge: (p: any, c) =>
        p &&
        typeof p === "object" &&
        Array.isArray(p.order) &&
        typeof p.startedAt === "number"
          ? { ...c, ...p }
          : c,
      partialize: (s) => ({
        cfg: s.cfg,
        order: s.order,
        startedAt: s.startedAt,
        endedAt: s.endedAt,
        simMin: s.simMin,
        idx: s.idx,
        phase: s.phase,
        hints: s.hints,
        hintsHere: s.hintsHere,
        spent: s.spent,
        solved: s.solved,
        verified: s.verified,
        status: s.status,
        missions: s.missions,
        adventureId: s.adventureId,
        adventureSource: s.adventureSource,
        apiWarnings: s.apiWarnings,
      }),
    },
  ),
);

// Time used = real elapsed + minutes simulated by demo verification (kept explicit so demo != real visit).
export const usedSec = (s: S, now: number) =>
  ((s.endedAt || now) - s.startedAt) / 1000 + s.simMin * 60;