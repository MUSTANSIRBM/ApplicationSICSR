// src/types/index.ts

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
  status: 'new' | 'scored' | 'scheduled' | 'approved' | 'completed' | 'deferred';
  impactScore?: number; // Alias for score
  scheduledWeek?: string;
  deferReason?: string;
  createdAt: string;
  updatedAt?: string;
  availableSlots?: TimeSlot[];
  bundleSuggestions?: Defect[];
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
  status: 'proposed' | 'pending' | 'approved' | 'locked' | 'executed';
  isCombined: boolean;
  combinedDepartments?: string[];
  duration: number;
  savings: number;
  // Additional properties used in the code
  description?: string;
  weekStart?: string;
  priority?: number;
  assignedTo?: string;
  updatedAt?: string;
  defectId?: string;
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
  status?: 'new' | 'scored' | 'scheduled' | 'approved' | 'completed' | 'deferred';
  search?: string;
}

export type Department = 'track' | 'power' | 'signals';
export type Tier = 'safety-critical' | 'high' | 'normal' | 'deferred';
export type BlockStatus = 'proposed' | 'pending' | 'approved' | 'locked' | 'executed';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'viewer';
  avatar?: string;
  createdAt: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  expiresIn: number;
}

// src/types/index.ts - Add these types

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'viewer';
  avatar?: string;
  createdAt: string;
  lastLogin?: string;
  // Profile fields
  bio?: string;
  department?: string;
  position?: string;
  phone?: string;
  location?: string;
  timezone?: string;
  preferences?: UserPreferences;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  notifications: boolean;
  emailNotifications: boolean;
  language: string;
  dashboardView: 'grid' | 'list';
}

export interface UpdateProfileData {
  name?: string;
  email?: string;
  bio?: string;
  department?: string;
  position?: string;
  phone?: string;
  location?: string;
  timezone?: string;
  preferences?: Partial<UserPreferences>;
}


export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  link?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}