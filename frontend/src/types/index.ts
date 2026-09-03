// frontend/src/types/index.ts
export interface Defect {
  id: string;
  department: 'track' | 'power' | 'signals';
  corridor: string;
  description: string;
  severity: number;
  overdueDays: number;
  trafficImpact: number;
  score: number;
  tier: 'safety-critical' | 'high' | 'normal' | 'deferred';
  status: 'new' | 'scored' | 'scheduled' | 'approved' | 'completed';
  availableSlots?: TimeSlot[];
  bundleSuggestions?: Defect[];
  createdAt: string;
}

export interface TimeSlot {
  corridor: string;
  startTime: string;
  endTime: string;
  available: boolean;
}

export interface ScheduleBlock {
  id: string;
  corridor: string;
  department: 'track' | 'power' | 'signals' | 'combined';
  startTime: string;
  endTime: string;
  defects: Defect[];
  status: 'proposed' | 'approved' | 'locked' | 'executed';
  isCombined: boolean;
  combinedDepartments?: string[];
  duration: number;
  savings: number;
}

export interface TrainSlot {
  id: string;
  corridor: string;
  startTime: string;
  endTime: string;
  trainType: 'passenger' | 'goods';
  trainNumber: string;
}

export interface TimelineData {
  corridors: string[];
  blocks: ScheduleBlock[];
  trainSlots: TrainSlot[];
  weekStart: string;
  weekEnd: string;
}

export interface InjectionDefect {
  department: 'track' | 'power' | 'signals';
  corridor: string;
  description: string;
  severity: number;
  isEmergency: boolean;
}

export interface SolveResult {
  status: 'solved-optimal' | 'solved-moved' | 'escalated';
  timeMs: number;
  blocksMoved: string[];
  blocksAdded: string[];
  blocksUnchanged: string[];
  explanation: string;
  confidence: number;
}

export interface ImpactData {
  week: string;
  totalClosureHoursPlanned: number;
  totalClosureHoursActual: number;
  hoursSaved: number;
  savingsPercentage: number;
  corridorUtilizationBefore: number;
  corridorUtilizationAfter: number;
  costSavings: number;
  breakdown: {
    bundling: number;
    betterTiming: number;
  };
  weeklyTrend: {
    day: string;
    planned: number;
    actual: number;
  }[];
  byDepartment: {
    track: number;
    power: number;
    signals: number;
  };
}

export interface SystemStatus {
  isLive: boolean;
  lastSolveTime: number;
  totalTasks: number;
  criticalWaiting: number;
  conflictsResolved: number;
  weekSavings: number;
}

export interface FilterParams {
  department?: 'track' | 'power' | 'signals';
  corridor?: string;
  tier?: 'safety-critical' | 'high' | 'normal' | 'deferred';
  search?: string;
}

export type Department = 'track' | 'power' | 'signals';
export type Tier = 'safety-critical' | 'high' | 'normal' | 'deferred';
export type BlockStatus = 'proposed' | 'approved' | 'locked' | 'executed';