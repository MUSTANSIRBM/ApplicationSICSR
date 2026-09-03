// src/components/board/DefectCard.tsx
import { useState } from 'react';
import { Defect } from '@/types';
import { Badge } from '@/components/ui/Badge';
import { Calendar, Clock, Edit, Trash2, AlertTriangle, CheckCircle, XCircle, ArrowRight } from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';

interface DefectCardProps {
  defect: Defect;
  onSchedule: (id: string) => void;
  onScheduleWithWeek?: (id: string) => void; // Made optional
  onDefer: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit?: (id: string, data: Partial<Defect>) => void;
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

  if (compact) {
    return (
      <div className="bg-white rounded-xl border border-gray-200/80 p-3 hover:shadow-md transition-all duration-200 flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-mono font-medium text-gray-500">{defect.id}</span>
            <Badge variant={defect.tier as any} size="sm">{getTierDisplay(defect.tier)}</Badge>
            {getStatusBadge()}
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
            onClick={() => onEdit?.(defect.id, {})}
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
    <div className="bg-white rounded-xl border border-gray-200/80 p-4 hover:shadow-lg transition-all duration-200 group">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs font-mono font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded">
              {defect.id}
            </span>
            <Badge variant={defect.tier as any}>{getTierDisplay(defect.tier)}</Badge>
            {getStatusBadge()}
            <span className="text-xs text-gray-300">•</span>
            <span className="text-xs text-gray-500">{defect.department}</span>
            <span className="text-xs text-gray-400">Corridor {defect.corridor}</span>
          </div>
          
          <p className="text-sm font-medium text-gray-800 mb-2 line-clamp-2">
            {defect.description}
          </p>
          
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${getImpactColor(defect.impactScore || 0)}`}>
                Impact: {defect.impactScore || 0}
              </span>
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDistanceToNow(new Date(defect.createdAt), { addSuffix: true })}
            </span>
          </div>
        </div>
        
        {defect.tier === 'safety-critical' && (
          <div className="flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-500 animate-pulse" />
          </div>
        )}
      </div>
      
      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100">
        {defect.status === 'new' && (
          <>
            <button
              onClick={() => onSchedule(defect.id)}
              disabled={isScheduling}
              className="btn btn-primary btn-sm flex items-center gap-1.5"
            >
              <Calendar className="w-3.5 h-3.5" />
              {isScheduling ? 'Scheduling...' : 'Schedule'}
            </button>
            {onScheduleWithWeek && (
              <button
                onClick={() => onScheduleWithWeek(defect.id)}
                className="btn btn-secondary btn-sm flex items-center gap-1.5"
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
            className="btn btn-warning btn-sm flex items-center gap-1.5"
          >
            <Clock className="w-3.5 h-3.5" />
            Defer
          </button>
        )}
        <button
          onClick={() => onEdit?.(defect.id, {})}
          className="btn btn-ghost btn-sm flex items-center gap-1.5"
        >
          <Edit className="w-3.5 h-3.5" />
          Edit
        </button>
        <button
          onClick={() => onDelete(defect.id)}
          className="btn btn-danger btn-sm flex items-center gap-1.5 ml-auto"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>
    </div>
  );
}