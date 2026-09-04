// src/pages/board.tsx
import { useEffect, useState } from 'react';
import { DefectList } from '@/components/board/DefectList';
import { useStore } from '@/store/useStore';
import { useAuthStore } from '@/store/useAuthStore';
import toast from 'react-hot-toast';
import { RefreshCw, LayoutGrid, Filter, Plus, X, Check, Clock, AlertTriangle, Calendar } from 'lucide-react';
import { Defect } from '@/types';
import { withAuth } from '@/hoc/withAuth';
import { format, addDays } from 'date-fns';

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
    createDefect,
    setFilters,
    setSearchQuery,
    loadSchedule
  } = useStore();

  const { user } = useAuthStore();
  const [isScheduling, setIsScheduling] = useState<string | null>(null);
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
  const [selectedDefectId, setSelectedDefectId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Create Defect Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newDefect, setNewDefect] = useState<Partial<Defect>>({
    department: 'track',
    corridor: '',
    description: '',
    severity: 50,
    tier: 'normal',
    impactScore: 50,
    overdueDays: 0,
    trafficImpact: 50,
    status: 'new',
    scheduledWeek: '',
  });
  const [createErrors, setCreateErrors] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    loadDefects();
  }, []);

  const safeDefects = defects || [];
  const totalDefects = safeDefects.length;
  const criticalDefects = safeDefects.filter(d => d.tier === 'safety-critical').length;
  const deferredDefects = safeDefects.filter(d => d.status === 'deferred').length;
  const scheduledDefects = safeDefects.filter(d => d.status === 'scheduled').length;
  const newDefectsCount = safeDefects.filter(d => d.status === 'new').length;

  // ============================================
  // HANDLER FUNCTIONS
  // ============================================

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

  const handleCreateDefect = async () => {
    const errors: { [key: string]: string } = {};
    if (!newDefect.description?.trim()) {
      errors.description = 'Description is required';
    }
    if (!newDefect.corridor?.trim()) {
      errors.corridor = 'Corridor is required';
    }

    if (Object.keys(errors).length > 0) {
      setCreateErrors(errors);
      return;
    }

    try {
      await createDefect(newDefect as Omit<Defect, 'id' | 'createdAt' | 'score'>);
      toast.success('✅ Defect created successfully');
      setShowCreateModal(false);
      setNewDefect({
        department: 'track',
        corridor: '',
        description: '',
        severity: 50,
        tier: 'normal',
        impactScore: 50,
        overdueDays: 0,
        trafficImpact: 50,
        status: 'new',
        scheduledWeek: '',
      });
      setCreateErrors({});
      await loadDefects();
    } catch (error: any) {
      toast.error(`❌ Failed to create defect: ${error.message || 'Unknown error'}`);
    }
  };

  // Get week range for display
  const getWeekRange = (weekStart: string) => {
    const start = new Date(weekStart);
    const end = addDays(start, 6);
    return {
      start: format(start, 'MMM d, yyyy'),
      end: format(end, 'MMM d, yyyy')
    };
  };

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
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">New Defect</span>
            </button>

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
              className="btn btn-secondary btn-sm flex items-center gap-1.5"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          <div className="rounded-xl border bg-blue-50 border-blue-100 p-3 sm:p-4 transition-all hover:shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-blue-700">{totalDefects}</div>
                <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider text-blue-600/70">Total Defects</div>
              </div>
              <div className="p-2 rounded-lg bg-white/50 text-blue-600">
                <LayoutGrid className="w-5 h-5" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-red-50 border-red-100 p-3 sm:p-4 transition-all hover:shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-red-700">{criticalDefects}</div>
                <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider text-red-600/70">Safety Critical</div>
              </div>
              <div className="p-2 rounded-lg bg-white/50 text-red-600">
                <AlertTriangle className="w-5 h-5" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-yellow-50 border-yellow-100 p-3 sm:p-4 transition-all hover:shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-yellow-700">{deferredDefects}</div>
                <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider text-yellow-600/70">Deferred</div>
              </div>
              <div className="p-2 rounded-lg bg-white/50 text-yellow-600">
                <Clock className="w-5 h-5" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-green-50 border-green-100 p-3 sm:p-4 transition-all hover:shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-green-700">{scheduledDefects}</div>
                <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider text-green-600/70">Scheduled</div>
              </div>
              <div className="p-2 rounded-lg bg-white/50 text-green-600">
                <Check className="w-5 h-5" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border bg-purple-50 border-purple-100 p-3 sm:p-4 transition-all hover:shadow-md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-bold text-purple-700">{newDefectsCount}</div>
                <div className="text-[10px] sm:text-xs font-medium uppercase tracking-wider text-purple-600/70">New</div>
              </div>
              <div className="p-2 rounded-lg bg-white/50 text-purple-600">
                <Plus className="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>

        {/* Create Defect Modal with Enhanced Date Section */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
            <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto animate-scale-in">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-gray-900">Create New Defect</h3>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setCreateErrors({});
                  }}
                  className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                {/* Description */}
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">
                    Description <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={newDefect.description || ''}
                    onChange={(e) => {
                      setNewDefect({ ...newDefect, description: e.target.value });
                      if (createErrors.description) setCreateErrors({ ...createErrors, description: '' });
                    }}
                    className={`w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all ${
                      createErrors.description ? 'border-red-500' : 'border-gray-300'
                    }`}
                    rows={3}
                    placeholder="Describe the defect..."
                  />
                  {createErrors.description && (
                    <p className="mt-1 text-sm text-red-500">{createErrors.description}</p>
                  )}
                </div>

                {/* Department & Corridor */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      Department <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={newDefect.department || 'track'}
                      onChange={(e) => setNewDefect({ ...newDefect, department: e.target.value as any })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    >
                      <option value="track">Track</option>
                      <option value="power">Power</option>
                      <option value="signals">Signals</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      Corridor <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={newDefect.corridor || ''}
                      onChange={(e) => {
                        setNewDefect({ ...newDefect, corridor: e.target.value });
                        if (createErrors.corridor) setCreateErrors({ ...createErrors, corridor: '' });
                      }}
                      className={`w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all ${
                        createErrors.corridor ? 'border-red-500' : 'border-gray-300'
                      }`}
                      placeholder="e.g., A-12"
                    />
                    {createErrors.corridor && (
                      <p className="mt-1 text-sm text-red-500">{createErrors.corridor}</p>
                    )}
                  </div>
                </div>

                {/* Tier & Impact Score */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Tier</label>
                    <select
                      value={newDefect.tier || 'normal'}
                      onChange={(e) => setNewDefect({ ...newDefect, tier: e.target.value as any })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                    >
                      <option value="safety-critical">Safety Critical</option>
                      <option value="high">High</option>
                      <option value="normal">Normal</option>
                      <option value="deferred">Deferred</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Impact Score</label>
                    <input
                      type="number"
                      value={newDefect.impactScore || 50}
                      onChange={(e) => setNewDefect({ ...newDefect, impactScore: parseInt(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                      min="0"
                      max="100"
                    />
                  </div>
                </div>

                {/* Severity & Traffic Impact */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Severity</label>
                    <input
                      type="number"
                      value={newDefect.severity || 50}
                      onChange={(e) => setNewDefect({ ...newDefect, severity: parseInt(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                      min="0"
                      max="100"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Traffic Impact</label>
                    <input
                      type="number"
                      value={newDefect.trafficImpact || 50}
                      onChange={(e) => setNewDefect({ ...newDefect, trafficImpact: parseInt(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                      min="0"
                      max="100"
                    />
                  </div>
                </div>

                {/* Overdue Days & Scheduled Week - ENHANCED */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      Overdue Days
                      <span className="ml-1 text-xs text-gray-400">(optional)</span>
                    </label>
                    <input
                      type="number"
                      value={newDefect.overdueDays || 0}
                      onChange={(e) => setNewDefect({ ...newDefect, overdueDays: parseInt(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                      min="0"
                    />
                    {newDefect.overdueDays && newDefect.overdueDays > 0 && (
                      <p className={`mt-1 text-xs flex items-center gap-1 ${
                        newDefect.overdueDays <= 7 ? 'text-yellow-600' : 
                        newDefect.overdueDays <= 14 ? 'text-orange-600' : 'text-red-600'
                      }`}>
                        <AlertTriangle className="w-3 h-3" />
                        {newDefect.overdueDays} days overdue
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">
                      Scheduled Date
                      <span className="ml-1 text-xs text-gray-400">(optional)</span>
                    </label>
                    <div className="relative">
                      <input
                        type="date"
                        value={newDefect.scheduledWeek || ''}
                        onChange={(e) => setNewDefect({ ...newDefect, scheduledWeek: e.target.value })}
                        className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all pr-10"
                      />
                      <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                    </div>
                    {newDefect.scheduledWeek && (
                      <p className="mt-1 text-xs text-blue-600 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Week of {format(new Date(newDefect.scheduledWeek), 'MMM d, yyyy')}
                      </p>
                    )}
                  </div>
                </div>

                {/* Status */}
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Status</label>
                  <select
                    value={newDefect.status || 'new'}
                    onChange={(e) => setNewDefect({ ...newDefect, status: e.target.value as any })}
                    className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                  >
                    <option value="new">New</option>
                    <option value="scored">Scored</option>
                    <option value="scheduled">Scheduled</option>
                    <option value="approved">Approved</option>
                    <option value="completed">Completed</option>
                    <option value="deferred">Deferred</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6 pt-4 border-t border-gray-200">
                <button
                  onClick={handleCreateDefect}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl font-medium transition-all shadow-sm hover:shadow flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Create Defect
                </button>
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setCreateErrors({});
                  }}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2.5 rounded-xl font-medium transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Schedule Dialog - ENHANCED */}
        {showScheduleDialog && selectedDefectId && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl animate-scale-in">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-500" />
                  Schedule Defect
                </h3>
                <button
                  onClick={() => {
                    setShowScheduleDialog(false);
                    setSelectedDefectId(null);
                  }}
                  className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-200/50">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Calendar className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-xs text-blue-600 font-medium">Current Week</p>
                      <p className="text-sm text-blue-800 font-semibold">
                        {getWeekRange(selectedWeek).start} – {getWeekRange(selectedWeek).end}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => handleSchedule(selectedDefectId, selectedWeek)}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl transition-all font-medium shadow-sm hover:shadow flex items-center justify-center gap-2"
                    disabled={isScheduling === selectedDefectId}
                  >
                    {isScheduling === selectedDefectId ? (
                      <>
                        <span className="spinner-sm" />
                        Scheduling...
                      </>
                    ) : (
                      <>
                        <Calendar className="w-4 h-4" />
                        Schedule This Week
                      </>
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

                <p className="text-xs text-gray-400 text-center">
                  The defect will be added to the selected week's schedule
                </p>
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
            onCreateDefect={() => setShowCreateModal(true)}
          />
        )}
      </div>
    </div>
  );
}

export default withAuth(BoardPage);