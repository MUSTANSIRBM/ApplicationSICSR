import { Defect, TimelineData, ImpactData, SystemStatus, InjectionDefect, SolveResult, ScheduleBlock, TrainSlot } from '@/types';

const today = new Date();
const weekStart = new Date(today);
weekStart.setDate(today.getDate() - today.getDay());

const corridors = ['A', 'B', 'C', 'D', 'E'];
const departments: ('track' | 'power' | 'signals')[] = ['track', 'power', 'signals'];

const defectDescriptions: Record<string, string[]> = {
  track: [
    'Crack detected at KM 42',
    'Rail wear at curve section',
    'Frog failure at junction',
    'Missing fish plates',
    'Track misalignment',
  ],
  power: [
    'Overhead wire wear',
    'Transformer overheating',
    'Circuit breaker failure',
    'Insulator crack',
    'Voltage fluctuation',
  ],
  signals: [
    'Signal lamp failure',
    'Circuit relay malfunction',
    'Cable insulation breakdown',
    'Point machine defect',
    'Track circuit failure',
  ],
};

function random(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomDate(start: Date, days: number): string {
  const d = new Date(start);
  d.setDate(d.getDate() + random(0, days));
  return d.toISOString();
}

// Centralized score calculation
export function calculateDefectScore(defect: {
  severity: number;
  overdueDays: number;
  trafficImpact: number;
}): number {
  const MAX_SEVERITY = 100;
  const MAX_OVERDUE_DAYS = 30;
  const MAX_TRAFFIC_IMPACT = 100;
  const severityWeight = 0.5;
  const overdueWeight = 0.3;
  const trafficWeight = 0.2;

  const severityContrib = (defect.severity / MAX_SEVERITY) * severityWeight * 100;
  const overdueContrib = (Math.min(defect.overdueDays, MAX_OVERDUE_DAYS) / MAX_OVERDUE_DAYS) * overdueWeight * 100;
  const trafficContrib = (defect.trafficImpact / MAX_TRAFFIC_IMPACT) * trafficWeight * 100;
  
  return severityContrib + overdueContrib + trafficContrib;
}

function generateDefects(count: number): Defect[] {
  const defects: Defect[] = [];
  const tiers: ('safety-critical' | 'high' | 'normal' | 'deferred')[] = [
    'normal', 'normal', 'normal', 'high', 'high', 'safety-critical',
  ];

  for (let i = 0; i < count; i++) {
    const dept = departments[random(0, 2)];
    const descs = defectDescriptions[dept];
    const tier = tiers[random(0, tiers.length - 1)];
    const severity = tier === 'safety-critical' ? random(85, 100) : random(20, 80);
    const overdueDays = random(0, 14);
    const trafficImpact = random(10, 90);
    
    const defect: Defect = {
      id: `D-${String(i + 1).padStart(3, '0')}`,
      department: dept,
      corridor: corridors[random(0, 4)],
      description: descs[random(0, descs.length - 1)],
      severity,
      overdueDays,
      trafficImpact,
      score: 0, // Will be calculated below
      tier,
      status: ['new', 'scored', 'scheduled', 'approved'][random(0, 3)] as any,
      createdAt: randomDate(new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000), 30),
      availableSlots: [],
      bundleSuggestions: [],
    };
    
    // Calculate score properly
    defect.score = calculateDefectScore(defect);
    defects.push(defect);
  }
  return defects;
}

