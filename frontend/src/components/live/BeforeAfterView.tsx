// src/components/live/BeforeAfterView.tsx
import { useState, useMemo } from 'react';
import { ScheduleBlock } from '@/types';
import { Badge } from '@/components/ui/Badge';
import { ArrowRight, CheckCircle, XCircle } from 'lucide-react';

interface BeforeAfterViewProps {
  beforeBlocks?: ScheduleBlock[];
  afterBlocks?: ScheduleBlock[];
  corridors?: string[];
  loading?: boolean;
}

export function BeforeAfterView({ 
  beforeBlocks = [], 
  afterBlocks = [], 
  corridors = [],
  loading = false 
}: BeforeAfterViewProps) {
  const [view, setView] = useState<'before' | 'after' | 'combined'>('combined');
  const [selectedCorridor, setSelectedCorridor] = useState<string>('all');

  // Ensure we're working with arrays
  const safeBeforeBlocks = Array.isArray(beforeBlocks) ? beforeBlocks : [];
  const safeAfterBlocks = Array.isArray(afterBlocks) ? afterBlocks : [];
  const safeCorridors = Array.isArray(corridors) ? corridors : [];

  // Get unique corridors from data if not provided
  const allCorridors = useMemo(() => {
    if (safeCorridors.length > 0) return safeCorridors;
    
    const corridorSet = new Set<string>();
    [...safeBeforeBlocks, ...safeAfterBlocks].forEach(block => {
      if (block?.corridor) {
        corridorSet.add(block.corridor);
      }
    });
    return Array.from(corridorSet);
  }, [safeBeforeBlocks, safeAfterBlocks, safeCorridors]);

  const getDisplayBlocks = (blocks: ScheduleBlock[], corridor?: string) => {
    // Guard against undefined or null blocks
    if (!blocks || !Array.isArray(blocks)) {
      return [];
    }
    
    if (corridor && corridor !== 'all') {
      return blocks.filter(b => b.corridor === corridor);
    }
    return blocks;
  };

  const getBlocks = () => {
    if (view === 'before') {
      return getDisplayBlocks(safeBeforeBlocks, selectedCorridor);
    } else if (view === 'after') {
      return getDisplayBlocks(safeAfterBlocks, selectedCorridor);
    } else {
      // Combined view - show both with a visual indicator
      const before = getDisplayBlocks(safeBeforeBlocks, selectedCorridor);
      const after = getDisplayBlocks(safeAfterBlocks, selectedCorridor);
      
      // Merge and deduplicate by ID
      const merged = [...before];
      after.forEach(aBlock => {
        if (!merged.find(b => b.id === aBlock.id)) {
          merged.push(aBlock);
        }
      });
      return merged;
    }
  };

  const getBlockStatus = (blockId: string) => {
    const inBefore = safeBeforeBlocks.some(b => b.id === blockId);
    const inAfter = safeAfterBlocks.some(b => b.id === blockId);
    
    if (inBefore && inAfter) return 'unchanged';
    if (inBefore && !inAfter) return 'removed';
    if (!inBefore && inAfter) return 'added';
    return 'unknown';
  };

  const displayBlocks = getBlocks();
  const totalBefore = safeBeforeBlocks.length;
  const totalAfter = safeAfterBlocks.length;
  const addedCount = safeAfterBlocks.filter(b => !safeBeforeBlocks.some(before => before.id === b.id)).length;
  const removedCount = safeBeforeBlocks.filter(b => !safeAfterBlocks.some(after => after.id === b.id)).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Schedule Comparison</h3>
          <p className="text-sm text-gray-500">
            Before: {totalBefore} blocks · After: {totalAfter} blocks
          </p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-gray-100 rounded-md p-1">
            <button
              onClick={() => setView('before')}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                view === 'before' 
                  ? 'bg-white shadow-sm text-gray-800' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Before
            </button>
            <button
              onClick={() => setView('after')}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                view === 'after' 
                  ? 'bg-white shadow-sm text-gray-800' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              After
            </button>
            <button
              onClick={() => setView('combined')}
              className={`px-3 py-1 text-sm rounded-md transition-colors ${
                view === 'combined' 
                  ? 'bg-white shadow-sm text-gray-800' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Combined
            </button>
          </div>
          
          <select
            value={selectedCorridor}
            onChange={(e) => setSelectedCorridor(e.target.value)}
            className="text-sm border rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Corridors</option>
            {allCorridors.map(corridor => (
              <option key={corridor} value={corridor}>{corridor}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-blue-600">{totalBefore}</div>
          <div className="text-xs text-blue-700">Before</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{totalAfter}</div>
          <div className="text-xs text-green-700">After</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-purple-600">
            {addedCount > 0 ? `+${addedCount}` : '0'}
            {removedCount > 0 && ` / -${removedCount}`}
          </div>
          <div className="text-xs text-purple-700">Added / Removed</div>
        </div>
      </div>

      {/* Blocks Grid */}
      {displayBlocks.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg font-medium">No blocks to display</p>
          <p className="text-sm">Try selecting a different corridor or view</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {displayBlocks.map(block => {
            const status = getBlockStatus(block.id);
            const statusConfig = {
              unchanged: { bg: 'bg-gray-50', border: 'border-gray-200', icon: null, label: 'Unchanged' },
              added: { bg: 'bg-green-50', border: 'border-green-300', icon: <CheckCircle className="w-4 h-4 text-green-600" />, label: 'Added' },
              removed: { bg: 'bg-red-50', border: 'border-red-300', icon: <XCircle className="w-4 h-4 text-red-600" />, label: 'Removed' },
              unknown: { bg: 'bg-gray-50', border: 'border-gray-200', icon: null, label: 'Unknown' },
            };
            
            const config = statusConfig[status] || statusConfig.unknown;

            return (
              <div 
                key={block.id} 
                className={`border rounded-lg p-3 ${config.bg} ${config.border} hover:shadow-md transition-shadow`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-500">{block.id}</span>
                  <span className="text-xs flex items-center gap-1">
                    {config.icon}
                    {config.label}
                  </span>
                </div>
                <div className="text-sm font-medium text-gray-800 line-clamp-2">
                  {block.description || 'No description'}
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                  <span>{block.duration || 0}h</span>
                  <span>P{block.priority || 3}</span>
                  <span>{block.assignedTo || 'Unassigned'}</span>
                  <span>{block.corridor || 'N/A'}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}