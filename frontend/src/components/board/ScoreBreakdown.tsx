import { Defect } from '@/types';
import { calculateDefectScore } from '@/api/mockData';

interface ScoreBreakdownProps {
  defect: Defect;
}

export function ScoreBreakdown({ defect }: ScoreBreakdownProps) {
  // MAX values for each metric
  const MAX_SEVERITY = 100;
  const MAX_OVERDUE_DAYS = 30;
  const MAX_TRAFFIC_IMPACT = 100;
  
  // Weights
  const severityWeight = 0.5;
  const overdueWeight = 0.3;
  const trafficWeight = 0.2;

  // Calculate individual contributions
  const severityValue = (defect.severity / MAX_SEVERITY) * 100;
  const overdueValue = (Math.min(defect.overdueDays, MAX_OVERDUE_DAYS) / MAX_OVERDUE_DAYS) * 100;
  const trafficValue = (defect.trafficImpact / MAX_TRAFFIC_IMPACT) * 100;
  
  // Calculate weighted contributions
  const severityContrib = severityValue * severityWeight;
  const overdueContrib = overdueValue * overdueWeight;
  const trafficContrib = trafficValue * trafficWeight;
  const total = severityContrib + overdueContrib + trafficContrib;

  // Calculate score using the same function for consistency
  const calculatedScore = calculateDefectScore(defect);

  const getColorForValue = (value: number) => {
    if (value >= 80) return '#EF4444';
    if (value >= 60) return '#F97316';
    if (value >= 40) return '#EAB308';
    if (value >= 20) return '#3B82F6';
    return '#22C55E';
  };

  return (
    <div className="bg-white/50 rounded-md p-3 space-y-2">
      <div className="text-xs font-medium text-gray-700">Score Breakdown (out of 100)</div>
      
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-24 text-gray-500">Severity (50%)</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${Math.min(severityValue, 100)}%`,
                background: getColorForValue(defect.severity)
              }} 
            />
          </div>
          <span className="w-16 text-right font-mono text-gray-600">
            {defect.severity}/{MAX_SEVERITY}
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-xs">
          <span className="w-24 text-gray-500">Overdue (30%)</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${Math.min(overdueValue, 100)}%`,
                background: getColorForValue(overdueValue)
              }} 
            />
          </div>
          <span className="w-16 text-right font-mono text-gray-600">
            {Math.min(defect.overdueDays, MAX_OVERDUE_DAYS)}/{MAX_OVERDUE_DAYS}d
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-xs">
          <span className="w-24 text-gray-500">Traffic (20%)</span>
          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${Math.min(trafficValue, 100)}%`,
                background: getColorForValue(defect.trafficImpact)
              }} 
            />
          </div>
          <span className="w-16 text-right font-mono text-gray-600">
            {defect.trafficImpact}/{MAX_TRAFFIC_IMPACT}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-gray-200/50">
        <span className="text-xs font-medium text-gray-700">Total Score (out of 100)</span>
        <span 
          className="text-sm font-bold"
          style={{ color: getColorForValue(calculatedScore) }}
        >
          {calculatedScore.toFixed(1)}
        </span>
      </div>
    </div>
  );
}