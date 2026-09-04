// src/components/shared/StatusBar.tsx
import { useEffect, useState } from 'react';

export function StatusBar() {
  const [status, setStatus] = useState({
    isLive: true,
    totalTasks: 0,
    criticalWaiting: 0,
  });

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/status');
        if (response.ok) {
          const data = await response.json();
          setStatus({
            isLive: data.is_live ?? true,
            totalTasks: data.total_tasks ?? 0,
            criticalWaiting: data.critical_waiting ?? 0,
          });
        }
      } catch (error) {
        console.warn('Status fetch failed:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-800 text-white px-4 py-2 text-sm flex items-center justify-between border-t border-gray-700">
      <div className="flex items-center space-x-6">
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${status.isLive ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
          {status.isLive ? 'System Online' : 'System Offline'}
        </span>
        <span className="text-gray-400">
          Tasks: {status.totalTasks}
        </span>
        {status.criticalWaiting > 0 && (
          <span className="text-red-400">
            ⚠️ Critical: {status.criticalWaiting}
          </span>
        )}
      </div>
      <div className="text-gray-400">
        v1.0.0
      </div>
    </div>
  );
}
