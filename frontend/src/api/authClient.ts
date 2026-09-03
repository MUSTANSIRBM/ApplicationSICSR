// src/api/authClient.ts
import { LoginCredentials, RegisterData, AuthResponse, User } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const USE_MOCK = true;

// Mock user data
const mockUsers: User[] = [
  {
    id: '1',
    email: 'admin@blockplanner.com',
    name: 'Admin User',
    role: 'admin',
    createdAt: new Date().toISOString(),
  },
  {
    id: '2',
    email: 'user@blockplanner.com',
    name: 'John Doe',
    role: 'user',
    createdAt: new Date().toISOString(),
  },
];

const mockPasswords: Record<string, string> = {
  'admin@blockplanner.com': 'admin123',
  'user@blockplanner.com': 'user123',
};

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const generateToken = (user: User): string => {
  return btoa(JSON.stringify({ 
    userId: user.id, 
    email: user.email,
    exp: Date.now() + 7 * 24 * 60 * 60 * 1000
  }));
};

const verifyToken = (token: string): { valid: boolean; user?: User } => {
  try {
    const decoded = JSON.parse(atob(token));
    if (decoded.exp < Date.now()) {
      return { valid: false };
    }
    const user = mockUsers.find(u => u.id === decoded.userId);
    return { valid: true, user };
  } catch {
    return { valid: false };
  }
};

export const authApi = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    if (USE_MOCK) {
      await delay(800);
      
      const user = mockUsers.find(u => u.email === credentials.email);
      const password = mockPasswords[credentials.email];
      
      if (!user || password !== credentials.password) {
        throw new Error('Invalid email or password');
      }
      
      const token = generateToken(user);
      
      return {
        user,
        token,
        expiresIn: 7 * 24 * 60 * 60,
      };
    }
    
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }
    
    return response.json();
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    if (USE_MOCK) {
      await delay(1000);
      
      if (data.password !== data.confirmPassword) {
        throw new Error('Passwords do not match');
      }
      
      if (mockUsers.find(u => u.email === data.email)) {
        throw new Error('Email already registered');
      }
      
      const newUser: User = {
        id: String(mockUsers.length + 1),
        email: data.email,
        name: data.name,
        role: 'user',
        createdAt: new Date().toISOString(),
      };
      
      mockUsers.push(newUser);
      mockPasswords[data.email] = data.password;
      
      const token = generateToken(newUser);
      
      return {
        user: newUser,
        token,
        expiresIn: 7 * 24 * 60 * 60,
      };
    }
    
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }
    
    return response.json();
  },

  async logout(): Promise<void> {
    if (USE_MOCK) {
      await delay(300);
      return;
    }
    
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
    });
  },

  async verifyToken(token: string): Promise<boolean> {
    if (USE_MOCK) {
      await delay(200);
      const result = verifyToken(token);
      return result.valid;
    }
    
    const response = await fetch(`${API_BASE}/auth/verify`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    return response.ok;
  },

  async getCurrentUser(token: string): Promise<User | null> {
    if (USE_MOCK) {
      await delay(200);
      const result = verifyToken(token);
      return result.user || null;
    }
    
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) return null;
    return response.json();
  },
};