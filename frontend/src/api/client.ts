// frontend/src/api/client.ts
import { 
  Defect, FilterParams, TimelineData, ImpactData, SystemStatus, 
  InjectionDefect, SolveResult, ScheduleBlock 
} from '@/types';
import { getCurrentDefects, getCurrentBlocks, mockTimelineData, mockImpactData, mockSystemStatus, mockSolveResult } from './mockData';

const USE_MOCK = true;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const api = {
  // Defects
  async getDefects(params?: FilterParams): Promise<Defect[]> {
  if (USE_MOCK) {
    await delay(300);
    let data = [...getCurrentDefects()];
    if (params?.department) data = data.filter(d => d.department === params.department);
    if (params?.corridor) data = data.filter(d => d.corridor === params.corridor);
    if (params?.tier) data = data.filter(d => d.tier === params.tier);
    if (params?.search) {
      const s = params.search.toLowerCase();
      data = data.filter(d => d.description.toLowerCase().includes(s));
    }
    return data;
  }
    const qs = new URLSearchParams(params as any);
    const res = await fetch(`${API_BASE}/defects?${qs}`);
    return res.json();
  },

  async getDefect(id: string): Promise<Defect> {
    if (USE_MOCK) {
      await delay(200);
      const defect = mockDefects.find(d => d.id === id);
      if (!defect) throw new Error('Defect not found');
      return defect;
    }
    const res = await fetch(`${API_BASE}/defects/${id}`);
    return res.json();
  },

  async scoreDefect(id: string): Promise<Defect> {
    if (USE_MOCK) {
      await delay(400);
      const defect = mockDefects.find(d => d.id === id);
      if (!defect) throw new Error('Defect not found');
      return { ...defect, status: 'scored' };
    }
    const res = await fetch(`${API_BASE}/defects/${id}/score`, { method: 'POST' });
    return res.json();
  },

  // Schedule
  async getSchedule(week: string): Promise<TimelineData> {
  if (USE_MOCK) {
    await delay(400);
    return { 
      ...mockTimelineData, 
      blocks: getCurrentBlocks(),
      weekStart: week,
    };
  }
    const res = await fetch(`${API_BASE}/schedule?week=${week}`);
    return res.json();
  },

  async approveBlock(id: string): Promise<ScheduleBlock> {
    if (USE_MOCK) {
      await delay(300);
      const block = mockTimelineData.blocks.find(b => b.id === id);
      if (!block) throw new Error('Block not found');
      return { ...block, status: 'approved' };
    }
    const res = await fetch(`${API_BASE}/blocks/${id}/approve`, { method: 'POST' });
    return res.json();
  },

  async lockBlock(id: string): Promise<ScheduleBlock> {
    if (USE_MOCK) {
      await delay(300);
      const block = mockTimelineData.blocks.find(b => b.id === id);
      if (!block) throw new Error('Block not found');
      return { ...block, status: 'locked' };
    }
    const res = await fetch(`${API_BASE}/blocks/${id}/lock`, { method: 'POST' });
    return res.json();
  },

  // Live
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

  // Impact
  async getImpact(week: string): Promise<ImpactData> {
    if (USE_MOCK) {
      await delay(300);
      return { ...mockImpactData };
    }
    const res = await fetch(`${API_BASE}/impact?week=${week}`);
    return res.json();
  },

  // Status
  async getStatus(): Promise<SystemStatus> {
    if (USE_MOCK) {
      await delay(200);
      return { ...mockSystemStatus };
    }
    const res = await fetch(`${API_BASE}/status`);
    return res.json();
  },
};

