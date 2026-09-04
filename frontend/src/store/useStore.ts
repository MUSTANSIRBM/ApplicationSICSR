// src/store/useStore.ts
import { create } from 'zustand';
import { Defect, ScheduleBlock, TimelineData, ImpactData, SystemStatus, FilterParams } from '@/types';
import { api } from '@/api/client';
import { useNotificationStore } from './useNotificationStore';

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
  
  scheduleDefect: (id: string, weekStart?: string) => Promise<void>;
  deferDefect: (id: string, reason?: string) => Promise<void>;
  deleteDefect: (id: string) => Promise<void>;
  editDefect: (id: string, data: Partial<Defect>) => Promise<void>;
  createDefect: (defect: Omit<Defect, 'id' | 'createdAt' | 'score'>) => Promise<Defect>;
  
  approveBlock: (id: string) => Promise<void>;
  lockBlock: (id: string) => Promise<void>;
  deleteBlock: (id: string) => Promise<void>;
  editBlock: (id: string, data: Partial<ScheduleBlock>) => Promise<void>;
  
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
      if (get().searchQuery && !currentFilters.search) {
        currentFilters.search = get().searchQuery;
      }
      const defects = await api.getDefects(currentFilters);
      set({ defects: defects || [], loading: false });
    } catch (error) {
      set({ defects: [], loading: false });
      throw error;
    }
  },

  loadSchedule: async (week: string) => {
    set({ loading: true });
    try {
      const data = await api.getSchedule(week);
      set({ 
        timelineData: data || null, 
        blocks: data?.blocks || [],
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
      set({ impactData: data || null });
    } catch (error) {
      set({ impactData: null });
      throw error;
    }
  },

  loadStatus: async () => {
    try {
      const data = await api.getStatus();
      set({ systemStatus: data || null });
    } catch (error) {
      set({ systemStatus: null });
      throw error;
    }
  },

  scheduleDefect: async (id: string, weekStart?: string) => {
    set({ loading: true });
    try {
      const targetWeek = weekStart || get().selectedWeek;
      await api.scheduleDefect(id, targetWeek);
      
      await get().loadDefects();
      await get().loadSchedule(targetWeek);
      await get().loadImpact(targetWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'success',
        title: 'Defect Scheduled ✅',
        message: `Defect ${id} has been successfully scheduled for ${new Date(targetWeek).toLocaleDateString()}`,
        link: '/plan',
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  deferDefect: async (id: string, reason?: string) => {
    set({ loading: true });
    try {
      await api.deferDefect(id, reason);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'warning',
        title: 'Defect Deferred ⏳',
        message: `Defect ${id} has been deferred${reason ? `: ${reason}` : ''}`,
        link: '/board',
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  deleteDefect: async (id: string) => {
    set({ loading: true });
    try {
      await api.deleteDefect(id);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'info',
        title: 'Defect Deleted 🗑️',
        message: `Defect ${id} has been deleted from the system`,
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  editDefect: async (id: string, data: Partial<Defect>) => {
    set({ loading: true });
    try {
      await api.editDefect(id, data);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'info',
        title: 'Defect Updated ✏️',
        message: `Defect ${id} has been updated successfully`,
        link: '/board',
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  createDefect: async (defectData: Omit<Defect, 'id' | 'createdAt' | 'score'>) => {
    set({ loading: true });
    try {
      const newDefect = await api.createDefect(defectData);
      await get().loadDefects();
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'success',
        title: 'New Defect Created 📝',
        message: `Defect ${newDefect.id} has been created: ${defectData.description?.substring(0, 50)}...`,
        link: '/board',
      });
      
      set({ loading: false });
      return newDefect;
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
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'success',
        title: 'Block Approved ✅',
        message: `Block ${id} has been approved by the manager`,
        link: '/plan',
      });
      
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
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'success',
        title: 'Block Locked 🔒',
        message: `Block ${id} has been locked and finalized`,
        link: '/plan',
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  deleteBlock: async (id: string) => {
    set({ loading: true });
    try {
      await api.deleteBlock(id);
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'warning',
        title: 'Block Deleted 🗑️',
        message: `Block ${id} has been deleted from the schedule`,
        link: '/plan',
      });
      
      set({ loading: false });
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  editBlock: async (id: string, data: Partial<ScheduleBlock>) => {
    set({ loading: true });
    try {
      await api.editBlock(id, data);
      await get().loadSchedule(get().selectedWeek);
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'info',
        title: 'Block Updated ✏️',
        message: `Block ${id} has been updated successfully`,
        link: '/plan',
      });
      
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
      
      // Add notification
      const { addNotification } = useNotificationStore.getState();
      addNotification({
        type: 'error',
        title: '🚨 Emergency Defect Injected',
        message: `Emergency ${defect.department} defect "${defect.description}" injected. ${result.blocksMoved.length} blocks moved.`,
        link: '/live',
      });
      
      set({ loading: false });
      return result;
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
    const currentFilters = get().filters;
    const newFilters = { 
      ...currentFilters,
      search: query || undefined
    };
    set({ filters: newFilters });
    get().loadDefects(newFilters);
  },

  setFilters: (filters: FilterParams) => {
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