// src/pages/live.tsx
import { useEffect } from 'react';
import { BeforeAfterView } from '@/components/live/BeforeAfterView';
import { DefectInjector } from '@/components/live/DefectInjector';
import { useStore } from '@/store/useStore';
import { withAuth } from '@/hoc/withAuth';
import toast from 'react-hot-toast';

function LivePage() {
  const { 
    timelineData, 
    loading, 
    selectedWeek,
    loadSchedule,
    injectDefect
  } = useStore();

  useEffect(() => {
    loadSchedule(selectedWeek);
  }, [selectedWeek]);

  const handleInject = async (defect: any) => {
    try {
      const result = await injectDefect(defect);
      toast.success(`✅ Defect injected successfully`);
      await loadSchedule(selectedWeek);
    } catch (error: any) {
      toast.error(`❌ Failed to inject defect: ${error.message || 'Unknown error'}`);
    }
  };

  const beforeBlocks = timelineData?.blocks || [];
  const afterBlocks = timelineData?.blocks || [];
  const corridors = timelineData?.corridors || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live View</h1>
          <p className="text-sm text-gray-500">
            Real-time schedule comparison and defect injection
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <BeforeAfterView 
            beforeBlocks={beforeBlocks}
            afterBlocks={afterBlocks}
            corridors={corridors}
            loading={loading}
          />
        </div>
        <div className="lg:col-span-1">
          <DefectInjector onInject={handleInject} loading={loading} />
        </div>
      </div>
    </div>
  );
}

export default withAuth(LivePage);