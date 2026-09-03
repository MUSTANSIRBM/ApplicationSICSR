// src/pages/plan.tsx
import { useEffect, useState } from 'react';
import { Timeline } from '@/components/plan/Timeline';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export default function PlanPage() {
  const { 
    timelineData, 
    loading, 
    selectedWeek,
    loadSchedule, 
    approveBlock, 
    lockBlock,
    setSelectedWeek 
  } = useStore();

  const [weekInput, setWeekInput] = useState('');

  useEffect(() => {
    // Set initial week
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - today.getDay());
    setWeekInput(start.toISOString());
    loadSchedule(start.toISOString());
  }, []);

  const handleWeekChange = (direction: 'prev' | 'next') => {
    const current = new Date(selectedWeek);
    current.setDate(current.getDate() + (direction === 'next' ? 7 : -7));
    const newWeek = current.toISOString();
    setWeekInput(newWeek);
    setSelectedWeek(newWeek);
  };

  const handleApprove = async (id: string) => {
    try {
      await approveBlock(id);
      toast.success(`✅ Block ${id} approved`);
    } catch (error) {
      toast.error('❌ Failed to approve block');
    }
  };

  const handleLock = async (id: string) => {
    try {
      await lockBlock(id);
      toast.success(`🔒 Block ${id} locked`);
    } catch (error) {
      toast.error('❌ Failed to lock block');
    }
  };

  if (loading || !timelineData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8" />
      </div>
    );
  }

  const weekStart = new Date(timelineData.weekStart);
  const weekEnd = new Date(timelineData.weekEnd);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plan</h1>
          <p className="text-sm text-gray-500">
            Week of {format(weekStart, 'MMM d, yyyy')} – {format(weekEnd, 'MMM d, yyyy')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleWeekChange('prev')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          >
            ← Prev
          </button>
          <button
            onClick={() => {
              const today = new Date();
              const start = new Date(today);
              start.setDate(today.getDate() - today.getDay());
              const newWeek = start.toISOString();
              setWeekInput(newWeek);
              setSelectedWeek(newWeek);
            }}
            className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md transition-colors"
          >
            Today
          </button>
          <button
            onClick={() => handleWeekChange('next')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          >
            Next →
          </button>
          <div className="text-sm text-gray-500 ml-2">
            {timelineData.blocks.length} blocks · {timelineData.blocks.filter(b => b.isCombined).length} combined
          </div>
        </div>
      </div>

      <Timeline 
        data={timelineData} 
        onApprove={handleApprove} 
        onLock={handleLock} 
      />
    </div>
  );
}