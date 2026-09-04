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

// ============================================================================
// Sensor Incident Types
// ============================================================================

export type EnvironmentalCondition = 'clear' | 'rain' | 'heavy_rain' | 'fog' | 'snow' | 'flood';
export type ObstructionType =
  | 'landslide_debris' | 'boulder' | 'track_buckling' | 'fallen_tree'
  | 'stranded_vehicle' | 'water_logging' | 'cattle_crossing'
  | 'broken_rail' | 'signal_cable_theft' | 'sensor_miscount'
  | 'environmental_false_positive' | 'unknown_obstruction' | 'equipment_failure_ahead';
export type SensorType = 'track_circuit' | 'axle_counter' | 'vibration' | 'accelerometer';
export type Action = 'proceed_with_caution' | 'reduce_speed' | 'reroute' | 'emergency_stop';

export interface IncidentRequest {
  train_speed_kmh: number;
  distance_to_obstacle_km: number;
  environmental_condition: EnvironmentalCondition;
  weather_alert: boolean;
  signal_quality_percent: number;
  severity_score: number;
  obstruction_type: ObstructionType;
  alternative_route_available: boolean;
  communication_latency_ms: number;
  axle_balance?: number | null;
  ahead_section_status: 'OCCUPIED' | 'CLEAR';
  known_train_schedule: boolean;
  distance_from_station_km: number;
  sensor_type: SensorType;
  create_repair_defect?: boolean;
  corridor?: string;
}

export interface PhysicsData {
  braking_distance_required_km: number;
  time_to_obstacle_min: number;
  effective_distance_km: number;
  safe_stopping_possible: boolean;
  weather_braking_multiplier?: number;
  speed_advisory?: { recommended_speed_kmh: number | null; basis: string };
}

export interface IncidentResponse {
  action: Action;
  confidence: number | null;
  source: string;
  reasons: string[];
  physics: PhysicsData;
  probabilities: Record<string, number> | null;
  evidence?: { summary: string; features: any[] } | null;
  decision_latency_ms: number;
  within_100ms_budget: boolean;
  repair_defect_id?: string | null;
}

// ============================================================================
// User Types
// ============================================================================

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