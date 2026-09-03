import { useEffect } from 'react';
import { MetricCard } from '@/components/impact/MetricCard';
import { SavingsChart } from '@/components/impact/SavingsChart';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';

export default function ImpactPage() {
  const { impactData, selectedWeek, loadImpact } = useStore();

  useEffect(() => {
    loadImpact(selectedWeek);
  }, [selectedWeek]);

  const handleRefresh = async () => {
    try {
      await loadImpact(selectedWeek);
      toast.success('📊 Data refreshed');
    } catch (error) {
      toast.error('❌ Failed to refresh data');
    }
  };

  if (!impactData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner h-8 w-8" />
      </div>
    );
  }

  const data = impactData;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Impact Dashboard</h1>
          <p className="text-sm text-gray-500">{data.week}</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handleRefresh}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            🔄 Refresh
          </button>
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            📄 Export PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard
          title="Total Savings"
          value={`${data.hoursSaved}h`}
          subtitle={`${data.savingsPercentage}% reduction`}
          description="Total hours saved through optimized scheduling"
          icon="💰"
          color="green"
          animate
        />
        <MetricCard
          title="Cost Savings"
          value={`₹${(data.costSavings / 100000).toFixed(1)}L`}
          subtitle="Estimated annual savings"
          description="Based on average operational costs"
          icon="📊"
          color="blue"
          animate
        />
        <MetricCard
          title="Corridor Utilization"
          value={`${data.corridorUtilizationAfter}%`}
          subtitle={`${data.corridorUtilizationAfter - data.corridorUtilizationBefore}% improvement`}
          description="Percentage of available corridor time used"
          icon="📈"
          color="yellow"
          change={Math.round((data.corridorUtilizationAfter - data.corridorUtilizationBefore) / data.corridorUtilizationBefore * 100)}
          trend="up"
          animate
        />
        <MetricCard
          title="Bundling Savings"
          value={`${data.breakdown.bundling}h`}
          subtitle={`${data.breakdown.betterTiming}h from better timing`}
          description="Hours saved by grouping related tasks"
          icon="🔗"
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <SavingsChart data={data} />
        </div>

        <div className="card">
          <h4 className="text-sm font-medium text-gray-700 mb-3">By Department</h4>
          <div className="space-y-2">
            {Object.entries(data.byDepartment).map(([dept, hours]) => (
              <div key={dept}>
                <div className="flex justify-between text-sm">
                  <span className="capitalize text-gray-600">{dept}</span>
                  <span className="font-medium text-gray-900">{hours}h</span>
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden mt-0.5">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(hours / Math.max(...Object.values(data.byDepartment))) * 100}%`,
                      backgroundColor: dept === 'track' ? '#F97316' : dept === 'power' ? '#EAB308' : '#3B82F6'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Total savings breakdown:</span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Bundling: {data.breakdown.bundling}h · Better Timing: {data.breakdown.betterTiming}h
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}