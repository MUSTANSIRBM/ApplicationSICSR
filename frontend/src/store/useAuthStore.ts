// src/store/useAuthStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, LoginCredentials, RegisterData, AuthResponse } from '@/types';
import { authApi } from '../api/authClient';
import toast from 'react-hot-toast';

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  setUser: (user: User | null) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(credentials);
          set({
            user: response.user,
            token: response.token,
            isAuthenticated: true,
            isLoading: false,
          });
          toast.success(`Welcome back, ${response.user.name}! 👋`);
          
          // Force a hard refresh after login to ensure styles load properly
          if (typeof window !== 'undefined') {
            setTimeout(() => {
              window.location.href = '/board';
            }, 300);
          }
        } catch (error: any) {
          set({ isLoading: false });
          toast.error(error.message || 'Login failed. Please try again.');
          throw error;
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true });
        try {
          const response = await authApi.register(data);
          set({
            user: response.user,
            token: response.token,
            isAuthenticated: true,
            isLoading: false,
          });
          toast.success(`Welcome to Block Planner, ${response.user.name}! 🚀`);
          
          // Force a hard refresh after registration to ensure styles load properly
          if (typeof window !== 'undefined') {
            setTimeout(() => {
              window.location.href = '/board';
            }, 300);
          }
        } catch (error: any) {
          set({ isLoading: false });
          toast.error(error.message || 'Registration failed. Please try again.');
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await authApi.logout();
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
          toast.success('Logged out successfully');
          
          // Force a hard refresh after logout to ensure styles load properly
          if (typeof window !== 'undefined') {
            setTimeout(() => {
              window.location.href = '/login';
            }, 300);
          }
        } catch (error) {
          set({ isLoading: false });
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
          toast.success('Logged out successfully');
          
          // Force a hard refresh after logout to ensure styles load properly
          if (typeof window !== 'undefined') {
            setTimeout(() => {
              window.location.href = '/login';
            }, 300);
          }
        }
      },

      checkAuth: async () => {
        const { token, user } = get();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return false;
        }

        try {
          const isValid = await authApi.verifyToken(token);
          if (isValid) {
            // Refresh user data
            const currentUser = await authApi.getCurrentUser(token);
            if (currentUser) {
              set({ user: currentUser, isAuthenticated: true });
            } else {
              set({ isAuthenticated: true });
            }
            return true;
          } else {
            set({ isAuthenticated: false, user: null, token: null });
            return false;
          }
        } catch (error) {
          set({ isAuthenticated: false, user: null, token: null });
          return false;
        }
      },

      setUser: (user: User | null) => {
        set({ user });
      },

      clearAuth: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);