// src/api/mockData.ts
import { Defect, ScheduleBlock, TimelineData, ImpactData, SystemStatus, InjectionDefect, SolveResult, FilterParams, TrainSlot } from '@/types';

// ============================================
// HELPER FUNCTIONS
// ============================================
export const calculateDefectScore = (defect: Partial<Defect>): number => {
  let score = 0;
  if (defect.tier === 'safety-critical') score += 40;
  else if (defect.tier === 'high') score += 30;
  else if (defect.tier === 'normal') score += 20;
  else score += 10;
  score += Math.min(defect.impactScore || defect.severity || 0, 60);
  return Math.min(score, 100);
};

// Generate mock defects
function generateDefects(count: number): Defect[] {
  const departments: Array<'track' | 'power' | 'signals'> = ['track', 'power', 'signals'];
  const corridors = ['A-12', 'B-07', 'C-04', 'D-09', 'E-15', 'F-03'];
  const tiers: Array<'safety-critical' | 'high' | 'normal' | 'deferred'> = ['safety-critical', 'high', 'normal', 'deferred'];
  const statuses: Array<'new' | 'scored' | 'scheduled' | 'approved' | 'completed' | 'deferred'> = ['new', 'new', 'new', 'scheduled', 'deferred'];
  const descriptions = [
    'Track misalignment detected',
    'Power supply fluctuation in corridor',
    'Signal failure at junction',
    'Track wear beyond threshold',
    'Communication system failure',
    'Rail crack detected',
    'Switch mechanism malfunction',
    'Circuit breaker tripped',
    'Sensor calibration required',
    'Structural integrity issue'
  ];

  const defects: Defect[] = [];
  for (let i = 0; i < count; i++) {
    const tier = tiers[Math.floor(Math.random() * tiers.length)];
    const severity = Math.floor(Math.random() * 80) + 20;
    const impactScore = Math.floor(Math.random() * 80) + 20;
    defects.push({
      id: `D-${String(i + 1).padStart(3, '0')}`,
      description: descriptions[Math.floor(Math.random() * descriptions.length)],
      department: departments[Math.floor(Math.random() * departments.length)],
      corridor: corridors[Math.floor(Math.random() * corridors.length)],
      tier: tier,
      severity: severity,
      impactScore: impactScore,
      score: calculateDefectScore({ tier, impactScore, severity }),
      status: statuses[Math.floor(Math.random() * statuses.length)],
      createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      overdueDays: Math.floor(Math.random() * 30),
      trafficImpact: Math.floor(Math.random() * 100),
      scheduledWeek: Math.random() > 0.7 ? new Date(Date.now() + Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString() : undefined,
    });
  }
  return defects;
}

// Generate blocks from defects
function generateBlocks(defects: Defect[]): ScheduleBlock[] {
  const scheduledDefects = defects.filter(d => d.status === 'scheduled' || d.status === 'approved');
  return scheduledDefects.map((defect, index) => {
    const startTime = new Date();
    startTime.setHours(8 + (index % 8), 0, 0, 0);
    const endTime = new Date(startTime);
    endTime.setHours(startTime.getHours() + 2 + Math.floor(Math.random() * 4));
    
    return {
      id: `B-${String(index + 1).padStart(3, '0')}`,
      corridor: defect.corridor || 'A-12',
      department: defect.department,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      defects: [defect],
      status: 'proposed',
      isCombined: Math.random() > 0.7,
      duration: Math.floor(Math.random() * 4) + 2,
      savings: Math.random() > 0.7 ? Math.floor(Math.random() * 3) + 1 : 0,
      description: defect.description,
      weekStart: new Date().toISOString(),
      priority: defect.tier === 'safety-critical' ? 1 : defect.tier === 'high' ? 2 : 3,
      assignedTo: defect.department,
      defectId: defect.id,
    };
  });
}

// Generate train slots
function generateTrainSlots(): TrainSlot[] {
  const slots: TrainSlot[] = [];
  const corridors = ['A-12', 'B-07', 'C-04', 'D-09', 'E-15', 'F-03'];
  const trainTypes: Array<'passenger' | 'goods'> = ['passenger', 'goods'];
  let idCounter = 1;
  
  for (let i = 0; i < 20; i++) {
    slots.push({
      id: `T-${String(idCounter++).padStart(3, '0')}`,
      corridor: corridors[Math.floor(Math.random() * corridors.length)],
      startTime: new Date().toISOString(),
      endTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      trainType: trainTypes[Math.floor(Math.random() * trainTypes.length)],
      trainNumber: `TR-${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`,
    });
  }
  return slots;
}

// Initial data
const weekStart = new Date();
weekStart.setDate(weekStart.getDate() - weekStart.getDay() + 1);

const corridors = ['A-12', 'B-07', 'C-04', 'D-09', 'E-15', 'F-03'];

// State
let mockDefects: Defect[] = generateDefects(30);
let mockBlocks: ScheduleBlock[] = generateBlocks(mockDefects);
const mockTrainSlots: TrainSlot[] = generateTrainSlots();

// Mock data exports
export const mockTimelineData: TimelineData = {
  corridors,
  blocks: mockBlocks,
  trainSlots: mockTrainSlots,
  weekStart: weekStart.toISOString(),
  weekEnd: new Date(weekStart.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
};

export const mockImpactData: ImpactData = {
  week: 'Week 12, 2024',
  totalClosureHoursPlanned: 42,
  totalClosureHoursActual: 28,
  hoursSaved: 14,
  savingsPercentage: 33.3,
  corridorUtilizationBefore: 45,
  corridorUtilizationAfter: 78,
  costSavings: 280000,
  breakdown: {
    bundling: 10,
    betterTiming: 4,
  },
  weeklyTrend: [
    { day: 'Mon', planned: 8, actual: 5 },
    { day: 'Tue', planned: 6, actual: 4 },
    { day: 'Wed', planned: 7, actual: 5 },
    { day: 'Thu', planned: 5, actual: 3 },
    { day: 'Fri', planned: 8, actual: 6 },
    { day: 'Sat', planned: 4, actual: 3 },
    { day: 'Sun', planned: 4, actual: 2 },
  ],
  byDepartment: {
    track: 12,
    power: 9,
    signals: 7,
  },
};

export const mockSystemStatus: SystemStatus = {
  isLive: true,
  lastSolveTime: 12,
  totalTasks: 30,
  criticalWaiting: 3,
  conflictsResolved: 47,
  weekSavings: 14,
};

export const mockSolveResult = (defect: InjectionDefect): SolveResult => ({
  status: 'solved-moved',
  timeMs: 856,
  blocksMoved: ['B-012', 'B-045', 'B-078'],
  blocksAdded: [`B-${String(mockBlocks.length + 1).padStart(3, '0')}`],
  blocksUnchanged: ['B-001', 'B-003', 'B-005', 'B-007', 'B-009', 'B-011', 'B-013', 'B-015'],
  explanation: `Emergency ${defect.department} defect injected. Re-solved with 2 blocks moved to accommodate the new priority task.`,
  confidence: 94,
});

// ============================================
// GETTER FUNCTIONS
// ============================================
export const getCurrentDefects = (): Defect[] => mockDefects;
export const getCurrentBlocks = (): ScheduleBlock[] => mockBlocks;

// ============================================
// UPDATE FUNCTIONS
// ============================================
export const updateMockDefects = (newDefects: Defect[]) => {
  mockDefects = newDefects;
  mockBlocks = generateBlocks(mockDefects);
};

export const updateMockBlocks = (newBlocks: ScheduleBlock[]) => {
  mockBlocks = newBlocks;
};

// ============================================
// DEFECT MUTATION FUNCTIONS
// ============================================
export const deleteMockDefect = (id: string): boolean => {
  const index = mockDefects.findIndex(d => d.id === id);
  if (index === -1) return false;
  mockDefects.splice(index, 1);
  mockBlocks = generateBlocks(mockDefects);
  return true;
};

export const scheduleMockDefect = (id: string, weekStart?: string): Defect | null => {
  const defect = mockDefects.find(d => d.id === id);
  if (!defect || defect.status === 'scheduled' || defect.status === 'approved') return null;

  const updatedDefect = {
    ...defect,
    status: 'scheduled' as const,
    scheduledWeek: weekStart || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const index = mockDefects.findIndex(d => d.id === id);
  mockDefects[index] = updatedDefect;

  const startTime = new Date();
  startTime.setHours(8 + (mockBlocks.length % 8), 0, 0, 0);
  const endTime = new Date(startTime);
  endTime.setHours(startTime.getHours() + 2 + Math.floor(Math.random() * 4));

  const newBlock: ScheduleBlock = {
    id: `B-${String(mockBlocks.length + 1).padStart(3, '0')}`,
    defectId: id,
    weekStart: weekStart || new Date().toISOString(),
    status: 'proposed',
    description: defect.description,
    duration: Math.floor(Math.random() * 4) + 2,
    priority: defect.tier === 'safety-critical' ? 1 : defect.tier === 'high' ? 2 : 3,
    isCombined: false,
    assignedTo: defect.department,
    updatedAt: new Date().toISOString(),
    corridor: defect.corridor || 'A-12',
    department: defect.department,
    startTime: startTime.toISOString(),
    endTime: endTime.toISOString(),
    defects: [defect],
    savings: 0,
  };
  mockBlocks.push(newBlock);

  return updatedDefect;
};

export const deferMockDefect = (id: string, reason?: string): Defect | null => {
  const defect = mockDefects.find(d => d.id === id);
  if (!defect || defect.status === 'deferred') return null;

  const updatedDefect = {
    ...defect,
    status: 'deferred' as const,
    tier: 'deferred' as const,
    deferReason: reason || 'Deferred by user',
    updatedAt: new Date().toISOString(),
  };

  const index = mockDefects.findIndex(d => d.id === id);
  mockDefects[index] = updatedDefect;
  mockBlocks = mockBlocks.filter(b => b.defectId !== id);

  return updatedDefect;
};

export const editMockDefect = (id: string, data: Partial<Defect>): Defect => {
  const index = mockDefects.findIndex(d => d.id === id);
  if (index === -1) throw new Error('Defect not found');

  const updatedDefect = {
    ...mockDefects[index],
    ...data,
    updatedAt: new Date().toISOString(),
  };
  mockDefects[index] = updatedDefect;
  mockBlocks = generateBlocks(mockDefects);
  return updatedDefect;
};

// ============================================
// BLOCK MUTATION FUNCTIONS
// ============================================
export const approveMockBlock = (id: string): ScheduleBlock | null => {
  const index = mockBlocks.findIndex(b => b.id === id);
  if (index === -1) return null;
  
  mockBlocks[index] = {
    ...mockBlocks[index],
    status: 'approved',
    updatedAt: new Date().toISOString(),
  };
  return mockBlocks[index];
};

export const lockMockBlock = (id: string): ScheduleBlock | null => {
  const index = mockBlocks.findIndex(b => b.id === id);
  if (index === -1) return null;
  
  mockBlocks[index] = {
    ...mockBlocks[index],
    status: 'locked',
    updatedAt: new Date().toISOString(),
  };
  return mockBlocks[index];
};

export const deleteMockBlock = (id: string): boolean => {
  const index = mockBlocks.findIndex(b => b.id === id);
  if (index === -1) return false;
  mockBlocks.splice(index, 1);
  return true;
};

export const editMockBlock = (id: string, data: Partial<ScheduleBlock>): ScheduleBlock => {
  const index = mockBlocks.findIndex(b => b.id === id);
  if (index === -1) throw new Error('Block not found');

  const updatedBlock = {
    ...mockBlocks[index],
    ...data,
    updatedAt: new Date().toISOString(),
  };
  mockBlocks[index] = updatedBlock;
  return updatedBlock;
};

// ============================================
// FILTER FUNCTION
// ============================================
export const filterDefects = (defects: Defect[], params?: FilterParams): Defect[] => {
  if (!defects || !Array.isArray(defects)) return [];
  
  let filtered = [...defects];
  
  if (params?.department) {
    filtered = filtered.filter(d => d.department === params.department);
  }
  if (params?.corridor) {
    filtered = filtered.filter(d => d.corridor === params.corridor);
  }
  if (params?.tier) {
    filtered = filtered.filter(d => d.tier === params.tier);
  }
  if (params?.status) {
    filtered = filtered.filter(d => d.status === params.status);
  }
  if (params?.search && params.search.trim() !== '') {
    const searchTerm = params.search.toLowerCase().trim();
    filtered = filtered.filter(d =>
      d.id?.toLowerCase().includes(searchTerm) ||
      d.description?.toLowerCase().includes(searchTerm) ||
      d.department?.toLowerCase().includes(searchTerm) ||
      d.corridor?.toLowerCase().includes(searchTerm) ||
      d.tier?.toLowerCase().includes(searchTerm)
    );
  }
  
  return filtered;
};