// frontend/src/pages/board.tsx
import { useEffect, useState } from 'react';
import { DefectList } from '@/components/board/DefectList';
import { api } from '@/api/client';
import { Defect, FilterParams } from '@/types';
import toast from 'react-hot-toast';

export default function BoardPage() {
  const [defects, setDefects] = useState<Defect[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterParams>({});

  useEffect(() => {
    loadDefects();
  }, [filters]);

  const loadDefects = async () => {
    setLoading(true);
    try {
      const data = await api.getDefects(filters);
      setDefects(data);
    } catch (error) {
      toast.error('Failed to load defects');
    } finally {
      setLoading(false);
    }
  };

  const handleSchedule = async (id: string) => {
    try {
      await api.scoreDefect(id);
      toast.success(`Defect ${id} scheduled`);
      loadDefects();
    } catch (error) {
      toast.error('Failed to schedule');
    }
  };

  const handleDefer = async (id: string) => {
    toast.success(`Defect ${id} deferred with reason`);
    loadDefects();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Board</h1>
          <p className="text-sm text-gray-500">Defect prioritization and scoring</p>
        </div>
        <div className="text-sm text-gray-500">
          {defects.length} defects · {defects.filter(d => d.tier === 'safety-critical').length} critical
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="spinner h-8 w-8" />
        </div>
      ) : (
        <DefectList
          defects={defects}
          filters={filters}
          onFilterChange={setFilters}
          onSchedule={handleSchedule}
          onDefer={handleDefer}
        />
      )}
    </div>
  );
}