// src/components/shared/StatusBar.tsx
import { useEffect, useState } from 'react';
import { useStore } from '@/store/useStore';
import { Activity, AlertTriangle, CheckCircle, Clock, Zap } from 'lucide-react';

export function StatusBar() {
  const { systemStatus, loadStatus } = useStore();
  const [isVisible, setIsVisible] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    loadStatus();
    const interval = setInterval(async () => {
      await loadStatus();
      setLastUpdate(new Date());
    }, 10000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  if (!systemStatus) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-gray-50/80 backdrop-blur-md border-t border-gray-200 px-4 py-2 text-xs text-gray-400 flex items-center justify-between">
        <span>Loading status...</span>
        <div className="spinner-sm" />
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-gray-200/80 px-4 py-2 text-xs text-gray-600 flex items-center justify-between shadow-[0_-1px_10px_rgba(0,0,0,0.05)]">
      <div className="flex items-center gap-4 overflow-x-auto">
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <Activity className="w-3.5 h-3.5 text-blue-500" />
          <span className="font-medium">Tasks:</span>
          <span className="text-gray-800 font-semibold">{systemStatus.totalTasks}</span>
        </div>
        
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          <span className="font-medium text-red-600">Critical:</span>
          <span className="text-red-700 font-semibold">{systemStatus.criticalWaiting}</span>
        </div>
        
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <CheckCircle className="w-3.5 h-3.5 text-green-500" />
          <span className="font-medium">Resolved:</span>
          <span className="text-gray-800 font-semibold">{systemStatus.conflictsResolved}</span>
        </div>
        
        <div className="flex items-center gap-1.5 whitespace-nowrap">
          <Zap className="w-3.5 h-3.5 text-yellow-500" />
          <span className="font-medium">Savings:</span>
          <span className="text-green-600 font-bold">{systemStatus.weekSavings}h</span>
        </div>
      </div>
      
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
          </span>
          <span className="text-green-600 font-medium">Live</span>
        </div>
        
        <div className="hidden sm:flex items-center gap-1.5 text-gray-400">
          <Clock className="w-3 h-3" />
          <span>Solve: {systemStatus.lastSolveTime}s ago</span>
        </div>
        
        <div className="hidden md:flex items-center gap-1.5 text-gray-400">
          <span>Updated: {lastUpdate.toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}