function generateBlocks(defects: Defect[]): ScheduleBlock[] {
  const blocks: ScheduleBlock[] = [];
  
  const shuffled = [...defects].sort(() => Math.random() - 0.5);
  const chunked = [];
  for (let i = 0; i < shuffled.length; i += 2) {
    chunked.push(shuffled.slice(i, i + 2));
  }

  chunked.forEach((chunk, idx) => {
    const corridor = corridors[idx % corridors.length];
    const startHour = 8 + (idx % 8);
    const startDate = new Date(weekStart);
    startDate.setDate(startDate.getDate() + Math.floor(idx / 8));
    startDate.setHours(startHour, 0, 0, 0);

    const duration = random(1, 4);
    const endDate = new Date(startDate);
    endDate.setHours(endDate.getHours() + duration);

    const depts = chunk.map(d => d.department);
    const isCombined = depts.length > 1 && depts.every(d => d === depts[0]);

    blocks.push({
      id: `B-${String(idx + 1).padStart(3, '0')}`,
      corridor,
      department: isCombined ? 'combined' : depts[0],
      startTime: startDate.toISOString(),
      endTime: endDate.toISOString(),
      defects: chunk,
      status: ['proposed', 'approved', 'locked'][random(0, 2)] as any,
      isCombined,
      combinedDepartments: isCombined ? depts : undefined,
      duration,
      savings: isCombined ? duration * 0.6 : 0,
    });
  });

  return blocks;
}

function generateTrainSlots(): TrainSlot[] {
  const slots: TrainSlot[] = [];
  const trainNumbers = ['12001', '12002', '12907', '12908', '12259', '12260'];
  
  for (let day = 0; day < 7; day++) {
    for (let i = 0; i < 3; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + day);
      d.setHours(6 + i * 4, 0, 0, 0);
      
      slots.push({
        id: `T-${String(slots.length + 1).padStart(3, '0')}`,
        corridor: corridors[slots.length % 5],
        startTime: d.toISOString(),
        endTime: new Date(d.getTime() + 2 * 60 * 60 * 1000).toISOString(),
        trainType: i % 2 === 0 ? 'passenger' : 'goods',
        trainNumber: trainNumbers[slots.length % trainNumbers.length],
      });
    }
  }
  return slots;
}

// Initial data
let currentDefects = generateDefects(30);
let currentBlocks = generateBlocks(currentDefects);

export const mockDefects = currentDefects;
export const mockBlocks = currentBlocks;
export const mockTrainSlots = generateTrainSlots();

export const mockTimelineData: TimelineData = {
  corridors,
  blocks: currentBlocks,
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
  blocksAdded: [`B-${String(currentBlocks.length + 1).padStart(3, '0')}`],
  blocksUnchanged: ['B-001', 'B-003', 'B-005', 'B-007', 'B-009', 'B-011', 'B-013', 'B-015'],
  explanation: `Emergency ${defect.department} defect injected. Re-solved with 2 blocks moved to accommodate the new priority task.`,
  confidence: 94,
});

// Mutation functions
export const getCurrentDefects = () => currentDefects;
export const getCurrentBlocks = () => currentBlocks;

export const updateMockDefects = (newDefects: Defect[]) => {
  currentDefects = newDefects;
  currentBlocks = generateBlocks(currentDefects);
};

export const updateMockBlocks = (newBlocks: ScheduleBlock[]) => {
  currentBlocks = newBlocks;
};

export const deleteMockDefect = (id: string): boolean => {
  const index = currentDefects.findIndex(d => d.id === id);
  if (index !== -1) {
    currentDefects.splice(index, 1);
    currentBlocks = generateBlocks(currentDefects);
    return true;
  }
  return false;
};

export const scheduleMockDefect = (id: string): Defect | null => {
  const defect = currentDefects.find(d => d.id === id);
  if (defect && defect.status !== 'scheduled') {
    defect.status = 'scheduled';
    defect.score = calculateDefectScore(defect); // Update score
    currentBlocks = generateBlocks(currentDefects);
    return defect;
  }
  return null;
};

export const deferMockDefect = (id: string): Defect | null => {
  const defect = currentDefects.find(d => d.id === id);
  if (defect && defect.status !== 'deferred') {
    defect.status = 'deferred';
    defect.tier = 'deferred';
    defect.score = calculateDefectScore(defect); // Update score
    currentBlocks = generateBlocks(currentDefects);
    return defect;
  }
  return null;
};