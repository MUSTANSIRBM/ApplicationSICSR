// frontend/src/components/shared/StatusBar.tsx
import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { SystemStatus } from '@/types';

export function StatusBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    api.getStatus().then(setStatus);
    const interval = setInterval(() => api.getStatus().then(setStatus), 10000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-4 py-1.5 text-xs text-gray-600 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <span className="font-medium">Tasks:</span>
          {status.totalTasks}
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium text-red-500">Critical:</span>
          {status.criticalWaiting}
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium">Conflicts Resolved:</span>
          {status.conflictsResolved}
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium">Week Savings:</span>
          <span className="text-green-600">{status.weekSavings}h</span>
        </span>
      </div>
      <div className="flex items-center gap-1">
        <span>Last solve:</span>
        <span className="font-medium">{status.lastSolveTime}s ago</span>
      </div>
    </div>
  );
}