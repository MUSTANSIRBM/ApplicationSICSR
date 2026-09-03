import { useEffect, useState } from 'react';
import { clsx } from 'clsx';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  description?: string;
  change?: number;
  icon?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'green' | 'red' | 'blue' | 'yellow';
  animate?: boolean;
}

export function MetricCard({ 
  title, 
  value, 
  subtitle, 
  description,
  change, 
  icon, 
  trend, 
  color = 'blue',
  animate = false 
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(animate ? 0 : value);

  useEffect(() => {
    if (animate && typeof value === 'number') {
      let start = 0;
      const duration = 1000;
      const step = Math.max(value / 60, 1);
      const interval = duration / 60;
      
      const timer = setInterval(() => {
        start += step;
        if (start >= value) {
          setDisplayValue(value);
          clearInterval(timer);
        } else {
          setDisplayValue(Math.round(start));
        }
      }, interval);
      
      return () => clearInterval(timer);
    }
  }, [value, animate]);

  const colors = {
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    blue: 'bg-blue-50 border-blue-200',
    yellow: 'bg-yellow-50 border-yellow-200',
  };

  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-500',
  };

  const finalValue = animate ? displayValue : value;

  return (
    <div className={clsx('card border', colors[color])}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {typeof finalValue === 'number' && !Number.isInteger(finalValue) 
              ? finalValue.toFixed(1) 
              : finalValue}
          </p>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
          {description && <p className="text-xs text-gray-400 mt-1">{description}</p>}
        </div>
        {icon && <span className="text-2xl">{icon}</span>}
      </div>
      {change !== undefined && (
        <div className="mt-2 flex items-center gap-1">
          <span className={clsx('text-xs font-medium', trendColors[trend || 'neutral'])}>
            {change > 0 ? '+' : ''}{change}%
          </span>
          <span className="text-xs text-gray-400">vs previous week</span>
        </div>
      )}
    </div>
  );
}