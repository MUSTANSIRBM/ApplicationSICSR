// src/components/shared/StatusBar.tsx
import { useEffect } from 'react';
import { useStore } from '@/store/useStore';

export function StatusBar() {
  const { systemStatus, loadStatus } = useStore();

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  if (!systemStatus) {
    return (
      <div className="bg-gray-50 border-t border-gray-200 px-4 py-1.5 text-xs text-gray-400">
        Loading status...
      </div>
    );
  }

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-4 py-1.5 text-xs text-gray-600 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <span className="font-medium">Tasks:</span>
          <span className="text-gray-700">{systemStatus.totalTasks}</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium text-red-500">Critical:</span>
          <span className="text-red-600">{systemStatus.criticalWaiting}</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium">Conflicts Resolved:</span>
          <span className="text-gray-700">{systemStatus.conflictsResolved}</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="font-medium">Week Savings:</span>
          <span className="text-green-600 font-semibold">{systemStatus.weekSavings}h</span>
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-green-600">Live</span>
        </span>
        <span>Last solve: <span className="font-medium">{systemStatus.lastSolveTime}s ago</span></span>
      </div>
    </div>
  );
} 