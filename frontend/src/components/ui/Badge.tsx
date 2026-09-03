// frontend/src/components/ui/Badge.tsx
import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  children: ReactNode;
  variant?: 'track' | 'power' | 'signals' | 'combined' | 'safety-critical' | 'high' | 'normal' | 'deferred' | 'approved' | 'default';
  size?: 'sm' | 'md';
  className?: string;
}

const variants = {
  track: 'bg-track/20 text-track border-track',
  power: 'bg-power/20 text-power border-power',
  signals: 'bg-signals/20 text-signals border-signals',
  combined: 'bg-combined/20 text-combined border-combined',
  'safety-critical': 'bg-safety-critical/10 text-safety-critical border-safety-critical',
  high: 'bg-orange-100 text-orange-700 border-orange-400',
  normal: 'bg-blue-100 text-blue-700 border-blue-400',
  deferred: 'bg-gray-100 text-gray-600 border-gray-400',
  approved: 'bg-green-100 text-green-700 border-green-400',
  default: 'bg-gray-100 text-gray-600 border-gray-300',
};

export function Badge({ children, variant = 'default', size = 'md', className }: BadgeProps) {
  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2.5 py-0.5 text-xs',
  };

  return (
    <span className={clsx(
      'inline-flex items-center rounded-full font-medium border',
      sizeStyles[size],
      variants[variant],
      className
    )}>
      {children}
    </span>
  );
}