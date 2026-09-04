// src/pages/sensor.tsx
import { useState } from 'react';
import { withAuth } from '@/hoc/withAuth';
import { SensorIncidentForm, DecisionDisplay } from '@/components/sensor';
import { IncidentRequest, IncidentResponse } from '@/types';
import { api } from '@/api/client';
import toast from 'react-hot-toast';

function SensorPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IncidentResponse | null>(null);
  const [history, setHistory] = useState<{ request: IncidentRequest; response: IncidentResponse }[]>([]);

  const handleSubmit = async (data: IncidentRequest) => {
    setLoading(true);
    try {
      const response = await api.sendIncident(data);
      setResult(response);
      setHistory(prev => [{ request: data, response }, ...prev].slice(0, 10));

      if (response.source === 'model') {
        toast.success(`ML decision: ${response.action} (${((response.confidence || 0) * 100).toFixed(1)}%)`);
      } else if (response.source === 'hard_rule') {
        toast.error(`Hard rule fired: ${response.action}`);
      } else {
        toast(`Rule fallback: ${response.action}`, { icon: '⚠️' });
      }
    } catch (error: any) {
      toast.error(error.message || 'Decision engine failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Sensor Decision Engine</h1>
        <p className="text-sm text-gray-500">
          Real-time ML inference with physics verification and safety overrides
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form */}
        <div className="lg:col-span-5">
          <SensorIncidentForm onSubmit={handleSubmit} loading={loading} />
        </div>

        {/* Results */}
        <div className="lg:col-span-7">
          <DecisionDisplay result={result} />
        </div>
      </div>

      {/* Decision History */}
      {history.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Recent Decisions</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Source</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Action</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Confidence</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Speed</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Severity</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Weather</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Latency</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-3">
                      <span className={`inline-block px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                        h.response.source === 'model' ? 'bg-green-100 text-green-700' :
                        h.response.source === 'hard_rule' ? 'bg-red-100 text-red-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        {h.response.source.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-2 px-3 font-medium text-gray-700">
                      {h.response.action.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2 px-3 font-mono text-gray-500">
                      {h.response.confidence !== null ? `${(h.response.confidence * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2 px-3 font-mono text-gray-500">{h.request.train_speed_kmh}</td>
                    <td className="py-2 px-3 font-mono text-gray-500">{h.request.severity_score}/10</td>
                    <td className="py-2 px-3 text-gray-500">{h.request.environmental_condition}</td>
                    <td className="py-2 px-3 font-mono text-gray-500">{h.response.decision_latency_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default withAuth(SensorPage);
