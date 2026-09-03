import { useState, useEffect, useMemo, useRef } from 'react';
import { clsx } from 'clsx';
import { Defect, FilterParams } from '@/types';
import { DefectCard } from './DefectCard';
import { Badge } from '@/components/ui/Badge';

interface DefectListProps {
  defects: Defect[];
  filters: FilterParams;
  onFilterChange: (filters: FilterParams) => void;
  onSchedule: (id: string) => void;
  onDefer: (id: string) => void;
  onDelete: (id: string) => void;
  onSearch: (query: string) => void;
  searchQuery: string;
}

const departments = ['all', 'track', 'power', 'signals'] as const;
const tiers = ['all', 'safety-critical', 'high', 'normal', 'deferred'] as const;

export function DefectList({ 
  defects, 
  filters, 
  onFilterChange, 
  onSchedule, 
  onDefer,
  onDelete,
  onSearch,
  searchQuery 
}: DefectListProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery || '');
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Update local search when prop changes (from external)
  useEffect(() => {
    setLocalSearch(searchQuery || '');
  }, [searchQuery]);

  // Handle Enter key press
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      performSearch(localSearch);
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      setLocalSearch('');
      performSearch('');
      inputRef.current?.blur();
    }
  };

  // Perform search
  const performSearch = (query: string) => {
    setIsSearching(true);
    onSearch(query);
    // Reset searching state after a short delay
    setTimeout(() => setIsSearching(false), 300);
  };

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalSearch(value);
    // Clear search if input is empty
    if (value === '') {
      performSearch('');
    }
  };

  // Handle search button click
  const handleSearchClick = () => {
    performSearch(localSearch);
  };

  // Handle clear search
  const handleClearSearch = () => {
    setLocalSearch('');
    performSearch('');
    inputRef.current?.focus();
  };

  // Sort defects by severity (highest first)
  const sortedDefects = useMemo(() => {
    const severityOrder = { 'safety-critical': 4, high: 3, normal: 2, deferred: 1 };
    return [...defects].sort((a, b) => {
      const tierDiff = (severityOrder[b.tier] || 0) - (severityOrder[a.tier] || 0);
      if (tierDiff !== 0) return tierDiff;
      return b.score - a.score;
    });
  }, [defects]);

  const groupedDefects = sortedDefects.reduce((acc, d) => {
    if (!acc[d.tier]) acc[d.tier] = [];
    acc[d.tier].push(d);
    return acc;
  }, {} as Record<string, Defect[]>);

  const tierOrder = ['safety-critical', 'high', 'normal', 'deferred'];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px] relative">
          <div className="relative flex items-center">
            {/* Search Icon */}
            <div className="absolute left-3 text-gray-400 pointer-events-none">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            
            {/* Search Input */}
            <input
              ref={inputRef}
              type="text"
              placeholder="Search by ID, description, or department..."
              value={localSearch}
              onChange={handleSearchChange}
              onKeyDown={handleKeyDown}
              className={clsx(
                "w-full pl-9 pr-20 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
                isSearching ? "bg-gray-50" : "bg-white",
                localSearch ? "border-blue-300" : "border-gray-200"
              )}
              style={{
                caretColor: '#3B82F6',
              }}
            />
            
            {/* Search Actions */}
            <div className="absolute right-1 flex items-center gap-1">
              {localSearch && (
                <button
                  onClick={handleClearSearch}
                  className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
                  title="Clear search"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
              <button
                onClick={handleSearchClick}
                className={clsx(
                  "px-3 py-1 text-sm font-medium rounded-md transition-colors",
                  localSearch 
                    ? "bg-blue-600 text-white hover:bg-blue-700" 
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                )}
                disabled={!localSearch}
                title="Press Enter or click to search"
              >
                Search
              </button>
            </div>
          </div>
          
          {/* Search Results Count & Hint */}
          <div className="flex items-center justify-between mt-1 px-1">
            {searchQuery && (
              <span className="text-xs text-gray-500">
                Found <span className="font-medium text-gray-700">{defects.length}</span> results for "<span className="font-medium text-gray-700">{searchQuery}</span>"
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-xs text-gray-400 mr-1">Dept:</span>
          {departments.map((dept) => (
            <button
              key={dept}
              onClick={() => {
                const newFilters = { 
                  ...filters, 
                  department: dept === 'all' ? undefined : dept 
                };
                if (searchQuery) {
                  newFilters.search = searchQuery;
                }
                onFilterChange(newFilters);
              }}
              className={clsx(
                'px-2 py-1 text-xs rounded-md transition-colors capitalize',
                (filters.department === dept || (dept === 'all' && !filters.department))
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {dept}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-xs text-gray-400 mr-1">Tier:</span>
          {tiers.map((tier) => (
            <button
              key={tier}
              onClick={() => {
                const newFilters = { 
                  ...filters, 
                  tier: tier === 'all' ? undefined : tier 
                };
                if (searchQuery) {
                  newFilters.search = searchQuery;
                }
                onFilterChange(newFilters);
              }}
              className={clsx(
                'px-2 py-1 text-xs rounded-md transition-colors capitalize',
                (filters.tier === tier || (tier === 'all' && !filters.tier))
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {tier.replace('-', ' ')}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-500 ml-auto">
          {defects.length} defects · {defects.filter(d => d.tier === 'safety-critical').length} critical
        </span>
      </div>

      <div className="space-y-3">
        {tierOrder.map((tier) => {
          const items = groupedDefects[tier] || [];
          if (items.length === 0) return null;
          
          return (
            <div key={tier}>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={tier as any}>{tier}</Badge>
                <span className="text-xs text-gray-500">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map(defect => (
                  <DefectCard
                    key={defect.id}
                    defect={defect}
                    onSchedule={onSchedule}
                    onDefer={onDefer}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}