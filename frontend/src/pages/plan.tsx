// src/pages/plan.tsx
import { useEffect, useState } from 'react';
import { Timeline } from '@/components/plan/Timeline';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';
import { format, startOfWeek, endOfWeek } from 'date-fns';
import { RefreshCw, Calendar as CalendarIcon, ChevronLeft, ChevronRight } from 'lucide-react';
import { withAuth } from '@/hoc/withAuth';

function PlanPage() {
  const { 
    timelineData, 
    loading, 
    selectedWeek,
    loadSchedule, 
    approveBlock, 
    lockBlock,
    deleteBlock,
    editBlock,
    setSelectedWeek,
  } = useStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    const today = new Date();
    const weekStart = startOfWeek(today, { weekStartsOn: 1 });
    loadSchedule(weekStart.toISOString());
  }, []);

  const handleWeekChange = (direction: 'prev' | 'next') => {
    const current = new Date(selectedWeek);
    current.setDate(current.getDate() + (direction === 'next' ? 7 : -7));
    setSelectedWeek(current.toISOString());
  };

  const handleGoToToday = () => {
    const today = new Date();
    const weekStart = startOfWeek(today, { weekStartsOn: 1 });
    setSelectedWeek(weekStart.toISOString());
  };

  const handleApprove = async (id: string) => {
    try {
      await approveBlock(id);
      toast.success('✅ Block approved successfully');
    } catch (error) {
      toast.error('❌ Failed to approve block');
    }
  };

  const handleLock = async (id: string) => {
    try {
      await lockBlock(id);
      toast.success('🔒 Block locked successfully');
    } catch (error) {
      toast.error('❌ Failed to lock block');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this block? This action cannot be undone.')) return;
    
    try {
      await deleteBlock(id);
      toast.success('🗑️ Block deleted successfully');
    } catch (error) {
      toast.error('❌ Failed to delete block');
    }
  };

  const handleEdit = async (id: string, updatedData: any) => {
    try {
      await editBlock(id, updatedData);
      toast.success('✏️ Block updated successfully');
    } catch (error) {
      toast.error('❌ Failed to update block');
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await loadSchedule(selectedWeek);
      toast.success('🔄 Schedule refreshed');
    } catch (error) {
      toast.error('❌ Failed to refresh schedule');
    } finally {
      setIsRefreshing(false);
    }
  };

  if (loading || !timelineData) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="spinner" />
        <p className="text-sm text-gray-500 animate-pulse">Loading schedule...</p>
      </div>
    );
  }

  const weekStart = new Date(timelineData.weekStart);
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });

  const totalBlocks = timelineData.blocks?.length || 0;
  const approvedBlocks = timelineData.blocks?.filter(b => b.status === 'approved').length || 0;
  const lockedBlocks = timelineData.blocks?.filter(b => b.status === 'locked').length || 0;
  const pendingBlocks = timelineData.blocks?.filter(b => b.status === 'proposed').length || 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
            📅 Plan
            <span className="text-sm font-normal text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              Week {format(weekStart, 'w')}
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {format(weekStart, 'MMM d, yyyy')} – {format(weekEnd, 'MMM d, yyyy')}
          </p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => handleWeekChange('prev')}
            className="btn btn-secondary btn-sm"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleGoToToday}
            className="btn btn-primary btn-sm"
          >
            <CalendarIcon className="w-4 h-4" />
            Today
          </button>
          <button
            onClick={() => handleWeekChange('next')}
            className="btn btn-secondary btn-sm"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="btn btn-secondary btn-sm"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card hover:shadow-md transition-shadow">
          <div className="text-2xl font-bold text-gray-900">{totalBlocks}</div>
          <div className="text-sm text-gray-500">Total Blocks</div>
        </div>
        <div className="card hover:shadow-md transition-shadow border-l-4 border-yellow-500">
          <div className="text-2xl font-bold text-yellow-600">{pendingBlocks}</div>
          <div className="text-sm text-gray-500">Pending</div>
        </div>
        <div className="card hover:shadow-md transition-shadow border-l-4 border-blue-500">
          <div className="text-2xl font-bold text-blue-600">{approvedBlocks}</div>
          <div className="text-sm text-gray-500">Approved</div>
        </div>
        <div className="card hover:shadow-md transition-shadow border-l-4 border-green-500">
          <div className="text-2xl font-bold text-green-600">{lockedBlocks}</div>
          <div className="text-sm text-gray-500">Locked</div>
        </div>
      </div>

      {/* Timeline */}
      <Timeline 
        data={timelineData} 
        onApprove={handleApprove} 
        onLock={handleLock}
        onDelete={handleDelete}
        onEdit={handleEdit}
      />
    </div>
  );
}
export default withAuth(PlanPage);  
