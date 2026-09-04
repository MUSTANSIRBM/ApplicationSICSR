// src/components/board/DefectList.tsx
import { useState, useEffect, useMemo, useRef } from 'react';
import { clsx } from 'clsx';
import { Defect, FilterParams } from '@/types';
import { DefectCard } from './DefectCard';
import { Badge } from '@/components/ui/Badge';
import { Search, X, Filter, AlertTriangle, Plus, Check, Calendar, Clock } from 'lucide-react';
import { format } from 'date-fns';

interface DefectListProps {
  defects: Defect[];
  filters: FilterParams;
  onFilterChange: (filters: FilterParams) => void;
  onSchedule: (id: string) => void;
  onScheduleWithWeek: (id: string) => void;
  onDefer: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (id: string, data: Partial<Defect>) => void;
  onSearch: (query: string) => void;
  searchQuery: string;
  isScheduling?: string | null;
  viewMode?: 'grid' | 'list';
  onCreateDefect?: () => void;
}

const departments = ['all', 'track', 'power', 'signals'] as const;
const tiers = ['all', 'safety-critical', 'high', 'normal', 'deferred'] as const;

export function DefectList({ 
  defects = [],
  filters = {},
  onFilterChange, 
  onSchedule, 
  onScheduleWithWeek,
  onDefer,
  onDelete,
  onEdit,
  onSearch,
  searchQuery = '',
  isScheduling,
  viewMode = 'grid',
  onCreateDefect
}: DefectListProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery || '');
  const [isSearching, setIsSearching] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<Defect>>({});
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setLocalSearch(searchQuery || '');
  }, [searchQuery]);

  // Search handlers
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      performSearch(localSearch);
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      setLocalSearch('');
      performSearch('');
      inputRef.current?.blur();
    }
  };

  const performSearch = (query: string) => {
    setIsSearching(true);
    onSearch(query);
    setTimeout(() => setIsSearching(false), 300);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalSearch(value);
    if (value === '') {
      performSearch('');
    }
  };

  const handleSearchClick = () => {
    performSearch(localSearch);
  };

  const handleClearSearch = () => {
    setLocalSearch('');
    performSearch('');
    inputRef.current?.focus();
  };

  // Edit handlers with schedule fields
  const handleEditStart = (defect: Defect) => {
    setEditingId(defect.id);
    setEditData({
      description: defect.description || '',
      department: defect.department || 'track',
      corridor: defect.corridor || '',
      tier: defect.tier || 'normal',
      impactScore: defect.impactScore || defect.score || 50,
      severity: defect.severity || 50,
      overdueDays: defect.overdueDays || 0,
      trafficImpact: defect.trafficImpact || 50,
      scheduledWeek: defect.scheduledWeek || '',
      status: defect.status || 'new',
    });
  };

  const handleEditSave = (id: string) => {
    const updatedData: Partial<Defect> = {};
    
    const originalDefect = defects.find(d => d.id === id);
    if (!originalDefect) return;

    if (editData.description !== undefined && editData.description !== originalDefect.description) {
      updatedData.description = editData.description;
    }
    if (editData.department !== undefined && editData.department !== originalDefect.department) {
      updatedData.department = editData.department as any;
    }
    if (editData.corridor !== undefined && editData.corridor !== originalDefect.corridor) {
      updatedData.corridor = editData.corridor;
    }
    if (editData.tier !== undefined && editData.tier !== originalDefect.tier) {
      updatedData.tier = editData.tier as any;
    }
    if (editData.impactScore !== undefined && editData.impactScore !== originalDefect.impactScore) {
      updatedData.impactScore = editData.impactScore;
    }
    if (editData.severity !== undefined && editData.severity !== originalDefect.severity) {
      updatedData.severity = editData.severity;
    }
    if (editData.overdueDays !== undefined && editData.overdueDays !== originalDefect.overdueDays) {
      updatedData.overdueDays = editData.overdueDays;
    }
    if (editData.trafficImpact !== undefined && editData.trafficImpact !== originalDefect.trafficImpact) {
      updatedData.trafficImpact = editData.trafficImpact;
    }
    if (editData.scheduledWeek !== undefined && editData.scheduledWeek !== originalDefect.scheduledWeek) {
      updatedData.scheduledWeek = editData.scheduledWeek;
    }
    if (editData.status !== undefined && editData.status !== originalDefect.status) {
      updatedData.status = editData.status as any;
    }

    if (Object.keys(updatedData).length > 0) {
      onEdit(id, updatedData);
    }
    
    setEditingId(null);
    setEditData({});
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditData({});
  };

  // Data processing
  const safeDefects = Array.isArray(defects) ? defects : [];
  
  const sortedDefects = useMemo(() => {
    const severityOrder = { 'safety-critical': 4, high: 3, normal: 2, deferred: 1 };
    return [...safeDefects].sort((a, b) => {
      const tierDiff = (severityOrder[b.tier] || 0) - (severityOrder[a.tier] || 0);
      if (tierDiff !== 0) return tierDiff;
      return (b.impactScore || 0) - (a.impactScore || 0);
    });
  }, [safeDefects]);

  const groupedDefects = sortedDefects.reduce((acc, d) => {
    const tier = d.tier || 'normal';
    if (!acc[tier]) acc[tier] = [];
    acc[tier].push(d);
    return acc;
  }, {} as Record<string, Defect[]>);

  const tierOrder = ['safety-critical', 'high', 'normal', 'deferred'];

  const getTierDisplay = (tier: string) => {
    const map: Record<string, string> = {
      'safety-critical': 'Safety Critical',
      'high': 'High',
      'normal': 'Normal',
      'deferred': 'Deferred'
    };
    return map[tier] || tier;
  };

  const totalDefects = safeDefects.length;
  const criticalCount = safeDefects.filter(d => d.tier === 'safety-critical').length;

  // Format date for input
  const formatDateForInput = (dateString?: string) => {
    if (!dateString) return '';
    try {
      return format(new Date(dateString), 'yyyy-MM-dd');
    } catch {
      return '';
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and filters */}
      <div className="bg-white rounded-xl border border-gray-200/80 p-3 sm:p-4 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Search by ID, description, or department..."
                value={localSearch}
                onChange={handleSearchChange}
                onKeyDown={handleKeyDown}
                className={clsx(
                  "w-full pl-9 pr-28 py-2.5 text-sm border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
                  isSearching ? "bg-gray-50" : "bg-white",
                  localSearch ? "border-blue-300" : "border-gray-200"
                )}
              />
              <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {localSearch && (
                  <button
                    onClick={handleClearSearch}
                    className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={handleSearchClick}
                  className={clsx(
                    "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                    localSearch 
                      ? "bg-blue-600 text-white hover:bg-blue-700" 
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  )}
                  disabled={!localSearch}
                >
                  Search
                </button>
              </div>
            </div>
            {searchQuery && (
              <div className="mt-1.5 px-1">
                <span className="text-xs text-gray-500">
                  Found <span className="font-medium text-gray-700">{totalDefects}</span> results for "<span className="font-medium text-gray-700">{searchQuery}</span>"
                </span>
              </div>
            )}
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400 font-medium mr-1">Dept:</span>
              {departments.map((dept) => (
                <button
                  key={dept}
                  onClick={() => {
                    const newFilters = { 
                      ...filters, 
                      department: dept === 'all' ? undefined : dept 
                    };
                    if (searchQuery) {
                      newFilters.search = searchQuery;
                    }
                    onFilterChange(newFilters);
                  }}
                  className={clsx(
                    'px-2.5 py-1 text-xs font-medium rounded-lg transition-all capitalize',
                    (filters.department === dept || (dept === 'all' && !filters.department))
                      ? 'bg-blue-100 text-blue-700 shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {dept}
                </button>
              ))}
            </div>
            
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400 font-medium mr-1">Tier:</span>
              {tiers.map((tier) => (
                <button
                  key={tier}
                  onClick={() => {
                    const newFilters = { 
                      ...filters, 
                      tier: tier === 'all' ? undefined : tier 
                    };
                    if (searchQuery) {
                      newFilters.search = searchQuery;
                    }
                    onFilterChange(newFilters);
                  }}
                  className={clsx(
                    'px-2.5 py-1 text-xs font-medium rounded-lg transition-all capitalize',
                    (filters.tier === tier || (tier === 'all' && !filters.tier))
                      ? 'bg-blue-100 text-blue-700 shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                >
                  {tier === 'safety-critical' ? 'Critical' : tier.replace('-', ' ')}
                </button>
              ))}
            </div>

            {onCreateDefect && (
              <button
                onClick={onCreateDefect}
                className="ml-2 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm hover:shadow flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                New Defect
              </button>
            )}
          </div>
        </div>
        
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
          <span className="text-xs text-gray-500">
            {totalDefects} defects · {criticalCount} critical
          </span>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>⌘K</span>
            <span className="text-gray-300">|</span>
            <span>Esc to clear</span>
          </div>
        </div>
      </div>

      {/* Defect grid with equal heights */}
      <div className={clsx(
        'gap-4',
        viewMode === 'grid' 
          ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3' 
          : 'grid grid-cols-1'
      )}>
        {tierOrder.map((tier: string) => {
          const items = groupedDefects[tier] || [];
          if (items.length === 0) return null;
          
          return (
            <div key={tier} className="contents">
              {/* Group header */}
              <div className="col-span-full flex items-center gap-2 pt-3 pb-2">
                <div className="flex items-center gap-2">
                  <Badge variant={tier as any} size="md" className="text-sm font-semibold">
                    {getTierDisplay(tier)}
                  </Badge>
                  <span className="text-xs text-gray-400 font-medium bg-gray-100 px-2 py-0.5 rounded-full">
                    {items.length}
                  </span>
                </div>
                {tier === 'safety-critical' && (
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                )}
                <div className="flex-1 h-px bg-gradient-to-r from-gray-200 to-transparent" />
              </div>
              
              {/* Cards grid with equal heights */}
              <div className={clsx(
                'col-span-full',
                viewMode === 'grid' 
                  ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4' 
                  : 'grid grid-cols-1 gap-3'
              )}>
                {items.map((defect: Defect) => (
                  <div key={defect.id} className="h-full">
                    {editingId === defect.id ? (
                      <div className="bg-white rounded-xl shadow-lg border border-blue-300 p-4 sm:p-5 h-full">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="text-sm font-semibold text-gray-700">Edit Defect #{defect.id}</h4>
                          <button
                            onClick={handleEditCancel}
                            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                        <div className="space-y-3">
                          <div>
                            <label className="text-xs font-medium text-gray-600 block mb-1">Description *</label>
                            <textarea
                              value={editData.description || ''}
                              onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                              className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                              rows={2}
                              placeholder="Defect description"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Department *</label>
                              <select
                                value={editData.department || 'track'}
                                onChange={(e) => setEditData({ ...editData, department: e.target.value as any })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                              >
                                <option value="track">Track</option>
                                <option value="power">Power</option>
                                <option value="signals">Signals</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Corridor *</label>
                              <input
                                type="text"
                                value={editData.corridor || ''}
                                onChange={(e) => setEditData({ ...editData, corridor: e.target.value })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                placeholder="e.g., A-12"
                              />
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Tier *</label>
                              <select
                                value={editData.tier || 'normal'}
                                onChange={(e) => setEditData({ ...editData, tier: e.target.value as any })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                              >
                                <option value="safety-critical">Safety Critical</option>
                                <option value="high">High</option>
                                <option value="normal">Normal</option>
                                <option value="deferred">Deferred</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Impact Score</label>
                              <input
                                type="number"
                                value={editData.impactScore || 0}
                                onChange={(e) => setEditData({ ...editData, impactScore: parseInt(e.target.value) || 0 })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                min="0"
                                max="100"
                              />
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Severity</label>
                              <input
                                type="number"
                                value={editData.severity || 0}
                                onChange={(e) => setEditData({ ...editData, severity: parseInt(e.target.value) || 0 })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                min="0"
                                max="100"
                              />
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Traffic Impact</label>
                              <input
                                type="number"
                                value={editData.trafficImpact || 0}
                                onChange={(e) => setEditData({ ...editData, trafficImpact: parseInt(e.target.value) || 0 })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                min="0"
                                max="100"
                              />
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Overdue Days</label>
                              <input
                                type="number"
                                value={editData.overdueDays || 0}
                                onChange={(e) => setEditData({ ...editData, overdueDays: parseInt(e.target.value) || 0 })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                                min="0"
                              />
                            </div>
                            <div>
                              <label className="text-xs font-medium text-gray-600 block mb-1">Scheduled Date</label>
                              <input
                                type="date"
                                value={formatDateForInput(editData.scheduledWeek)}
                                onChange={(e) => setEditData({ ...editData, scheduledWeek: e.target.value })}
                                className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-gray-600 block mb-1">Status</label>
                            <select
                              value={editData.status || 'new'}
                              onChange={(e) => setEditData({ ...editData, status: e.target.value as any })}
                              className="w-full text-sm border rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                            >
                              <option value="new">New</option>
                              <option value="scored">Scored</option>
                              <option value="scheduled">Scheduled</option>
                              <option value="approved">Approved</option>
                              <option value="completed">Completed</option>
                              <option value="deferred">Deferred</option>
                            </select>
                          </div>
                          <div className="flex gap-2 pt-1">
                            <button
                              onClick={() => handleEditSave(defect.id)}
                              className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all shadow-sm hover:shadow flex items-center justify-center gap-2"
                            >
                              <Check className="w-4 h-4" />
                              Save Changes
                            </button>
                            <button
                              onClick={handleEditCancel}
                              className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <DefectCard
                        defect={defect}
                        onSchedule={onSchedule}
                        onScheduleWithWeek={onScheduleWithWeek}
                        onDefer={onDefer}
                        onDelete={onDelete}
                        onEdit={() => handleEditStart(defect)}
                        isScheduling={isScheduling === defect.id}
                        compact={viewMode === 'list'}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {totalDefects === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-lg font-medium text-gray-700">No defects found</p>
          <p className="text-sm text-gray-400 mt-1">Try adjusting your filters or search criteria</p>
          {onCreateDefect && (
            <button
              onClick={onCreateDefect}
              className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2 mx-auto"
            >
              <Plus className="w-4 h-4" />
              Create your first defect
            </button>
          )}
        </div>
      )}
    </div>
  );
}