// src/store/useStore.ts
import { create } from 'zustand';
import { Defect, ScheduleBlock, TimelineData, ImpactData, SystemStatus, FilterParams } from '@/types';
import { api } from '@/api/client';
import { mockDefects, mockBlocks, mockTimelineData, mockImpactData, mockSystemStatus } from '@/api/mockData';

interface AppState {
  // State
  defects: Defect[];
  blocks: ScheduleBlock[];
  timelineData: TimelineData | null;
  impactData: ImpactData | null;
  systemStatus: SystemStatus | null;
  loading: boolean;
  selectedWeek: string;
  filters: FilterParams;
  searchQuery: string;
  
  // Actions
  loadDefects: (filters?: FilterParams) => Promise<void>;
  loadSchedule: (week: string) => Promise<void>;
  loadImpact: (week: string) => Promise<void>;
  loadStatus: () => Promise<void>;
  scheduleDefect: (id: string) => Promise<void>;
  deferDefect: (id: string, reason?: string) => Promise<void>;
  approveBlock: (id: string) => Promise<void>;
  lockBlock: (id: string) => Promise<void>;
  injectDefect: (defect: any) => Promise<any>;
  setSearchQuery: (query: string) => void;
  setFilters: (filters: FilterParams) => void;
  setSelectedWeek: (week: string) => void;
  resetStore: () => void;
}

// Initial state for fresh load
const initialState = {
  defects: [],
  blocks: [],
  timelineData: null,
  impactData: null,
  systemStatus: null,
  loading: false,
  selectedWeek: new Date().toISOString(),
  filters: {},
  searchQuery: '',
};

export const useStore = create<AppState>((set, get) => ({
  ...initialState,

  loadDefects: async (filters?: FilterParams) => {
    set({ loading: true });
    try {
      const currentFilters = filters || get().filters;
      const defects = await api.getDefects(currentFilters);
      set({ defects, loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  loadSchedule: async (week: string) => {
    set({ loading: true });
    try {
      const data = await api.getSchedule(week);
      set({ 
        timelineData: data, 
        blocks: data.blocks,
        selectedWeek: week,
        loading: false 
      });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  loadImpact: async (week: string) => {
    try {
      const data = await api.getImpact(week);
      set({ impactData: data });
    } catch (error) {
      throw error;
    }
  },

  loadStatus: async () => {
    try {
      const data = await api.getStatus();
      set({ systemStatus: data });
    } catch (error) {
      throw error;
    }
  },

  scheduleDefect: async (id: string) => {
    set({ loading: true });
    try {
      const defect = await api.scoreDefect(id);
      // Update defect in list
      const updatedDefects = get().defects.map(d => 
        d.id === id ? { ...d, status: 'scored', ...defect } : d
      );
      set({ defects: updatedDefects, loading: false });
      
      // Reload schedule to reflect changes
      await get().loadSchedule(get().selectedWeek);
      return defect;
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  deferDefect: async (id: string, reason?: string) => {
    set({ loading: true });
    try {
      // In real app, call API to defer
      const updatedDefects = get().defects.map(d => 
        d.id === id ? { ...d, status: 'deferred', tier: 'deferred' } : d
      );
      set({ defects: updatedDefects, loading: false });
      
      // Reload schedule to reflect changes
      await get().loadSchedule(get().selectedWeek);
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  approveBlock: async (id: string) => {
    set({ loading: true });
    try {
      const block = await api.approveBlock(id);
      const updatedBlocks = get().blocks.map(b => 
        b.id === id ? { ...b, status: 'approved' } : b
      );
      set({ blocks: updatedBlocks, loading: false });
      
      // Reload schedule
      await get().loadSchedule(get().selectedWeek);
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  lockBlock: async (id: string) => {
    set({ loading: true });
    try {
      const block = await api.lockBlock(id);
      const updatedBlocks = get().blocks.map(b => 
        b.id === id ? { ...b, status: 'locked' } : b
      );
      set({ blocks: updatedBlocks, loading: false });
      
      // Reload schedule
      await get().loadSchedule(get().selectedWeek);
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  injectDefect: async (defect: any) => {
    set({ loading: true });
    try {
      const result = await api.injectDefect(defect);
      // Reload everything to reflect changes
      await get().loadSchedule(get().selectedWeek);
      await get().loadDefects();
      await get().loadImpact(get().selectedWeek);
      set({ loading: false });
      return result;
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
    // Apply search filter
    get().loadDefects({ ...get().filters, search: query });
  },

  setFilters: (filters: FilterParams) => {
    set({ filters });
    get().loadDefects(filters);
  },

  setSelectedWeek: (week: string) => {
    set({ selectedWeek: week });
    get().loadSchedule(week);
    get().loadImpact(week);
  },

  resetStore: () => {
    set(initialState);
  },
}));