// src/pages/live.tsx
import { useState } from 'react';
import { DefectInjector } from '@/components/live/DefectInjector';
import { BeforeAfterView } from '@/components/live/BeforeAfterView';
import { useStore } from '@/store/useStore';
import { ScheduleBlock, InjectionDefect, SolveResult } from '@/types';
import { mockBlocks } from '@/api/mockData';
import toast from 'react-hot-toast';

export default function LivePage() {
  const { injectDefect, loadSchedule, selectedWeek } = useStore();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [afterBlocks, setAfterBlocks] = useState<ScheduleBlock[]>(mockBlocks);
  const [injectedDefect, setInjectedDefect] = useState<InjectionDefect | null>(null);
  const [showBefore, setShowBefore] = useState(true);

  const handleInject = async (defect: InjectionDefect) => {
    setLoading(true);
    setInjectedDefect(defect);
    setShowBefore(true);
    
    try {
      // Store current blocks as "before"
      const beforeBlocks = [...afterBlocks];
      
      // Inject the defect
      const solveResult = await injectDefect(defect);
      setResult(solveResult);
      
      // Simulate after blocks (in reality, would come from backend)
      const newBlocks = [...mockBlocks];
      const newBlock: ScheduleBlock = {
        id: `B-${String(mockBlocks.length + 1).padStart(3, '0')}`,
        corridor: defect.corridor,
        department: defect.department,
        startTime: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        endTime: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(),
        defects: [{
          id: `EMERG-${Date.now()}`,
          department: defect.department,
          corridor: defect.corridor,
          description: defect.description,
          severity: 95,
          overdueDays: 0,
          trafficImpact: 80,
          score: 85,
          tier: 'safety-critical',
          status: 'new',
          createdAt: new Date().toISOString(),
        }],
        status: 'proposed',
        isCombined: false,
        duration: 3,
        savings: 0,
      };
      newBlocks.push(newBlock);
      setAfterBlocks(newBlocks);
      
      toast.success('🚨 Emergency defect injected! Re-solving...');
    } catch (error) {
      toast.error('❌ Failed to inject defect');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = () => {
    toast.success('✅ New schedule accepted');
    // Reload schedule
    loadSchedule(selectedWeek);
    setResult(null);
  };

  const handleReject = () => {
    setResult(null);
    setAfterBlocks(mockBlocks);
    toast('↩️ Schedule reverted to previous plan');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Injection</h1>
          <p className="text-sm text-gray-500">Emergency defect re-solving demo</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Status:</span>
          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium animate-pulse">
            ● Live
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <DefectInjector onInject={handleInject} loading={loading} />
          
          {injectedDefect && (
            <div className="mt-4 card bg-yellow-50 border-yellow-200">
              <div className="text-sm font-medium text-yellow-800">Last Injection</div>
              <div className="text-xs text-yellow-700 mt-1">
                {injectedDefect.department} · Corridor {injectedDefect.corridor}
              </div>
              <div className="text-xs text-yellow-600">{injectedDefect.description}</div>
            </div>
          )}

          {result && (
            <div className="mt-4 card bg-green-50 border-green-200">
              <div className="text-sm font-medium text-green-800">Solve Result</div>
              <div className="text-xs text-green-700 mt-1">
                ⏱️ {result.timeMs}ms · {result.status}
              </div>
              <div className="text-xs text-green-600">
                {result.blocksMoved.length} moved · {result.blocksAdded.length} added
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-3">
          <BeforeAfterView
            beforeBlocks={mockBlocks}
            afterBlocks={afterBlocks}
            result={result}
            onAccept={handleAccept}
            onReject={handleReject}
          />
        </div>
      </div>
    </div>
  );
}