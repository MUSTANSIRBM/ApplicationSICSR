// frontend/src/components/impact/SavingsChart.tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ImpactData } from '@/types';

interface SavingsChartProps {
  data: ImpactData;
}

export function SavingsChart({ data }: SavingsChartProps) {
  const chartData = data.weeklyTrend.map(item => ({
    day: item.day,
    'Planned Hours': item.planned,
    'Actual Hours': item.actual,
  }));

  const totalPlanned = data.totalClosureHoursPlanned;
  const totalActual = data.totalClosureHoursActual;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-gray-700">Weekly Closure Hours</h4>
          <p className="text-xs text-gray-400">Planned vs Actual</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-gray-400" />
            <span>Planned: {totalPlanned}h</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500" />
            <span>Actual: {totalActual}h</span>
          </div>
        </div>
      </div>
      
      <div className="h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="day" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip 
              contentStyle={{ fontSize: 12, borderRadius: 8, border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}
            />
            <Legend />
            <Bar dataKey="Planned Hours" fill="#94A3B8" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Actual Hours" fill="#22C55E" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}