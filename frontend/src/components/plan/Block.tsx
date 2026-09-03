// frontend/src/components/plan/Block.tsx
import { useState } from 'react';
import { clsx } from 'clsx';
import { ScheduleBlock } from '@/types';

interface BlockProps {
  block: ScheduleBlock;
  onClick: () => void;
}

const departmentColors = {
  track: 'bg-track/30 border-track hover:bg-track/40',
  power: 'bg-power/30 border-power hover:bg-power/40',
  signals: 'bg-signals/30 border-signals hover:bg-signals/40',
  combined: 'bg-combined/30 border-combined hover:bg-combined/40',
};

const statusColors = {
  proposed: 'border-l-4',
  approved: 'border-l-4 border-green-500',
  locked: 'border-l-4 border-blue-500',
  executed: 'border-l-4 border-gray-400',
};

export function Block({ block, onClick }: BlockProps) {
  const [isHovered, setIsHovered] = useState(false);
  const start = new Date(block.startTime);
  const end = new Date(block.endTime);
  const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60);

  const width = Math.max(duration * 24, 24);

  return (
    <div
      className={clsx(
        'absolute rounded-md text-xs transition-all cursor-pointer group',
        'border shadow-sm',
        departmentColors[block.department],
        statusColors[block.status],
        isHovered && 'shadow-md z-10'
      )}
      style={{
        left: `${(start.getHours() - 6) * 24}px`,
        top: '4px',
        width: `${width}px`,
        height: '44px',
      }}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="px-1.5 py-0.5 truncate text-[10px] font-medium">
        {block.defects.map(d => d.department).join('+')}
        <span className="ml-1 text-gray-500">{duration.toFixed(1)}h</span>
      </div>
      {block.isCombined && (
        <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-combined border border-white" />
      )}
    </div>
  );
}