// src/components/board/DefectCard.tsx
import { useState } from 'react';
import { Defect } from '@/types';
import { Badge } from '@/components/ui/Badge';
import { Calendar, Clock, Edit, Trash2, AlertTriangle } from 'lucide-react';
import { formatDate, getRelativeTime, getSmartDate, DateFormats } from '@/utils/dateUtils';

interface DefectCardProps {
  defect: Defect;
  onSchedule: (id: string) => void;
  onScheduleWithWeek?: (id: string) => void;
  onDefer: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit?: (id: string, data?: Partial<Defect>) => void;
  isScheduling?: boolean;
  compact?: boolean;
}

export function DefectCard({ 
  defect, 
  onSchedule, 
  onScheduleWithWeek,
  onDefer, 
  onDelete,
  onEdit,
  isScheduling,
  compact = false
}: DefectCardProps) {
  if (!defect) return null;

  const getTierDisplay = (tier: string) => {
    const map: Record<string, string> = {
      'safety-critical': 'Safety Critical',
      'high': 'High',
      'normal': 'Normal',
      'deferred': 'Deferred'
    };
    return map[tier] || tier;
  };

  const getStatusBadge = () => {
    switch(defect.status) {
      case 'scheduled':
        return <Badge variant="approved" size="sm">✓ Scheduled</Badge>;
      case 'deferred':
        return <Badge variant="deferred" size="sm">⏳ Deferred</Badge>;
      case 'completed':
        return <Badge variant="approved" size="sm">✓ Completed</Badge>;
      default:
        return <Badge variant="default" size="sm">📌 New</Badge>;
    }
  };

  const getImpactColor = (score: number) => {
    if (score >= 80) return 'text-red-600 bg-red-50';
    if (score >= 60) return 'text-orange-600 bg-orange-50';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50';
    return 'text-blue-600 bg-blue-50';
  };

  const getOverdueStatus = (days: number) => {
    if (days <= 0) return null;
    if (days <= 7) return 'text-orange-600 bg-orange-50';
    if (days <= 14) return 'text-red-500 bg-red-50';
    return 'text-red-700 bg-red-100';
  };

  const handleEditClick = () => {
    if (onEdit) {
      onEdit(defect.id);
    }
  };

  const overdueDays = defect.overdueDays || 0;
  const isOverdue = overdueDays > 0;

  if (compact) {
    return (
      <div className="bg-white rounded-xl border border-gray-200/80 p-3 hover:shadow-md transition-all duration-200 flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-mono font-medium text-gray-500">{defect.id}</span>
            <Badge variant={defect.tier as any} size="sm">{getTierDisplay(defect.tier)}</Badge>
            {getStatusBadge()}
            {isOverdue && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getOverdueStatus(overdueDays)}`}>
                ⚠️ {overdueDays}d overdue
              </span>
            )}
          </div>
          <p className="text-sm text-gray-800 truncate">{defect.description}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>{defect.department} · Corridor {defect.corridor}</span>
            <span>Impact: <span className="font-medium">{defect.impactScore || 0}</span></span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {defect.status === 'new' && (
            <button
              onClick={() => onSchedule(defect.id)}
              disabled={isScheduling}
              className="px-2.5 py-1.5 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              <Calendar className="w-3 h-3" />
              Schedule
            </button>
          )}
          <button
            onClick={handleEditClick}
            className="p-1.5 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
          >
            <Edit className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(defect.id)}
            className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200/80 p-4 hover:shadow-lg transition-all duration-200 group h-full flex flex-col">
      {/* Header - Fixed height area */}
      <div className="flex items-start justify-between gap-2 min-h-[44px]">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-mono font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded">
              {defect.id}
            </span>
            <Badge variant={defect.tier as any}>{getTierDisplay(defect.tier)}</Badge>
            {getStatusBadge()}
          </div>
        </div>
        
        {defect.tier === 'safety-critical' && (
          <div className="flex-shrink-0">
            <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
          </div>
        )}
      </div>

      {/* Description - Fixed height with ellipsis */}
      <div className="mt-1.5 flex-1">
        <p className="text-sm font-medium text-gray-800 line-clamp-2 min-h-[40px]">
          {defect.description}
        </p>
      </div>

      {/* Meta info - Fixed height */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs text-gray-500 min-h-[24px]">
        <span className="flex items-center gap-1">
          <span className="font-medium">{defect.department}</span>
          <span className="text-gray-300">·</span>
          <span>Corridor {defect.corridor}</span>
        </span>
        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full font-medium ${getImpactColor(defect.impactScore || 0)}`}>
          Impact: {defect.impactScore || 0}
        </span>
      </div>

      {/* Date and overdue - Fixed height */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs min-h-[20px]">
        <span className="text-gray-400 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {getSmartDate(defect.createdAt)}
        </span>
        {isOverdue && (
          <span className={`font-medium px-2 py-0.5 rounded-full ${getOverdueStatus(overdueDays)}`}>
            ⚠️ {overdueDays} day{overdueDays > 1 ? 's' : ''} overdue
          </span>
        )}
        {defect.scheduledWeek && (
          <span className="text-blue-600 flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {formatDate(defect.scheduledWeek, DateFormats.SHORT)}
          </span>
        )}
      </div>

      {/* Actions - Fixed height */}
      <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-gray-100 min-h-[36px]">
        {defect.status === 'new' && (
          <>
            <button
              onClick={() => onSchedule(defect.id)}
              disabled={isScheduling}
              className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              <Calendar className="w-3.5 h-3.5" />
              {isScheduling ? 'Scheduling...' : 'Schedule'}
            </button>
            {onScheduleWithWeek && (
              <button
                onClick={() => onScheduleWithWeek(defect.id)}
                className="px-3 py-1 text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors flex items-center gap-1"
              >
                <Calendar className="w-3.5 h-3.5" />
                Pick Week
              </button>
            )}
          </>
        )}
        {defect.status === 'scheduled' && (
          <button
            onClick={() => onDefer(defect.id)}
            className="px-3 py-1 text-xs bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg transition-colors flex items-center gap-1"
          >
            <Clock className="w-3.5 h-3.5" />
            Defer
          </button>
        )}
        <button
          onClick={handleEditClick}
          className="px-3 py-1 text-xs bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg transition-colors flex items-center gap-1"
        >
          <Edit className="w-3.5 h-3.5" />
          Edit
        </button>
        <button
          onClick={() => onDelete(defect.id)}
          className="px-3 py-1 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors flex items-center gap-1 ml-auto"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>
    </div>
  );
}