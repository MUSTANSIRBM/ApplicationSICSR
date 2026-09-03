// src/pages/plan.tsx
import { useEffect, useState } from 'react';
import { Timeline } from '@/components/plan/Timeline';
import { api } from '@/api/client';
import { TimelineData } from '@/types';
import toast from 'react-hot-toast';

export default function PlanPage() {
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [week, setWeek] = useState('');

  useEffect(() => {
    const today = new Date();
    const start = new Date(today);
    start.setDate(today.getDate() - today.getDay());
    setWeek(start.toISOString());
  }, []);

  useEffect(() => {
    if (week) {
      loadSchedule();
    }
  }, [week]);

  const loadSchedule = async () => {
    setLoading(true);
    try {
      const data = await api.getSchedule(week);
      setData(data);
    } catch (error) {
      toast.error('Failed to load schedule');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveBlock(id);
      toast.success(`Block ${id} approved`);
      loadSchedule();
    } catch (error) {
      toast.error('Failed to approve');
    }
  };

  const handleLock = async (id: string) => {
    try {
      await api.lockBlock(id);
      toast.success(`Block ${id} locked`);
      loadSchedule();
    } catch (error) {
      toast.error('Failed to lock');
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plan</h1>
          <p className="text-sm text-gray-500">
            Week of {new Date(data.weekStart).toLocaleDateString()} – {new Date(data.weekEnd).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>{data.blocks.length} blocks</span>
          <span>·</span>
          <span>{data.blocks.filter(b => b.isCombined).length} combined</span>
        </div>
      </div>

      <Timeline data={data} onApprove={handleApprove} onLock={handleLock} />
    </div>
  );
}