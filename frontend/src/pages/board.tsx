// src/pages/board.tsx
import { useEffect, useState } from 'react';
import { DefectList } from '@/components/board/DefectList';
import { Defect, FilterParams } from '@/types';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';

export default function BoardPage() {
  const { 
    defects, 
    loading, 
    filters, 
    searchQuery,
    loadDefects, 
    scheduleDefect, 
    deferDefect, 
    setFilters, 
    setSearchQuery 
  } = useStore();

  useEffect(() => {
    loadDefects();
  }, []);

  const handleSchedule = async (id: string) => {
    try {
      await scheduleDefect(id);
      toast.success(`✅ Defect ${id} scheduled successfully`);
    } catch (error) {
      toast.error('❌ Failed to schedule defect');
    }
  };

  const handleDefer = async (id: string) => {
    try {
      await deferDefect(id);
      toast.success(`⏳ Defect ${id} deferred`);
    } catch (error) {
      toast.error('❌ Failed to defer defect');
    }
  };

  const handleFilterChange = (newFilters: FilterParams) => {
    setFilters(newFilters);
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
          onFilterChange={handleFilterChange}
          onSchedule={handleSchedule}
          onDefer={handleDefer}
          onSearch={setSearchQuery}
          searchQuery={searchQuery}
        />
      )}
    </div>
  );
}