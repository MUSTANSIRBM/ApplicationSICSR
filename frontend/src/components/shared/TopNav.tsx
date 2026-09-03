// frontend/src/components/shared/TopNav.tsx
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { clsx } from 'clsx';

const tabs = [
  { name: 'Board', href: '/board', icon: '📋' },
  { name: 'Plan', href: '/plan', icon: '📅' },
  { name: 'Live', href: '/live', icon: '⚡' },
  { name: 'Impact', href: '/impact', icon: '📈' },
];

export function TopNav() {
  const router = useRouter();
  const [isLive] = useState(true);

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-2">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🚂</span>
            <h1 className="text-xl font-bold text-gray-900">Block Planner</h1>
          </div>
          <div className="flex items-center gap-1 ml-4">
            {tabs.map(tab => (
              <Link
                key={tab.href}
                href={tab.href}
                className={clsx(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  router.pathname === tab.href
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.name}
              </Link>
            ))}
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <span className={clsx(
              'h-2 w-2 rounded-full',
              isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            )} />
            <span className="text-gray-600">{isLive ? 'Live' : 'Offline'}</span>
          </div>
          <button className="text-gray-400 hover:text-gray-600 transition-colors">
            <span className="text-lg">🔔</span>
          </button>
          <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-medium text-sm">
            JD
          </div>
        </div>
      </div>
    </nav>
  );
}