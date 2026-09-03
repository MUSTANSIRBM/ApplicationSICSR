// src/api/client.ts
import { 
  Defect, FilterParams, TimelineData, ImpactData, SystemStatus, 
  InjectionDefect, SolveResult, ScheduleBlock 
} from '@/types';
import { 
  getCurrentDefects, 
  getCurrentBlocks, 
  mockTimelineData, 
  mockImpactData, 
  mockSystemStatus, 
  mockSolveResult,
  deleteMockDefect,
  scheduleMockDefect,
  deferMockDefect,
  editMockDefect,
  deleteMockBlock,
  editMockBlock,
  approveMockBlock,
  lockMockBlock,
  filterDefects,
} from './mockData';

const USE_MOCK = true;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
  async getDefects(params?: FilterParams): Promise<Defect[]> {
    if (USE_MOCK) {
      await delay(300);
      const defects = getCurrentDefects();
      return filterDefects(defects, params);
    }
    const qs = new URLSearchParams(params as any);
    const res = await fetch(`${API_BASE}/defects?${qs}`);
    const data = await res.json();
    return data || [];
  },

  async getDefect(id: string): Promise<Defect> {
    if (USE_MOCK) {
      await delay(200);
      const defect = getCurrentDefects().find(d => d.id === id);
      if (!defect) throw new Error('Defect not found');
      return defect;
    }
    const res = await fetch(`${API_BASE}/defects/${id}`);
    return res.json();
  },

  async deleteDefect(id: string): Promise<boolean> {
    if (USE_MOCK) {
      await delay(300);
      return deleteMockDefect(id);
    }
    const res = await fetch(`${API_BASE}/defects/${id}`, { method: 'DELETE' });
    return res.ok;
  },

  async scheduleDefect(id: string, weekStart?: string): Promise<Defect | null> {
    if (USE_MOCK) {
      await delay(400);
      return scheduleMockDefect(id, weekStart);
    }
    const url = weekStart 
      ? `${API_BASE}/defects/${id}/schedule?week_start=${weekStart}`
      : `${API_BASE}/defects/${id}/schedule`;
    const res = await fetch(url, { method: 'POST' });
    return res.json();
  },

  async deferDefect(id: string, reason?: string): Promise<Defect | null> {
    if (USE_MOCK) {
      await delay(400);
      return deferMockDefect(id, reason);
    }
    const res = await fetch(`${API_BASE}/defects/${id}/defer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    return res.json();
  },

  async editDefect(id: string, data: Partial<Defect>): Promise<Defect> {
    if (USE_MOCK) {
      await delay(300);
      return editMockDefect(id, data);
    }
    const res = await fetch(`${API_BASE}/defects/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async getSchedule(week: string): Promise<TimelineData> {
    if (USE_MOCK) {
      await delay(400);
      const blocks = getCurrentBlocks();
      return { 
        ...mockTimelineData, 
        blocks: blocks || [],
        weekStart: week,
      };
    }
    const res = await fetch(`${API_BASE}/schedule?week=${week}`);
    const data = await res.json();
    return data || { blocks: [], weekStart: week, weekEnd: '', trainSlots: [], corridors: [] };
  },

  async approveBlock(id: string): Promise<ScheduleBlock> {
    if (USE_MOCK) {
      await delay(300);
      const updated = approveMockBlock(id);
      if (!updated) throw new Error('Block not found');
      return updated;
    }
    const res = await fetch(`${API_BASE}/blocks/${id}/approve`, { method: 'POST' });
    return res.json();
  },

  async lockBlock(id: string): Promise<ScheduleBlock> {
    if (USE_MOCK) {
      await delay(300);
      const updated = lockMockBlock(id);
      if (!updated) throw new Error('Block not found');
      return updated;
    }
    const res = await fetch(`${API_BASE}/blocks/${id}/lock`, { method: 'POST' });
    return res.json();
  },

  async deleteBlock(id: string): Promise<boolean> {
    if (USE_MOCK) {
      await delay(300);
      return deleteMockBlock(id);
    }
    const res = await fetch(`${API_BASE}/blocks/${id}`, { method: 'DELETE' });
    return res.ok;
  },

  async editBlock(id: string, data: Partial<ScheduleBlock>): Promise<ScheduleBlock> {
    if (USE_MOCK) {
      await delay(300);
      return editMockBlock(id, data);
    }
    const res = await fetch(`${API_BASE}/blocks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async injectDefect(defect: InjectionDefect): Promise<SolveResult> {
    if (USE_MOCK) {
      await delay(800);
      return mockSolveResult(defect);
    }
    const res = await fetch(`${API_BASE}/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(defect),
    });
    return res.json();
  },

  async reSolve(params?: { keepLocked: boolean }): Promise<SolveResult> {
    if (USE_MOCK) {
      await delay(600);
      return {
        status: 'solved-optimal',
        timeMs: 523,
        blocksMoved: ['B-012'],
        blocksAdded: ['B-099'],
        blocksUnchanged: ['B-001', 'B-003', 'B-005', 'B-007', 'B-009', 'B-011', 'B-015'],
        explanation: 'Re-solved successfully with minimal changes.',
        confidence: 98,
      };
    }
    const res = await fetch(`${API_BASE}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return res.json();
  },

  async getImpact(week: string): Promise<ImpactData> {
    if (USE_MOCK) {
      await delay(300);
      return { ...mockImpactData };
    }
    const res = await fetch(`${API_BASE}/impact?week=${week}`);
    const data = await res.json();
    return data || mockImpactData;
  },

  async getStatus(): Promise<SystemStatus> {
    if (USE_MOCK) {
      await delay(200);
      return { ...mockSystemStatus };
    }
    const res = await fetch(`${API_BASE}/status`);
    const data = await res.json();
    return data || mockSystemStatus;
  },
};