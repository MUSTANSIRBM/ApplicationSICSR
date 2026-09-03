// frontend/src/components/board/DefectList.tsx
import { useState } from 'react';
import { clsx } from 'clsx';
import { Defect, FilterParams } from '@/types';
import { DefectCard } from './DefectCard';
import { Badge } from '@/components/ui/Badge';

interface DefectListProps {
  defects: Defect[];
  filters: FilterParams;
  onFilterChange: (filters: FilterParams) => void;
  onSchedule: (id: string) => void;
  onDefer: (id: string) => void;
}

const departments = ['all', 'track', 'power', 'signals'] as const;
const tiers = ['all', 'safety-critical', 'high', 'normal', 'deferred'] as const;

export function DefectList({ defects, filters, onFilterChange, onSchedule, onDefer }: DefectListProps) {
  const [search, setSearch] = useState('');

  const handleSearch = (value: string) => {
    setSearch(value);
    onFilterChange({ ...filters, search: value });
  };

  const groupedDefects = defects.reduce((acc, d) => {
    if (!acc[d.tier]) acc[d.tier] = [];
    acc[d.tier].push(d);
    return acc;
  }, {} as Record<string, Defect[]>);

  const tierOrder = ['safety-critical', 'high', 'normal', 'deferred'];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search defects..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1">
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => onFilterChange({ ...filters, department: dept === 'all' ? undefined : dept })}
              className={clsx(
                'px-2 py-1 text-xs rounded-md transition-colors capitalize',
                (filters.department === dept || (dept === 'all' && !filters.department))
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {dept}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {tiers.map((tier) => (
            <button
              key={tier}
              onClick={() => onFilterChange({ ...filters, tier: tier === 'all' ? undefined : tier })}
              className={clsx(
                'px-2 py-1 text-xs rounded-md transition-colors capitalize',
                (filters.tier === tier || (tier === 'all' && !filters.tier))
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {tier.replace('-', ' ')}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-500 ml-auto">{defects.length} defects</span>
      </div>

      <div className="space-y-3">
        {tierOrder.map((tier) => {
          const items = groupedDefects[tier] || [];
          if (items.length === 0) return null;
          
          return (
            <div key={tier}>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={tier as any}>{tier}</Badge>
                <span className="text-xs text-gray-500">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map(defect => (
                  <DefectCard
                    key={defect.id}
                    defect={defect}
                    onSchedule={onSchedule}
                    onDefer={onDefer}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}