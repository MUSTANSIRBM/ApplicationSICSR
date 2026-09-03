// src/pages/board.tsx
import { useEffect, useState } from 'react';
import { DefectList } from '@/components/board/DefectList';
import { useStore } from '@/store/useStore';
import { useAuthStore } from '@/store/useAuthStore';
import toast from 'react-hot-toast';
import { RefreshCw, LayoutGrid, Filter, Search, Plus, Calendar, Clock, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { Defect } from '@/types';
import { withAuth } from '@/hoc/withAuth';
import { format } from 'date-fns';

function BoardPage() {
  const { 
    defects, 
    loading, 
    filters, 
    searchQuery,
    selectedWeek,
    loadDefects, 
    scheduleDefect, 
    deferDefect,
    deleteDefect,
    editDefect,
    setFilters, 
    setSearchQuery,
    loadSchedule
  } = useStore();

  const { user } = useAuthStore();
  const [isScheduling, setIsScheduling] = useState<string | null>(null);
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
  const [selectedDefectId, setSelectedDefectId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  useEffect(() => {
    loadDefects();
  }, []);

  const handleSchedule = async (id: string, weekStart?: string) => {
    setIsScheduling(id);
    try {
      const targetWeek = weekStart || selectedWeek;
      await scheduleDefect(id, targetWeek);
      await loadSchedule(targetWeek);
      toast.success(`✅ Defect scheduled successfully`);
      setShowScheduleDialog(false);
      setSelectedDefectId(null);
    } catch (error: any) {
      toast.error(`❌ Failed to schedule: ${error.message || 'Unknown error'}`);
    } finally {
      setIsScheduling(null);
    }
  };

  const handleDefer = async (id: string) => {
    try {
      await deferDefect(id);
      toast.success(`⏳ Defect deferred successfully`);
    } catch (error: any) {
      toast.error(`❌ Failed to defer: ${error.message || 'Unknown error'}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm(`Delete this defect? This cannot be undone.`)) {
      try {
        await deleteDefect(id);
        toast.success(`🗑️ Defect deleted successfully`);
      } catch (error: any) {
        toast.error(`❌ Failed to delete: ${error.message || 'Unknown error'}`);
      }
    }
  };

  const handleEdit = async (id: string, updatedData: Partial<Defect>) => {
    try {
      await editDefect(id, updatedData);
      toast.success(`✏️ Defect updated successfully`);
    } catch (error: any) {
      toast.error(`❌ Failed to update: ${error.message || 'Unknown error'}`);
    }
  };

  const handleFilterChange = (newFilters: any) => {
    setFilters(newFilters);
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  const handleQuickSchedule = (id: string) => {
    handleSchedule(id, selectedWeek);
  };

  const openScheduleDialog = (id: string) => {
    setSelectedDefectId(id);
    setShowScheduleDialog(true);
  };

  const safeDefects = defects || [];
  const totalDefects = safeDefects.length;
  const criticalDefects = safeDefects.filter(d => d.tier === 'safety-critical').length;
  const deferredDefects = safeDefects.filter(d => d.status === 'deferred').length;
  const scheduledDefects = safeDefects.filter(d => d.status === 'scheduled').length;
  const newDefects = safeDefects.filter(d => d.status === 'new').length;

  // Stats cards with icons
  const stats = [
    { 
      label: 'Total Defects', 
      value: totalDefects, 
      icon: <LayoutGrid className="w-5 h-5" />,
      color: 'bg-blue-50 text-blue-600 border-blue-100',
      textColor: 'text-blue-700'
    },
    { 
      label: 'Safety Critical', 
      value: criticalDefects, 
      icon: <AlertTriangle className="w-5 h-5" />,
      color: 'bg-red-50 text-red-600 border-red-100',
      textColor: 'text-red-700'
    },
    { 
      label: 'Deferred', 
      value: deferredDefects, 
      icon: <Clock className="w-5 h-5" />,
      color: 'bg-yellow-50 text-yellow-600 border-yellow-100',
      textColor: 'text-yellow-700'
    },
    { 
      label: 'Scheduled', 
      value: scheduledDefects, 
      icon: <CheckCircle className="w-5 h-5" />,
      color: 'bg-green-50 text-green-600 border-green-100',
      textColor: 'text-green-700'
    },
    { 
      label: 'New', 
      value: newDefects, 
      icon: <Plus className="w-5 h-5" />,
      color: 'bg-purple-50 text-purple-600 border-purple-100',
      textColor: 'text-purple-700'
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center gap-3">
              📋 Board
              <span className="text-sm font-normal text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                {totalDefects} total
              </span>
            </h1>
            <p className="text-sm text-gray-500 mt-1 flex items-center gap-2">
              <span>Defect prioritization, scoring, and scheduling</span>
              {user && (
                <span className="hidden sm:inline text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                  👤 {user.name}
                </span>
              )}
            </p>
          </div>
          
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* View toggle */}
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-md transition-all ${
                  viewMode === 'grid' 
                    ? 'bg-white shadow-sm text-gray-800' 
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded-md transition-all ${
                  viewMode === 'list' 
                    ? 'bg-white shadow-sm text-gray-800' 
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                <Filter className="w-4 h-4" />
              </button>
            </div>

            <button
              onClick={() => loadDefects()}
              className="btn btn-primary btn-sm flex items-center gap-1.5"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          {stats.map((stat, index) => (
            <div 
              key={stat.label}
              className={`rounded-xl border p-3 sm:p-4 transition-all duration-200 hover:shadow-md ${stat.color} animate-fade-in`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xl sm:text-2xl font-bold">{stat.value}</div>
                  <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider opacity-70">
                    {stat.label}
                  </div>
                </div>
                <div className={`p-2 rounded-lg bg-white/50 ${stat.textColor}`}>
                  {stat.icon}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Schedule Dialog */}
        {showScheduleDialog && selectedDefectId && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl animate-scale-in">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Schedule Defect</h3>
              <p className="text-sm text-gray-600 mb-4">
                Choose when to schedule this defect. Current week: <span className="font-medium">{format(new Date(selectedWeek), 'MMM d, yyyy')}</span>
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleSchedule(selectedDefectId, selectedWeek)}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl transition-all font-medium shadow-sm hover:shadow"
                  disabled={isScheduling === selectedDefectId}
                >
                  {isScheduling === selectedDefectId ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="spinner-sm" />
                      Scheduling...
                    </span>
                  ) : (
                    'Schedule This Week'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowScheduleDialog(false);
                    setSelectedDefectId(null);
                  }}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2.5 rounded-xl transition-all font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Defect List */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="spinner" />
            <p className="text-sm text-gray-500 animate-pulse">Loading defects...</p>
          </div>
        ) : (
          <DefectList
            defects={safeDefects}
            filters={filters || {}}
            onFilterChange={handleFilterChange}
            onSchedule={handleQuickSchedule}
            onScheduleWithWeek={openScheduleDialog}
            onDefer={handleDefer}
            onDelete={handleDelete}
            onEdit={handleEdit}
            onSearch={handleSearch}
            searchQuery={searchQuery || ''}
            isScheduling={isScheduling}
            viewMode={viewMode}
          />
        )}
      </div>

      {/* Add animation keyframes to globals.css if not already present */}
      <style jsx>{`
        @keyframes scale-in {
          from {
            transform: scale(0.95);
            opacity: 0;
          }
          to {
            transform: scale(1);
            opacity: 1;
          }
        }
        .animate-scale-in {
          animation: scale-in 0.2s ease-out;
        }
      `}</style>
    </div>
  );
}

export default withAuth(BoardPage);