// frontend/src/components/live/BeforeAfterView.tsx
import { useState } from 'react';
import { clsx } from 'clsx';
import { ScheduleBlock, SolveResult } from '@/types';
import { Button } from '@/components/ui/Button';

interface BeforeAfterViewProps {
  beforeBlocks: ScheduleBlock[];
  afterBlocks: ScheduleBlock[];
  result: SolveResult | null;
  onAccept?: () => void;
  onReject?: () => void;
}

export function BeforeAfterView({ beforeBlocks, afterBlocks, result, onAccept, onReject }: BeforeAfterViewProps) {
  const [view, setView] = useState<'before' | 'after' | 'diff'>('after');

  const getBlockStyle = (block: ScheduleBlock, isAfter: boolean) => {
    if (view === 'diff' && result) {
      if (result.blocksAdded.includes(block.id) && isAfter) {
        return 'bg-red-100 border-red-500 animate-pulse-glow';
      }
      if (result.blocksMoved.includes(block.id) && isAfter) {
        return 'bg-yellow-100 border-yellow-500';
      }
      if (result.blocksUnchanged.includes(block.id)) {
        return 'bg-green-50 border-green-300';
      }
    }
    return 'bg-white border-gray-200';
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="flex rounded-md overflow-hidden border border-gray-200">
          {(['before', 'after', 'diff'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setView(mode)}
              className={clsx(
                'px-3 py-1 text-sm capitalize transition-colors',
                view === mode ? 'bg-blue-100 text-blue-700' : 'bg-white text-gray-600 hover:bg-gray-50'
              )}
            >
              {mode}
            </button>
          ))}
        </div>
        {result && (
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-gray-500">Solved in</span>
            <span className="font-mono font-medium">{result.timeMs}ms</span>
            <span className={clsx(
              'px-2 py-0.5 rounded-full text-xs font-medium',
              result.status === 'solved-optimal' ? 'bg-green-100 text-green-700' :
              result.status === 'solved-moved' ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            )}>
              {result.status.replace('-', ' ')}
            </span>
          </div>
        )}
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 w-20">Corridor</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Blocks</th>
            </tr>
          </thead>
          <tbody>
            {['A', 'B', 'C', 'D', 'E'].map(corridor => {
              const blocks = view === 'before' ? beforeBlocks : afterBlocks;
              const filtered = blocks.filter(b => b.corridor === corridor);
              const isAfter = view === 'after' || view === 'diff';
              
              return (
                <tr key={corridor} className="border-b border-gray-100 last:border-0">
                  <td className="px-3 py-2 font-medium text-gray-700">{corridor}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1.5">
                      {filtered.length > 0 ? filtered.map(block => (
                        <div
                          key={block.id}
                          className={clsx(
                            'px-2 py-0.5 rounded text-xs border transition-all',
                            getBlockStyle(block, isAfter)
                          )}
                        >
                          {block.id}
                          <span className="ml-1 text-gray-400">{block.defects.length}</span>
                        </div>
                      )) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {result && view !== 'before' && (
        <div className="mt-3 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            <span className="font-medium">{result.blocksUnchanged.length}</span> blocks unchanged,
            <span className="font-medium text-yellow-600"> {result.blocksMoved.length}</span> moved,
            <span className="font-medium text-red-600"> {result.blocksAdded.length}</span> added
          </div>
          <div className="flex gap-2">
            <Button onClick={onAccept} variant="success" size="sm">Accept</Button>
            <Button onClick={onReject} variant="secondary" size="sm">Reject</Button>
          </div>
        </div>
      )}
    </div>
  );
}