// frontend/src/components/sensor/DecisionDisplay.tsx
import { IncidentResponse } from '@/types';
import { Badge } from '@/components/ui/Badge';

interface DecisionDisplayProps {
  result: IncidentResponse | null;
}

const ACTION_STYLES: Record<string, { bg: string; border: string; label: string }> = {
  emergency_stop:    { bg: 'bg-red-50',    border: 'border-red-300',    label: 'Emergency Stop' },
  reduce_speed:      { bg: 'bg-amber-50',  border: 'border-amber-300',  label: 'Reduce Speed' },
  reroute:           { bg: 'bg-blue-50',   border: 'border-blue-300',   label: 'Reroute' },
  proceed_with_caution: { bg: 'bg-green-50', border: 'border-green-300', label: 'Proceed with Caution' },
};

const SOURCE_BADGE: Record<string, 'error' | 'warning' | 'info' | 'success'> = {
  hard_rule: 'error',
  model: 'success',
  rule_fallback: 'warning',
};

export function DecisionDisplay({ result }: DecisionDisplayProps) {
  if (!result) {
    return (
      <div className="card border border-gray-200 border-dashed flex items-center justify-center min-h-[300px]">
        <div className="text-center text-gray-400">
          <p className="text-sm font-medium">No decision yet</p>
          <p className="text-xs mt-1">Submit a sensor incident to see the engine response</p>
        </div>
      </div>
    );
  }

  const style = ACTION_STYLES[result.action] || ACTION_STYLES.proceed_with_caution;

  return (
    <div className="space-y-3">
      {/* Action Banner */}
      <div className={`card ${style.bg} ${style.border} border-2`}>
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-lg font-bold text-gray-900">{style.label}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={SOURCE_BADGE[result.source] || 'default'} size="sm">
                {result.source.replace('_', ' ')}
              </Badge>
              {result.confidence !== null && (
                <span className="text-xs text-gray-500 font-mono">
                  {(result.confidence * 100).toFixed(1)}% confidence
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-gray-400 block">Decision Latency</span>
            <span className={`text-sm font-mono font-bold ${result.within_100ms_budget ? 'text-green-600' : 'text-red-600'}`}>
              {result.decision_latency_ms}ms
            </span>
          </div>
        </div>

        {/* Confidence bar */}
        {result.confidence !== null && (
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${
                result.confidence >= 0.8 ? 'bg-green-500' :
                result.confidence >= 0.55 ? 'bg-amber-500' : 'bg-red-500'
              }`}
              style={{ width: `${result.confidence * 100}%` }}
            />
          </div>
        )}
      </div>

      {/* Physics Panel */}
      <div className="card border border-gray-200">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Physics</h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Braking distance</span>
            <span className="font-mono font-medium">{result.physics.braking_distance_required_km} km</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Effective distance</span>
            <span className="font-mono font-medium">{result.physics.effective_distance_km} km</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Time to obstacle</span>
            <span className="font-mono font-medium">{result.physics.time_to_obstacle_min} min</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Safe stopping</span>
            <span className={`font-mono font-medium ${result.physics.safe_stopping_possible ? 'text-green-600' : 'text-red-600'}`}>
              {result.physics.safe_stopping_possible ? 'YES' : 'NO'}
            </span>
          </div>
          {result.physics.weather_braking_multiplier !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-500">Weather multiplier</span>
              <span className="font-mono font-medium">{result.physics.weather_braking_multiplier}x</span>
            </div>
          )}
        </div>

        {/* Speed Advisory */}
        {result.physics.speed_advisory && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            <span className="text-[10px] font-semibold text-amber-600 uppercase">Speed Advisory</span>
            <p className="text-xs text-gray-600 mt-0.5">
              {result.physics.speed_advisory.recommended_speed_kmh !== null
                ? `Reduce to ${result.physics.speed_advisory.recommended_speed_kmh} km/h`
                : result.physics.speed_advisory.basis}
            </p>
          </div>
        )}
      </div>

      {/* Reasons */}
      <div className="card border border-gray-200">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Reasons</h4>
        <ol className="space-y-1.5">
          {result.reasons.map((reason, i) => (
            <li key={i} className="text-xs text-gray-600 flex gap-2">
              <span className="text-gray-300 font-mono mt-0.5 shrink-0">{i + 1}.</span>
              <span>{reason}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Probabilities */}
      {result.probabilities && (
        <div className="card border border-gray-200">
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Action Probabilities</h4>
          <div className="space-y-1.5">
            {Object.entries(result.probabilities)
              .sort((a, b) => b[1] - a[1])
              .map(([action, prob]) => (
                <div key={action} className="flex items-center gap-2 text-xs">
                  <span className="text-gray-500 w-36 truncate text-right">
                    {action.replace(/_/g, ' ')}
                  </span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${action === result.action ? 'bg-blue-500' : 'bg-gray-300'}`}
                      style={{ width: `${prob * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-gray-400 w-12 text-right">
                    {(prob * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Repair Defect */}
      {result.repair_defect_id && (
        <div className="card border border-green-200 bg-green-50/50">
          <h4 className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-1">Repair Defect Created</h4>
          <p className="text-xs text-gray-600">
            Defect ID: <span className="font-mono font-medium">{result.repair_defect_id}</span>
          </p>
          <p className="text-[10px] text-gray-400 mt-1">
            Safety-critical defect bridged to the block planner
          </p>
        </div>
      )}
    </div>
  );
}
