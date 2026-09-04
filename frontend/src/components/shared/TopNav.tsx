// src/components/shared/TopNav.tsx
import Link from 'next/link';
import { useRouter } from 'next/router';

export function TopNav() {
  const router = useRouter();
  
  const navItems = [
    { href: '/', label: 'Dashboard' },
    { href: '/board', label: 'Board' },
    { href: '/plan', label: 'Plan' },
    { href: '/live', label: 'Live' },
    { href: '/impact', label: 'Impact' },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link href="/" className="text-xl font-bold text-gray-800">
            🚂 Block Planner
          </Link>
          <div className="flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = router.pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full">
            ● Live
          </span>
        </div>
      </div>
    </nav>
  );
}
