// src/pages/plan.tsx
import { useEffect, useState } from 'react';
import { Timeline } from '@/components/plan/Timeline';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';
import { format, startOfWeek, endOfWeek } from 'date-fns';
import { RefreshCw, Calendar as CalendarIcon, ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react';
import { withAuth } from '@/hoc/withAuth';
import { getWeekRange, getWeekNumber, DateFormats, formatDate } from '@/utils/dateUtils';

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
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="relative">
          <div className="spinner" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
          </div>
        </div>
        <p className="text-sm text-gray-500 animate-pulse">Loading schedule...</p>
      </div>
    );
  }

  const weekStart = new Date(timelineData.weekStart);
  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
  const weekNumber = getWeekNumber(weekStart);
  const weekRange = getWeekRange(weekStart);

  const totalBlocks = timelineData.blocks?.length || 0;
  const approvedBlocks = timelineData.blocks?.filter(b => b.status === 'approved').length || 0;
  const lockedBlocks = timelineData.blocks?.filter(b => b.status === 'locked').length || 0;
  const pendingBlocks = timelineData.blocks?.filter(b => b.status === 'proposed' || b.status === 'pending').length || 0;

  // Check if current week is today's week
  const isCurrentWeek = (() => {
    const today = new Date();
    const todayWeekStart = startOfWeek(today, { weekStartsOn: 1 });
    return weekStart.getTime() === todayWeekStart.getTime();
  })();

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">📅 Plan</h1>
            <span className="text-sm font-normal text-gray-500 bg-gray-100 px-3 py-1 rounded-full flex items-center gap-1.5">
              <span>Week {weekNumber}</span>
              {isCurrentWeek && (
                <span className="text-[10px] font-medium text-blue-600 bg-blue-100 px-1.5 py-0.5 rounded-full">
                  Current
                </span>
              )}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-sm text-gray-500">
              {formatDate(weekStart, DateFormats.SHORT)} – {formatDate(weekEnd, DateFormats.SHORT)}
            </p>
            <span className="text-xs text-gray-400">•</span>
            <span className="text-xs text-gray-400">
              {formatDate(weekStart, DateFormats.FULL)}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => handleWeekChange('prev')}
            className="btn btn-secondary btn-sm"
            title="Previous Week"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleGoToToday}
            className="btn btn-primary btn-sm"
            title="Go to Current Week"
          >
            <CalendarIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Today</span>
          </button>
          <button
            onClick={() => handleWeekChange('next')}
            className="btn btn-secondary btn-sm"
            title="Next Week"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="btn btn-secondary btn-sm"
            title="Refresh Schedule"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card hover:shadow-md transition-all duration-200 hover:-translate-y-0.5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-gray-900">{totalBlocks}</div>
              <div className="text-sm text-gray-500">Total Blocks</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-100/50 text-gray-600">
              <CalendarIcon className="w-5 h-5" />
            </div>
          </div>
        </div>
        <div className="card hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border-l-4 border-yellow-500">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-yellow-600">{pendingBlocks}</div>
              <div className="text-sm text-gray-500">Pending</div>
            </div>
            <div className="p-2 rounded-lg bg-yellow-50 text-yellow-600">
              <div className="w-5 h-5 rounded-full border-2 border-yellow-500 border-t-transparent animate-spin" />
            </div>
          </div>
        </div>
        <div className="card hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-blue-600">{approvedBlocks}</div>
              <div className="text-sm text-gray-500">Approved</div>
            </div>
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>
        <div className="card hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 border-l-4 border-green-500">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-green-600">{lockedBlocks}</div>
              <div className="text-sm text-gray-500">Locked</div>
            </div>
            <div className="p-2 rounded-lg bg-green-50 text-green-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-soft border border-gray-200/60 overflow-hidden">
        <div className="px-6 py-3 border-b border-gray-200/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">📋 Schedule Timeline</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              {totalBlocks} blocks
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              Pending
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Approved
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              Locked
            </span>
          </div>
        </div>
        <div className="p-4">
          <Timeline 
            data={timelineData} 
            onApprove={handleApprove} 
            onLock={handleLock}
            onDelete={handleDelete}
            onEdit={handleEdit}
          />
        </div>
      </div>
    </div>
  );
}

export default withAuth(PlanPage);