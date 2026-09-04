// src/components/ui/Badge.tsx
import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  children: ReactNode;
  variant?: 'track' | 'power' | 'signals' | 'combined' | 'safety-critical' | 'high' | 'medium' | 'low' | 'deferred' | 'approved' | 'locked' | 'pending' | 'default' | 'success' | 'warning' | 'info' | 'error';
  size?: 'sm' | 'md';
  className?: string;
  animated?: boolean;
}

const variants: Record<string, string> = {
  track: 'bg-orange-100 text-orange-800',
  power: 'bg-yellow-100 text-yellow-800',
  signals: 'bg-blue-100 text-blue-800',
  combined: 'bg-purple-100 text-purple-800',
  'safety-critical': 'bg-red-100 text-red-800 animate-pulse-glow',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
  deferred: 'bg-gray-100 text-gray-600',
  approved: 'bg-green-100 text-green-800',
  locked: 'bg-indigo-100 text-indigo-800',
  pending: 'bg-yellow-100 text-yellow-800',
  default: 'bg-gray-100 text-gray-600',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  info: 'bg-cyan-100 text-cyan-800',
  error: 'bg-red-100 text-red-800',
};

export function Badge({ children, variant = 'default', size = 'md', className, animated = false }: BadgeProps) {
  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-0.5 text-xs gap-1.5',
  };

  return (
    <span className={clsx(
      'inline-flex items-center rounded-full font-medium transition-all duration-200',
      sizeStyles[size],
      variants[variant] || variants.default,
      animated && 'animate-pulse-glow',
      className
    )}>
      {children}
    </span>
  );
}