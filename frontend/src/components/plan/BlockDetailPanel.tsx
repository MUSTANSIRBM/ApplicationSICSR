// frontend/src/components/plan/BlockDetailPanel.tsx
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import { format } from 'date-fns';
import { ScheduleBlock } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface BlockDetailPanelProps {
  block: ScheduleBlock | null;
  open: boolean;
  onClose: () => void;
  onApprove?: (id: string) => void;
  onLock?: (id: string) => void;
}

export function BlockDetailPanel({ block, open, onClose, onApprove, onLock }: BlockDetailPanelProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (open) {
      setIsVisible(true);
    } else {
      const timer = setTimeout(() => setIsVisible(false), 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

  if (!block) return null;

  const start = new Date(block.startTime);
  const end = new Date(block.endTime);

  return (
    <>
      <div 
        className={clsx(
          'fixed inset-0 bg-black/20 transition-opacity z-40',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
      />

      <div
        className={clsx(
          'fixed top-0 right-0 h-full w-[480px] bg-white shadow-xl transition-transform z-50 overflow-y-auto',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Block {block.id}</h2>
              <p className="text-sm text-gray-500">
                Corridor {block.corridor} · {format(start, 'MMM d, h:mm a')} – {format(end, 'h:mm a')}
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              ✕
            </button>
          </div>

          <div className="flex items-center gap-2 mb-4">
            <Badge variant={block.department} className="capitalize">
              {block.isCombined ? 'Combined' : block.department}
            </Badge>
            <Badge variant={block.status === 'approved' ? 'approved' : 'default'}>
              {block.status}
            </Badge>
            {block.isCombined && (
              <Badge variant="combined" size="sm">
                +{block.savings.toFixed(1)}h saved
              </Badge>
            )}
          </div>

          <div className="border-t border-gray-200 pt-4 mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Defects ({block.defects.length})</h4>
            <div className="space-y-2">
              {block.defects.map(defect => (
                <div key={defect.id} className="text-sm p-2 bg-gray-50 rounded-md">
                  <div className="flex items-center gap-2">
                    <Badge variant={defect.department} size="sm">{defect.department}</Badge>
                    <span className="font-medium">{defect.id}</span>
                    <span className="text-gray-500">·</span>
                    <span className="text-gray-600 truncate">{defect.description}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {block.isCombined && (
            <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
              <div className="text-sm font-medium text-green-800">Bundle Savings</div>
              <div className="text-sm text-green-700">
                {block.defects.map(d => d.department).join(' + ')} combined
                · {block.savings.toFixed(1)} hours saved vs separate closures
              </div>
            </div>
          )}

          <div className="border-t border-gray-200 pt-4 flex items-center gap-2">
            {block.status === 'proposed' && (
              <>
                <Button onClick={() => onApprove?.(block.id)} variant="success" size="sm">
                  ✓ Approve
                </Button>
                <Button onClick={() => onLock?.(block.id)} variant="primary" size="sm">
                  🔒 Lock
                </Button>
              </>
            )}
            {block.status === 'approved' && (
              <Button onClick={() => onLock?.(block.id)} variant="primary" size="sm">
                🔒 Lock
              </Button>
            )}
            <Button variant="ghost" size="sm">📋 View Details</Button>
            <Button variant="ghost" size="sm" className="ml-auto">🗑️</Button>
          </div>
        </div>
      </div>
    </>
  );
}