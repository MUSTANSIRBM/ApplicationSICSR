// src/components/shared/TopNav.tsx
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { clsx } from 'clsx';
import { 
  LayoutDashboard, Calendar, Zap, BarChart3, User, Menu, X, LogOut, UserCircle 
} from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { NotificationDropdown } from './NotificationDropdown';

const tabs = [
  { name: 'Board', href: '/board', icon: LayoutDashboard },
  { name: 'Plan', href: '/plan', icon: Calendar },
  { name: 'Live', href: '/live', icon: Zap },
  { name: 'Impact', href: '/impact', icon: BarChart3 },
];

export function TopNav() {
  const router = useRouter();
  const { logout, user } = useAuthStore();
  const [isLive, setIsLive] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [router.pathname]);

  const handleLogout = async () => {
    await logout();
  };

  const getUserInitials = () => {
    if (!user?.name) return 'U';
    const names = user.name.split(' ');
    if (names.length === 1) return names[0].charAt(0).toUpperCase();
    return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
  };

  return (
    <nav className={clsx(
      'sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200/80 transition-shadow duration-200',
      scrolled && 'shadow-sm'
    )}>
      <div className="flex items-center justify-between px-4 py-2 max-w-7xl mx-auto">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md">
            <span className="text-lg">🚂</span>
          </div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Block Planner
            </h1>
            <span className="text-[10px] text-gray-400 font-medium tracking-wider uppercase hidden sm:inline">
              AI-Powered Scheduling
            </span>
          </div>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = router.pathname === tab.href;
            const Icon = tab.icon;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                <Icon className={clsx('w-4 h-4', isActive && 'text-blue-600')} />
                {tab.name}
              </Link>
            );
          })}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2">
          {/* Status indicator */}
          <div className="hidden sm:flex items-center gap-2 text-sm">
            <span className={clsx(
              'h-2 w-2 rounded-full',
              isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            )} />
            <span className="text-gray-600 font-medium">{isLive ? 'Live' : 'Offline'}</span>
          </div>

          {/* User name */}
          {user && (
            <span className="hidden sm:inline text-sm font-medium text-gray-700">
              {user.name}
            </span>
          )}

          {/* Notification Bell - Now Active */}
          <NotificationDropdown />

          {/* User avatar - Clickable to Profile */}
          <Link href="/profile">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm shadow-md cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200">
              {getUserInitials()}
            </div>
          </Link>

          {/* Logout button */}
          <button
            onClick={handleLogout}
            className="hidden md:flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200/80 bg-white/95 backdrop-blur-lg animate-slide-down">
          <div className="px-4 py-3 space-y-1">
            {tabs.map((tab) => {
              const isActive = router.pathname === tab.href;
              const Icon = tab.icon;
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={clsx(
                    'flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200',
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  )}
                >
                  <Icon className={clsx('w-5 h-5', isActive && 'text-blue-600')} />
                  {tab.name}
                </Link>
              );
            })}
            
            {/* Mobile Profile */}
            <Link
              href="/profile"
              className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <UserCircle className="w-5 h-5" />
              Profile
            </Link>
            
            {/* Mobile logout */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-4 py-3 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full"
            >
              <LogOut className="w-5 h-5" />
              Logout
            </button>
            
            {/* Mobile status */}
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-gray-500 border-t border-gray-100 mt-2">
              <span className={clsx(
                'h-2 w-2 rounded-full',
                isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
              )} />
              <span>{isLive ? 'Live' : 'Offline'}</span>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}