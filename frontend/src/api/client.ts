// frontend/src/api/client.ts
import {
  Defect,
  FilterParams,
  TimelineData,
  ImpactData,
  SystemStatus,
  SolveResult,
  ScheduleBlock,
  TrainSlot,
  IncidentRequest,
  IncidentResponse,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const USE_MOCK = false; // 🔴 TURNED OFF: Now using real backend

// --- HELPER MAPPING FUNCTIONS ---

const mapDefect = (backendDefect: any): Defect => {
  const tier = backendDefect.safety_critical 
    ? 'safety-critical' 
    : backendDefect.severity >= 4 
      ? 'high' 
      : backendDefect.status === 'DEFERRED' 
        ? 'deferred' 
        : 'normal';

  return {
    id: backendDefect.id || backendDefect.defect_id,
    department: backendDefect.department.toLowerCase() as 'track' | 'power' | 'signals',
    corridor: backendDefect.corridor_id,
    description: backendDefect.description,
    severity: backendDefect.severity,
    overdueDays: backendDefect.overdue_days,
    trafficImpact: backendDefect.traffic_impact,
    score: backendDefect.score || 0,
    impactScore: backendDefect.score || 0,
    tier,
    status: backendDefect.status.toLowerCase() as any,
    createdAt: backendDefect.created_at,
    updatedAt: backendDefect.scheduled_time || backendDefect.created_at,
    scheduledWeek: backendDefect.scheduled_time ? new Date(backendDefect.scheduled_time).toISOString() : undefined,
    deferReason: backendDefect.deferral_reason || undefined,
  };
};

const mapBlock = (backendBlock: any, defects: Defect[]): ScheduleBlock => {
  const statusMap: Record<string, any> = {
    'PROPOSED': 'proposed', 'PENDING': 'pending', 'APPROVED': 'approved',
    'LOCKED': 'locked', 'EXECUTED': 'executed',
  };

  const associatedDefects = defects.filter(d => backendBlock.defect_source_refs?.includes(d.id));

  return {
    id: backendBlock.id,
    corridor: backendBlock.corridor,
    department: (backendBlock.department || 'track').toLowerCase() as any,
    startTime: backendBlock.start,
    endTime: backendBlock.end,
    duration: Math.round(backendBlock.closure_minutes / 60),
    isCombined: backendBlock.is_combined,
    status: statusMap[backendBlock.status] || 'proposed',
    defects: associatedDefects,
    description: associatedDefects.map(d => d.description).join(', '),
    priority: associatedDefects.length > 0 ? (associatedDefects[0].tier === 'safety-critical' ? 1 : 2) : 3,
    savings: 0, // TODO: Ask backend to provide per-block savings if available
  };
};

// --- API CLIENT ---

export const api = {
  async getDefects(params?: FilterParams): Promise<Defect[]> {
    const queryParams = new URLSearchParams();
    if (params?.department) queryParams.append('department', params.department);
    if (params?.status) queryParams.append('status', params.status);

    const response = await fetch(`${API_BASE_URL}/defects?${queryParams.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch defects');
    const data = await response.json();
    return data.map(mapDefect);
  },

  async getSchedule(week: string): Promise<TimelineData> {
    const response = await fetch(`${API_BASE_URL}/plan`);
    if (!response.ok) throw new Error('Failed to fetch plan');
    const data = await response.json();

    // Fetch defects to map them to blocks properly
    const defects = await this.getDefects(); 
    const blocks: ScheduleBlock[] = data.blocks.map((b: any) => mapBlock(b, defects));
    
    const trainSlots: TrainSlot[] = [
      ...(data.occupancy?.trains || []).map((t: any, i: number) => ({
        id: `T-${i}`, corridor: t.corridor_id || 'A-12', startTime: t.start_time,
        endTime: t.end_time, trainType: 'passenger' as const, trainNumber: t.train_id,
      })),
      ...(data.occupancy?.goods || []).map((g: any, i: number) => ({
        id: `G-${i}`, corridor: g.corridor_id || 'A-12', startTime: g.start_time,
        endTime: g.end_time, trainType: 'goods' as const, trainNumber: g.train_id,
      }))
    ];

    return {
      corridors: [...new Set(blocks.map(b => b.corridor))],
      blocks,
      trainSlots,
      weekStart: week,
      weekEnd: new Date(new Date(week).getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    };
  },

  async reSolve(params?: { keepLocked: boolean }): Promise<SolveResult> {
    const response = await fetch(`${API_BASE_URL}/solve?preserve_approved=${params?.keepLocked ?? true}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to solve schedule');
    const data = await response.json();

    return {
      status: data.solver_used === 'cp-sat' ? 'solved-optimal' : 'solved-moved',
      timeMs: data.solve_time_ms,
      blocksMoved: data.changes_from_previous?.filter((c: any) => c.action === 'moved').map((c: any) => c.block_id) || [],
      blocksAdded: data.changes_from_previous?.filter((c: any) => c.action === 'added').map((c: any) => c.block_id) || [],
      blocksUnchanged: data.changes_from_previous?.filter((c: any) => c.action === 'unchanged').map((c: any) => c.block_id) || [],
      explanation: `Schedule optimized using ${data.solver_used}. ${data.stats?.total_blocks || 0} blocks generated.`,
      confidence: 95,
    };
  },

  async getImpact(week: string): Promise<ImpactData> {
    const response = await fetch(`${API_BASE_URL}/impact`);
    if (!response.ok) throw new Error('Failed to fetch impact metrics');
    const data = await response.json();

    return {
      week,
      totalClosureHoursPlanned: data.closure_hours_baseline,
      totalClosureHoursActual: data.closure_hours_optimized,
      hoursSaved: data.hours_saved,
      savingsPercentage: data.percent_improvement,
      corridorUtilizationBefore: 45, // ⚠️ FALLBACK: See Backend Prompt #3
      corridorUtilizationAfter: 45 + (data.utilization_improvement || 0),
      costSavings: data.hours_saved * 20000, // ⚠️ FALLBACK: See Backend Prompt #3
      breakdown: {
        bundling: data.combined_blocks_count || 0,
        betterTiming: Math.max(0, (data.hours_saved || 0) - (data.combined_blocks_count || 0)),
      },
      weeklyTrend: [ // ⚠️ FALLBACK: See Backend Prompt #3
        { day: 'Mon', planned: 8, actual: 5 }, { day: 'Tue', planned: 6, actual: 4 },
        { day: 'Wed', planned: 7, actual: 5 }, { day: 'Thu', planned: 5, actual: 3 },
        { day: 'Fri', planned: 8, actual: 6 }, { day: 'Sat', planned: 4, actual: 3 },
        { day: 'Sun', planned: 4, actual: 2 },
      ],
      byDepartment: { track: 12, power: 9, signals: 7 }, // ⚠️ FALLBACK: See Backend Prompt #3
    };
  },

  async getStatus(): Promise<SystemStatus> {
    const defects = await this.getDefects();
    const criticalWaiting = defects.filter(d => d.tier === 'safety-critical' && d.status === 'new').length;
    
    return {
      isLive: true,
      lastSolveTime: 12, // ⚠️ FALLBACK: See Backend Prompt #3
      totalTasks: defects.length,
      criticalWaiting,
      conflictsResolved: 47, // ⚠️ FALLBACK
      weekSavings: 14, // ⚠️ FALLBACK
    };
  },

  // --- MUTATIONS ---

  async sendIncident(data: IncidentRequest): Promise<IncidentResponse> {
    const response = await fetch(`${API_BASE_URL}/incident`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `Incident request failed (${response.status})`);
    }
    return response.json();
  },

  async updateDefectStatus(id: string, status: string, reason?: string): Promise<Defect> {
    const params = new URLSearchParams();
    params.append('status', status);
    if (reason) params.append('deferral_reason', reason);
    const response = await fetch(`${API_BASE_URL}/defects/${id}?${params.toString()}`, {
      method: 'PATCH',
    });
    if (!response.ok) throw new Error('Failed to update defect');
    return mapDefect(await response.json());
  },

  async deleteDefect(id: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/defects/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete defect');
    const data = await response.json();
    return data.success;
  },

  async updateBlockStatus(id: string, status: string): Promise<ScheduleBlock> {
    const params = new URLSearchParams();
    params.append('status', status);
    const response = await fetch(`${API_BASE_URL}/blocks/${id}?${params.toString()}`, {
      method: 'PATCH',
    });
    if (!response.ok) throw new Error('Failed to update block');
    const defects = await this.getDefects();
    return mapBlock(await response.json(), defects);
  },

  async scheduleDefect(id: string, weekStart?: string): Promise<void> {
    const defects = await this.getDefects();
    const defect = defects.find(d => d.id === id);
    if (defect) {
      await this.updateDefectStatus(id, 'SCHEDULED');
    }
    await this.reSolve({ keepLocked: true });
  },

  async deferDefect(id: string, reason?: string): Promise<void> {
    await this.updateDefectStatus(id, 'DEFERRED', reason);
  },

  async editDefect(id: string, data: Partial<Defect>): Promise<void> {
    const params = new URLSearchParams();
    if (data.status) params.append('status', data.status);
    if (data.deferReason) params.append('deferral_reason', data.deferReason);
    const response = await fetch(`${API_BASE_URL}/defects/${id}?${params.toString()}`, {
      method: 'PATCH',
    });
    if (!response.ok) throw new Error('Failed to edit defect');
  },

  async createDefect(defectData: any): Promise<Defect> {
    const response = await fetch(`${API_BASE_URL}/defects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(defectData),
    });
    if (!response.ok) throw new Error('Failed to create defect');
    return mapDefect(await response.json());
  },

  async approveBlock(id: string): Promise<void> {
    await this.updateBlockStatus(id, 'APPROVED');
  },

  async lockBlock(id: string): Promise<void> {
    await this.updateBlockStatus(id, 'LOCKED');
  },

  async deleteBlock(id: string): Promise<void> {
    throw new Error('Block deletion not yet implemented on backend');
  },

  async editBlock(id: string, data: Partial<ScheduleBlock>): Promise<void> {
    if (data.status) {
      const statusMap: Record<string, string> = {
        proposed: 'PROPOSED', pending: 'PENDING',
        approved: 'APPROVED', locked: 'LOCKED', executed: 'EXECUTED',
      };
      await this.updateBlockStatus(id, statusMap[data.status] || data.status);
    }
  },

  async injectDefect(defect: any): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/defects/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(defect),
    });
    if (!response.ok) throw new Error('Failed to inject defect');
    const result = await response.json();
    const solveResult = await this.reSolve({ keepLocked: true });
    return { defect: mapDefect(result), blocksMoved: solveResult.blocksMoved };
  },
};