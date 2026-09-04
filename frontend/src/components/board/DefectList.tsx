// src/components/board/DefectList.tsx
import { useState } from 'react';

interface Defect {
  id: string;
  defect_id: string;
  description: string;
  department: string;
  severity: number;
  overdue_days: number;
  traffic_impact: number;
  safety_critical: boolean;
  corridor_id: string;
  status: string;
  score: number | null;
}

interface DefectListProps {
  defects: Defect[];
  onSelectDefect?: (defect: Defect) => void;
  onScoreDefect?: (id: string) => void;
  onScoreAll?: () => void;
  filters?: {
    department?: string;
    status?: string;
    corridor?: string;
    search?: string;
  };
  setFilters?: (filters: any) => void;
  loading?: boolean;
}

const DEPARTMENTS = ['all', 'Track', 'Power', 'Signals'];
const STATUSES = ['all', 'NEW', 'SCORED', 'SCHEDULED', 'APPROVED', 'COMPLETED'];

export default function DefectList({
  defects = [],
  onSelectDefect,
  onScoreDefect,
  onScoreAll,
  filters = {},
  setFilters,
  loading = false,
}: DefectListProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelect = (defect: Defect) => {
    setSelectedId(defect.id);
    if (onSelectDefect) onSelectDefect(defect);
  };

  const handleFilterChange = (key: string, value: string) => {
    if (setFilters) {
      setFilters({ ...filters, [key]: value === 'all' ? undefined : value });
    }
  };

  const getDepartmentColor = (dept: string) => {
    const colors: Record<string, string> = {
      Track: 'bg-blue-100 text-blue-700 border-blue-200',
      Power: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      Signals: 'bg-green-100 text-green-700 border-green-200',
    };
    return colors[dept] || 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      NEW: 'bg-gray-100 text-gray-600',
      SCORED: 'bg-blue-100 text-blue-600',
      SCHEDULED: 'bg-purple-100 text-purple-600',
      APPROVED: 'bg-green-100 text-green-600',
      COMPLETED: 'bg-gray-300 text-gray-600',
      DEFERRED: 'bg-orange-100 text-orange-600',
      ESCALATED: 'bg-red-100 text-red-600',
    };
    return colors[status] || 'bg-gray-100 text-gray-600';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-gray-500">Loading defects...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center bg-white p-4 rounded-lg shadow">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Department:</span>
          <div className="flex gap-1 flex-wrap">
            {DEPARTMENTS.map((dept) => (
              <button
                key={dept}
                onClick={() => handleFilterChange('department', dept)}
                className={`px-2 py-1 text-xs rounded-md transition-colors capitalize ${
                  (filters.department === dept || (dept === 'all' && !filters.department))
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {dept}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Status:</span>
          <div className="flex gap-1 flex-wrap">
            {STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => handleFilterChange('status', status)}
                className={`px-2 py-1 text-xs rounded-md transition-colors capitalize ${
                  (filters.status === status || (status === 'all' && !filters.status))
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        {onScoreAll && (
          <button
            onClick={onScoreAll}
            className="ml-auto px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Score All
          </button>
        )}
      </div>

      {defects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <div className="text-gray-400 text-lg">No defects found</div>
          <div className="text-gray-400 text-sm">Try adjusting your filters</div>
        </div>
      ) : (
        <div className="space-y-3">
          {defects.map((defect) => (
            <div
              key={defect.id}
              className={`bg-white p-4 rounded-lg shadow border-l-4 cursor-pointer transition-all hover:shadow-md ${
                defect.safety_critical ? 'border-red-500' : 'border-blue-500'
              } ${selectedId === defect.id ? 'ring-2 ring-blue-400' : ''}`}
              onClick={() => handleSelect(defect)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getDepartmentColor(defect.department)}`}>
                      {defect.department}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(defect.status)}`}>
                      {defect.status}
                    </span>
                    {defect.safety_critical && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-500 text-white animate-pulse">
                        ⚠️ SAFETY
                      </span>
                    )}
                    {defect.score !== null && defect.score !== undefined && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                        Score: {defect.score.toFixed(1)}
                      </span>
                    )}
                  </div>
                  <h3 className="font-semibold text-gray-800">{defect.description}</h3>
                  <div className="flex gap-4 mt-1 text-sm text-gray-500 flex-wrap">
                    <span>ID: {defect.defect_id}</span>
                    <span>Corridor: {defect.corridor_id}</span>
                    <span>Severity: {defect.severity}/5</span>
                    <span>Overdue: {defect.overdue_days} days</span>
                    <span>Traffic: {defect.traffic_impact}/5</span>
                  </div>
                </div>
                {onScoreDefect && defect.score === null && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onScoreDefect(defect.id);
                    }}
                    className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                  >
                    Score
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
