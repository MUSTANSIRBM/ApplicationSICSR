import { create } from 'zustand';
import { Defect, ScheduleBlock, TimelineData, ImpactData, SystemStatus, FilterParams } from '@/types';
import { api } from '@/api/client';

interface AppState {
  defects: Defect[];
  blocks: ScheduleBlock[];
  timelineData: TimelineData | null;
  impactData: ImpactData | null;
  systemStatus: SystemStatus | null;
  loading: boolean;
  selectedWeek: string;
  filters: FilterParams;
  searchQuery: string;
  
  loadDefects: (filters?: FilterParams) => Promise<void>;
  loadSchedule: (week: string) => Promise<void>;
  loadImpact: (week: string) => Promise<void>;
  loadStatus: () => Promise<void>;
  scheduleDefect: (id: string) => Promise<void>;
  deferDefect: (id: string, reason?: string) => Promise<void>;
  deleteDefect: (id: string) => Promise<void>;
  approveBlock: (id: string) => Promise<void>;
  lockBlock: (id: string) => Promise<void>;
  injectDefect: (defect: any) => Promise<any>;
  setSearchQuery: (query: string) => void;
  setFilters: (filters: FilterParams) => void;
  setSelectedWeek: (week: string) => void;
  resetStore: () => void;
}

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
      // Only include search if there's a search query
      if (get().searchQuery && !currentFilters.search) {
        currentFilters.search = get().searchQuery;
      }
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

  deleteDefect: async (id: string) => {
    set({ loading: true });
    try {
      await api.deleteDefect(id);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  scheduleDefect: async (id: string) => {
    set({ loading: true });
    try {
      await api.scheduleDefect(id);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  deferDefect: async (id: string) => {
    set({ loading: true });
    try {
      await api.deferDefect(id);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  approveBlock: async (id: string) => {
    set({ loading: true });
    try {
      await api.approveBlock(id);
      await get().loadSchedule(get().selectedWeek);
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  lockBlock: async (id: string) => {
    set({ loading: true });
    try {
      await api.lockBlock(id);
      await get().loadSchedule(get().selectedWeek);
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  injectDefect: async (defect: any) => {
    set({ loading: true });
    try {
      const result = await api.injectDefect(defect);
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
    // Update filters with search query
    const currentFilters = get().filters;
    const newFilters = { 
      ...currentFilters,
      search: query || undefined
    };
    set({ filters: newFilters });
    // Only load defects if there's a search query or it was cleared
    get().loadDefects(newFilters);
  },

  setFilters: (filters: FilterParams) => {
    // Preserve search query in filters
    const searchQuery = get().searchQuery;
    const newFilters = { 
      ...filters,
      search: searchQuery || filters.search
    };
    set({ filters: newFilters });
    get().loadDefects(newFilters);
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