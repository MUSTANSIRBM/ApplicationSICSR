// frontend/src/components/board/ScoreBreakdown.tsx
import { Defect } from '@/types';

interface ScoreBreakdownProps {
  defect: Defect;
}

export function ScoreBreakdown({ defect }: ScoreBreakdownProps) {
  const severityWeight = 0.5;
  const overdueWeight = 0.3;
  const trafficWeight = 0.2;

  const severityContrib = defect.severity * severityWeight;
  const overdueContrib = Math.min(defect.overdueDays * 5, 50) * overdueWeight;
  const trafficContrib = defect.trafficImpact * trafficWeight;
  const total = severityContrib + overdueContrib + trafficContrib;

  return (
    <div className="bg-white/50 rounded-md p-3 space-y-2">
      <div className="text-xs font-medium text-gray-700">Score Breakdown</div>
      
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-20 text-gray-500">Severity</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(severityContrib / 50) * 100}%` }} />
          </div>
          <span className="w-12 text-right font-mono text-gray-600">{severityContrib.toFixed(1)}</span>
        </div>
        
        <div className="flex items-center gap-2 text-xs">
          <span className="w-20 text-gray-500">Overdue</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-orange-500 rounded-full" style={{ width: `${(overdueContrib / 15) * 100}%` }} />
          </div>
          <span className="w-12 text-right font-mono text-gray-600">{overdueContrib.toFixed(1)}</span>
        </div>
        
        <div className="flex items-center gap-2 text-xs">
          <span className="w-20 text-gray-500">Traffic Impact</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${(trafficContrib / 20) * 100}%` }} />
          </div>
          <span className="w-12 text-right font-mono text-gray-600">{trafficContrib.toFixed(1)}</span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-gray-200/50">
        <span className="text-xs font-medium text-gray-700">Total Score</span>
        <span className="text-sm font-bold text-gray-900">{total.toFixed(1)}</span>
      </div>
    </div>
  );
}