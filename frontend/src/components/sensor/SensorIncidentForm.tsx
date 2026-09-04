// frontend/src/components/sensor/SensorIncidentForm.tsx
import { useState } from 'react';
import { IncidentRequest, EnvironmentalCondition, ObstructionType, SensorType } from '@/types';
import { Button } from '@/components/ui/Button';

interface SensorIncidentFormProps {
  onSubmit: (data: IncidentRequest) => void;
  loading: boolean;
}

const WEATHER_OPTIONS: EnvironmentalCondition[] = ['clear', 'rain', 'fog', 'heavy_rain', 'snow', 'flood'];
const OBSTRUCTION_OPTIONS: ObstructionType[] = [
  'landslide_debris', 'boulder', 'track_buckling', 'fallen_tree',
  'stranded_vehicle', 'water_logging', 'cattle_crossing', 'broken_rail',
  'signal_cable_theft', 'sensor_miscount', 'environmental_false_positive',
  'unknown_obstruction', 'equipment_failure_ahead',
];
const SENSOR_OPTIONS: SensorType[] = ['track_circuit', 'axle_counter', 'vibration', 'accelerometer'];
const CORRIDOR_OPTIONS = ['DEL-AGRA', 'MUM-PUNE', 'KOL-HOW', 'CHN-BGLR', 'HYB-SEC', 'ET-NGP'];

const formatLabel = (s: string) =>
  s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

export function SensorIncidentForm({ onSubmit, loading }: SensorIncidentFormProps) {
  const [form, setForm] = useState<IncidentRequest>({
    train_speed_kmh: 120,
    distance_to_obstacle_km: 8.5,
    environmental_condition: 'heavy_rain',
    weather_alert: true,
    signal_quality_percent: 45,
    severity_score: 9,
    obstruction_type: 'landslide_debris',
    alternative_route_available: false,
    communication_latency_ms: 1200,
    axle_balance: null,
    ahead_section_status: 'CLEAR',
    known_train_schedule: true,
    distance_from_station_km: 6.0,
    sensor_type: 'track_circuit',
    create_repair_defect: false,
    corridor: 'ET-NGP',
  });

  const set = (key: keyof IncidentRequest, value: any) =>
    setForm(prev => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="card border border-gray-200">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white shadow-sm">
          <span className="text-sm">📡</span>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Sensor Incident</h3>
          <p className="text-[10px] text-gray-400">14 raw telemetry fields</p>
        </div>
      </div>

      {/* Train */}
      <fieldset className="mb-3">
        <legend className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Train</legend>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-600 block mb-1">Speed (km/h)</label>
            <input type="number" min={45} max={200} step={0.1}
              value={form.train_speed_kmh}
              onChange={e => set('train_speed_kmh', parseFloat(e.target.value))}
              className="input input-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Distance (km)</label>
            <input type="number" min={0} max={20} step={0.1}
              value={form.distance_to_obstacle_km}
              onChange={e => set('distance_to_obstacle_km', parseFloat(e.target.value))}
              className="input input-sm" />
          </div>
        </div>
      </fieldset>

      {/* Environment */}
      <fieldset className="mb-3">
        <legend className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Environment</legend>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-600 block mb-1">Weather</label>
            <select value={form.environmental_condition}
              onChange={e => set('environmental_condition', e.target.value)}
              className="input input-sm">
              {WEATHER_OPTIONS.map(w => <option key={w} value={w}>{formatLabel(w)}</option>)}
            </select>
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.weather_alert}
                onChange={e => set('weather_alert', e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500" />
              <span className="text-xs text-gray-600">Weather Alert</span>
            </label>
          </div>
        </div>
      </fieldset>

      {/* Sensors */}
      <fieldset className="mb-3">
        <legend className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Sensors</legend>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-600 block mb-1">Sensor Type</label>
            <select value={form.sensor_type}
              onChange={e => set('sensor_type', e.target.value)}
              className="input input-sm">
              {SENSOR_OPTIONS.map(s => <option key={s} value={s}>{formatLabel(s)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Signal Quality (%)</label>
            <input type="number" min={0} max={100} step={1}
              value={form.signal_quality_percent}
              onChange={e => set('signal_quality_percent', parseFloat(e.target.value))}
              className="input input-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Axle Balance</label>
            <input type="number" min={0.3} max={1.7} step={0.01} placeholder="optional"
              value={form.axle_balance ?? ''}
              onChange={e => set('axle_balance', e.target.value ? parseFloat(e.target.value) : null)}
              className="input input-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Latency (ms)</label>
            <input type="number" min={10} max={5000} step={10}
              value={form.communication_latency_ms}
              onChange={e => set('communication_latency_ms', parseFloat(e.target.value))}
              className="input input-sm" />
          </div>
        </div>
      </fieldset>

      {/* Incident */}
      <fieldset className="mb-3">
        <legend className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Incident</legend>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-600 block mb-1">Severity (1-10)</label>
            <input type="number" min={1} max={10} step={1}
              value={form.severity_score}
              onChange={e => set('severity_score', parseInt(e.target.value))}
              className="input input-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Obstruction Type</label>
            <select value={form.obstruction_type}
              onChange={e => set('obstruction_type', e.target.value)}
              className="input input-sm">
              {OBSTRUCTION_OPTIONS.map(t => <option key={t} value={t}>{formatLabel(t)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Ahead Section</label>
            <select value={form.ahead_section_status}
              onChange={e => set('ahead_section_status', e.target.value)}
              className="input input-sm">
              <option value="CLEAR">Clear</option>
              <option value="OCCUPIED">Occupied</option>
            </select>
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.alternative_route_available}
                onChange={e => set('alternative_route_available', e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span className="text-xs text-gray-600">Alt Route Available</span>
            </label>
          </div>
        </div>
      </fieldset>

      {/* Context */}
      <fieldset className="mb-3">
        <legend className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Context</legend>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-600 block mb-1">Station Distance (km)</label>
            <input type="number" min={0} max={25} step={0.1}
              value={form.distance_from_station_km}
              onChange={e => set('distance_from_station_km', parseFloat(e.target.value))}
              className="input input-sm" />
          </div>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.known_train_schedule}
                onChange={e => set('known_train_schedule', e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span className="text-xs text-gray-600">Known Schedule</span>
            </label>
          </div>
        </div>
      </fieldset>

      {/* Bridge */}
      <fieldset className="mb-4 p-2 rounded-lg bg-blue-50/50 border border-blue-100">
        <legend className="text-[10px] font-semibold text-blue-500 uppercase tracking-wider mb-2">Planner Bridge</legend>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.create_repair_defect}
                onChange={e => set('create_repair_defect', e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span className="text-xs text-gray-600">Create Repair Defect</span>
            </label>
          </div>
          {form.create_repair_defect && (
            <div>
              <label className="text-xs text-gray-600 block mb-1">Corridor</label>
              <select value={form.corridor || ''}
                onChange={e => set('corridor', e.target.value)}
                className="input input-sm" required>
                <option value="">Select...</option>
                {CORRIDOR_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          )}
        </div>
      </fieldset>

      <Button type="submit" variant="primary" loading={loading} fullWidth>
        Run Decision Engine
      </Button>
    </form>
  );
}
