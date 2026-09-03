import { useState, useMemo } from 'react';
import { clsx } from 'clsx';
import { Defect } from '@/types';
import { Badge } from '@/components/ui/Badge';
import { ScoreBreakdown } from './ScoreBreakdown';
import { calculateDefectScore } from '@/api/mockData';

interface DefectCardProps {
  defect: Defect;
  onSchedule?: (id: string) => void;
  onDefer?: (id: string) => void;
  onDelete?: (id: string) => void;
}

const tierColors = {
  'safety-critical': 'border-safety-critical/30 bg-safety-critical/5',
  high: 'border-orange-400/30 bg-orange-50',
  normal: 'border-blue-400/30 bg-blue-50',
  deferred: 'border-gray-400/30 bg-gray-50',
};

export function DefectCard({ defect, onSchedule, onDefer, onDelete }: DefectCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Always calculate score dynamically for consistency
  const displayScore = useMemo(() => {
    return calculateDefectScore(defect);
  }, [defect]);

  return (
    <div className={clsx(
      'border rounded-lg p-3 transition-all cursor-pointer',
      tierColors[defect.tier],
      expanded ? 'shadow-md' : 'hover:shadow-sm'
    )}>
      <div onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Badge variant={defect.department} size="sm">{defect.department}</Badge>
              <span className="text-xs text-gray-500">{defect.id}</span>
            </div>
            <p className="text-sm font-medium text-gray-900 mt-1 truncate">
              {defect.description}
            </p>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span>Corridor {defect.corridor}</span>
              <span>•</span>
              <span>Score: <span className="font-semibold text-gray-700">{displayScore.toFixed(1)}/100</span></span>
              <span>•</span>
              <span>Overdue: {defect.overdueDays}d</span>
            </div>
          </div>
          <div className="flex items-center gap-2 ml-2">
            <Badge variant={defect.tier}>{defect.tier}</Badge>
            <span className="text-gray-400">{expanded ? '▾' : '▸'}</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-200/50 space-y-3">
          <ScoreBreakdown defect={defect} />
          
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSchedule?.(defect.id);
              }}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Schedule Now
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDefer?.(defect.id);
              }}
              className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
            >
              Defer
            </button>
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete?.(defect.id);
                }}
                className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors ml-auto"
              >
                Delete
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}