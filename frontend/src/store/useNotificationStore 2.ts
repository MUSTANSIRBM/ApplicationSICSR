// src/store/useNotificationStore.ts
import { create } from 'zustand';
import { Notification } from '@/types';
import toast from 'react-hot-toast';

interface NotificationStore {
  notifications: Notification[];
  unreadCount: number;
  isOpen: boolean;
  addNotification: (notification: Omit<Notification, 'id' | 'read' | 'createdAt'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (id: string) => void;
  clearAll: () => void;
  toggleDropdown: () => void;
  setOpen: (open: boolean) => void;
  getUnreadCount: () => number;
}

// Generate unique ID
const generateId = () => Math.random().toString(36).substring(2, 10);

// Mock notifications
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'success',
    title: 'Defect Scheduled ✅',
    message: 'Defect D-012 has been successfully scheduled for Week 36',
    read: false,
    createdAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    link: '/plan',
  },
  {
    id: '2',
    type: 'warning',
    title: 'Overdue Defect Alert ⚠️',
    message: 'Defect D-007 is 5 days overdue. Please take action.',
    read: false,
    createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    link: '/board',
  },
  {
    id: '3',
    type: 'info',
    title: 'Schedule Optimized 📊',
    message: 'Schedule has been optimized with 2.5 hours of savings',
    read: true,
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    link: '/impact',
  },
  {
    id: '4',
    type: 'error',
    title: 'Conflict Detected ⚡',
    message: 'Corridor A-12 has a scheduling conflict. Please resolve.',
    read: true,
    createdAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    link: '/live',
  },
  {
    id: '5',
    type: 'success',
    title: 'Block Approved ✅',
    message: 'Block B-003 has been approved by the manager',
    read: true,
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    link: '/plan',
  },
];

// Helper function to show toast notifications
const showToast = (type: string, title: string, message: string) => {
  const toastMap: Record<string, () => void> = {
    success: () => toast.success(title, { duration: 4000 }),
    error: () => toast.error(title, { duration: 4000 }),
    warning: () => toast(title, { 
      icon: '⚠️', 
      duration: 4000,
      style: {
        background: '#FEF3C7',
        color: '#92400E',
        border: '1px solid #FCD34D',
      }
    }),
    info: () => toast(title, { 
      icon: 'ℹ️', 
      duration: 4000,
      style: {
        background: '#EFF6FF',
        color: '#1E40AF',
        border: '1px solid #93C5FD',
      }
    }),
  };
  
  const showFn = toastMap[type] || toastMap.info;
  showFn();
};

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: mockNotifications,
  unreadCount: mockNotifications.filter(n => !n.read).length,
  isOpen: false,

  addNotification: (notification) => {
    const newNotification: Notification = {
      ...notification,
      id: generateId(),
      read: false,
      createdAt: new Date().toISOString(),
    };
    
    set((state) => ({
      notifications: [newNotification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    }));

    // Show toast using the helper function
    showToast(notification.type, notification.title, notification.message);
  },

  markAsRead: (id: string) => {
    set((state) => {
      const updated = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications: updated,
        unreadCount: updated.filter((n) => !n.read).length,
      };
    });
  },

  markAllAsRead: () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }));
    toast.success('All notifications marked as read');
  },

  deleteNotification: (id: string) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
      unreadCount: state.notifications.filter((n) => n.id !== id && !n.read).length,
    }));
  },

  clearAll: () => {
    set({
      notifications: [],
      unreadCount: 0,
    });
    toast.success('All notifications cleared');
  },

  toggleDropdown: () => {
    set((state) => ({ isOpen: !state.isOpen }));
  },

  setOpen: (open: boolean) => {
    set({ isOpen: open });
  },

  getUnreadCount: () => {
    return get().unreadCount;
  },
}));