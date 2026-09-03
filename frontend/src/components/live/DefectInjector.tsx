// frontend/src/components/live/DefectInjector.tsx
import { useState } from 'react';
import { InjectionDefect } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface DefectInjectorProps {
  onInject: (defect: InjectionDefect) => void;
  loading: boolean;
}

const emergencyDescriptions = {
  track: ['Broken rail detected', 'Track buckling', 'Washout on embankment'],
  power: ['Live wire down', 'Transformer explosion', 'Power pole collapse'],
  signals: ['Signal control failure', 'Interlocking malfunction', 'Track circuit short'],
};

export function DefectInjector({ onInject, loading }: DefectInjectorProps) {
  const [defect, setDefect] = useState<InjectionDefect>({
    department: 'track',
    corridor: 'A',
    description: 'Broken rail detected',
    severity: 95,
    isEmergency: true,
  });

  const corridors = ['A', 'B', 'C', 'D', 'E'];

  return (
    <div className="card border-2 border-dashed border-red-300 bg-red-50/50">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🚨</span>
        <h3 className="text-sm font-semibold text-red-700">Emergency Defect Injection</h3>
        <Badge variant="safety-critical">DEMO</Badge>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Department</label>
          <select
            value={defect.department}
            onChange={(e) => setDefect({ ...defect, department: e.target.value as any })}
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="track">Track</option>
            <option value="power">Power</option>
            <option value="signals">Signals</option>
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Corridor</label>
          <select
            value={defect.corridor}
            onChange={(e) => setDefect({ ...defect, corridor: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {corridors.map(c => (
              <option key={c} value={c}>Corridor {c}</option>
            ))}
          </select>
        </div>

        <div className="col-span-2">
          <label className="text-xs font-medium text-gray-600 block mb-1">Description</label>
          <select
            value={defect.description}
            onChange={(e) => setDefect({ ...defect, description: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {emergencyDescriptions[defect.department].map(desc => (
              <option key={desc} value={desc}>{desc}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Button
          onClick={() => onInject(defect)}
          loading={loading}
          variant="danger"
          className="flex-1"
        >
          ⚡ Inject Emergency Defect
        </Button>
        <span className="text-xs text-gray-400">Will re-solve in {'<'}1s</span>
      </div>
    </div>
  );
}