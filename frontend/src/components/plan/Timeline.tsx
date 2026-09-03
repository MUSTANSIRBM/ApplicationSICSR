// frontend/src/components/plan/Timeline.tsx
import { useState } from 'react';
import { format, startOfWeek, addDays, addHours, isSameDay, differenceInMinutes } from 'date-fns';
import { TimelineData, ScheduleBlock } from '@/types';
import { Block } from './Block';
import { BlockDetailPanel } from './BlockDetailPanel';

interface TimelineProps {
  data: TimelineData;
  onApprove?: (id: string) => void;
  onLock?: (id: string) => void;
}

export function Timeline({ data, onApprove, onLock }: TimelineProps) {
  const [selectedBlock, setSelectedBlock] = useState<ScheduleBlock | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const weekStart = new Date(data.weekStart);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const hours = Array.from({ length: 14 }, (_, i) => addHours(weekStart, 6 + i));

  const getBlocksForCell = (corridor: string, day: Date, hour: Date): ScheduleBlock[] => {
    return data.blocks.filter(block => {
      const start = new Date(block.startTime);
      const end = new Date(block.endTime);
      return block.corridor === corridor && isSameDay(start, day) && start <= hour && end > hour;
    });
  };

  const handleBlockClick = (block: ScheduleBlock) => {
    setSelectedBlock(block);
    setPanelOpen(true);
  };

  return (
    <div className="relative">
      <div className="timeline-container">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-20 bg-white w-24 border-b border-gray-200 p-2 text-left text-xs font-medium text-gray-500">
                Corridor
              </th>
              {days.map((day, i) => (
                <th key={i} className="border-b border-gray-200 p-2 text-center min-w-[120px]">
                  <div className="text-xs font-medium text-gray-700">
                    {format(day, 'EEE')}
                  </div>
                  <div className="text-xs text-gray-400">
                    {format(day, 'MMM d')}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.corridors.map((corridor, rowIdx) => (
              <tr key={rowIdx}>
                <td className="sticky left-0 z-10 bg-white border-b border-gray-200 p-2 text-sm font-medium text-gray-700">
                  {corridor}
                </td>
                {days.map((day, colIdx) => (
                  <td key={colIdx} className="relative border-b border-r border-gray-100 p-0 h-16 align-top">
                    <div className="relative h-full min-h-[64px]">
                      {hours.map((hour, hourIdx) => {
                        const blocks = getBlocksForCell(corridor, day, hour);
                        const hasTrain = data.trainSlots.some(t => 
                          t.corridor === corridor && isSameDay(new Date(t.startTime), day)
                        );
                        
                        return (
                          <div key={hourIdx} className="absolute inset-0">
                            {blocks.map(block => (
                              <Block
                                key={block.id}
                                block={block}
                                onClick={() => handleBlockClick(block)}
                              />
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <BlockDetailPanel
        block={selectedBlock}
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
        onApprove={onApprove}
        onLock={onLock}
      />
    </div>
  );
}