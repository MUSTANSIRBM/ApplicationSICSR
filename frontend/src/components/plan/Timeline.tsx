// src/components/plan/Timeline.tsx
import { useState } from 'react';
import { ScheduleBlock, TimelineData } from '@/types';
import { Edit2, Trash2, Check, Lock, Clock } from 'lucide-react';

type TimelineBlock = ScheduleBlock & {
  description: string;
  priority: number;
  assignedTo: string;
  weekStart: string | Date;
};

interface TimelineProps {
  data: TimelineData;
  onApprove: (id: string) => void;
  onLock: (id: string) => void;
  onDelete: (id: string) => void;
  onEdit: (id: string, data: Partial<ScheduleBlock>) => void;
}

export function Timeline({ data, onApprove, onLock, onDelete, onEdit }: TimelineProps) {
  const [editingBlock, setEditingBlock] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<TimelineBlock>>({});

  const handleEditStart = (block: TimelineBlock) => {
    setEditingBlock(block.id);
    setEditData({
      description: block.description,
      duration: block.duration,
      priority: block.priority,
      assignedTo: block.assignedTo,
    });
  };

  const handleEditSave = (id: string) => {
    onEdit(id, editData as Partial<ScheduleBlock>);
    setEditingBlock(null);
    setEditData({});
  };

  const handleEditCancel = () => {
    setEditingBlock(null);
    setEditData({});
  };

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  // Group blocks by day
  const blocksByDay: Record<string, TimelineBlock[]> = {};
  days.forEach(day => { blocksByDay[day] = []; });
  
  data.blocks.forEach(block => {
    const timelineBlock = block as TimelineBlock;
    const day = new Date(timelineBlock.weekStart).getDay();
    const dayName = days[day === 0 ? 6 : day - 1];
    if (blocksByDay[dayName]) {
      blocksByDay[dayName].push(timelineBlock);
    }
  });

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'approved': return 'border-l-4 border-blue-500 bg-blue-50/50';
      case 'locked': return 'border-l-4 border-green-500 bg-green-50/50';
      case 'pending': return 'border-l-4 border-yellow-500 bg-yellow-50/50';
      default: return 'border-l-4 border-gray-300 bg-gray-50/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'approved': return <Check className="w-4 h-4 text-blue-600" />;
      case 'locked': return <Lock className="w-4 h-4 text-green-600" />;
      default: return <Clock className="w-4 h-4 text-yellow-600" />;
    }
  };

  const getPriorityLabel = (priority: number) => {
    const labels = { 1: 'Critical', 2: 'High', 3: 'Medium', 4: 'Low' };
    return labels[priority as keyof typeof labels] || 'Medium';
  };

  const getPriorityColor = (priority: number) => {
    const colors = { 1: 'text-red-600', 2: 'text-orange-600', 3: 'text-yellow-600', 4: 'text-blue-600' };
    return colors[priority as keyof typeof colors] || 'text-gray-600';
  };

  return (
    <div className="card p-6 overflow-x-auto">
      <div className="grid grid-cols-7 gap-3 min-w-[700px]">
        {days.map((day, index) => (
          <div key={day} className="space-y-2">
            <div className={`text-sm font-semibold text-center py-2 rounded-lg ${
              index === 0 || index === 6 
                ? 'text-gray-400 bg-gray-50' 
                : 'text-gray-700 bg-gray-100/50'
            }`}>
              {day}
            </div>
            <div className="space-y-2 min-h-[200px]">
              {blocksByDay[day]?.map((block) => (
                <div 
                  key={block.id} 
                  className={`rounded-lg p-3 shadow-sm transition-all duration-200 hover:shadow-md ${getStatusColor(block.status)}`}
                >
                  {editingBlock === block.id ? (
                    <div className="space-y-2 animate-fade-in">
                      <input
                        type="text"
                        value={editData.description || ''}
                        onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                        className="input input-sm"
                        placeholder="Description"
                        autoFocus
                      />
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={editData.duration || 4}
                          onChange={(e) => setEditData({ ...editData, duration: parseInt(e.target.value) })}
                          className="input input-sm w-16"
                          min="1"
                          max="8"
                        />
                        <select
                          value={editData.priority || 3}
                          onChange={(e) => setEditData({ ...editData, priority: parseInt(e.target.value) })}
                          className="select select-sm flex-1"
                        >
                          <option value={1}>Critical</option>
                          <option value={2}>High</option>
                          <option value={3}>Medium</option>
                          <option value={4}>Low</option>
                        </select>
                      </div>
                      <div className="flex gap-1 mt-1">
                        <button
                          onClick={() => handleEditSave(block.id)}
                          className="btn btn-success btn-sm flex-1"
                        >
                          <Check className="w-3 h-3" />
                          Save
                        </button>
                        <button
                          onClick={handleEditCancel}
                          className="btn btn-secondary btn-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-gray-500">{block.id}</span>
                        <div className="flex items-center gap-1">
                          {getStatusIcon(block.status)}
                          <span className="text-xs font-medium capitalize">{block.status}</span>
                        </div>
                      </div>
                      <div className="text-sm font-medium text-gray-800 line-clamp-2">
                        {block.description}
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {block.duration}h
                        </span>
                        <span className={`font-medium ${getPriorityColor(block.priority)}`}>
                          P{block.priority} · {getPriorityLabel(block.priority)}
                        </span>
                        <span className="text-gray-400">{block.assignedTo}</span>
                      </div>
                      <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-gray-200/50">
                        {block.status === 'proposed' && (
                          <>
                            <button
                              onClick={() => onApprove(block.id)}
                              className="btn btn-success btn-sm"
                            >
                              <Check className="w-3 h-3" />
                              Approve
                            </button>
                            <button
                              onClick={() => onLock(block.id)}
                              className="btn btn-primary btn-sm"
                            >
                              <Lock className="w-3 h-3" />
                              Lock
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleEditStart(block)}
                          className="btn btn-secondary btn-sm"
                        >
                          <Edit2 className="w-3 h-3" />
                          Edit
                        </button>
                        <button
                          onClick={() => onDelete(block.id)}
                          className="btn btn-danger btn-sm"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {(!blocksByDay[day] || blocksByDay[day].length === 0) && (
                <div className="h-24 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg">
                  <span className="text-xs text-gray-400">No blocks</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}