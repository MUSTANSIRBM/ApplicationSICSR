// src/components/shared/NotificationDropdown.tsx
import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  Bell, 
  Check, 
  X, 
  AlertCircle, 
  CheckCircle, 
  Info, 
  AlertTriangle,
  Trash2,
  CheckCheck
} from 'lucide-react';
import { useNotificationStore } from '@/store/useNotificationStore';
import { formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';

export function NotificationDropdown() {
  const router = useRouter();
  const { 
    notifications, 
    unreadCount, 
    isOpen, 
    setOpen,
    markAsRead, 
    markAllAsRead, 
    deleteNotification,
    clearAll 
  } = useNotificationStore();
  
  const [isHovered, setIsHovered] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [setOpen]);

  // Close dropdown on route change
  useEffect(() => {
    setOpen(false);
  }, [router.pathname, setOpen]);

  const getIcon = (type: string) => {
    switch(type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch(type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  const handleNotificationClick = (notification: any) => {
    markAsRead(notification.id);
    if (notification.link) {
      setOpen(false);
      router.push(notification.link);
    }
  };

  const handleMarkAllRead = () => {
    markAllAsRead();
  };

  const handleClearAll = () => {
    if (notifications.length === 0) return;
    if (window.confirm('Clear all notifications?')) {
      clearAll();
    }
  };

  const formatTime = (date: string) => {
    try {
      return formatDistanceToNow(new Date(date), { addSuffix: true });
    } catch {
      return 'Unknown time';
    }
  };

  return (
    <div ref={dropdownRef} className="relative">
      {/* Bell Button */}
      <button
        onClick={() => setOpen(!isOpen)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={clsx(
          'relative p-2 rounded-lg transition-all duration-200',
          isOpen || isHovered 
            ? 'bg-blue-50 text-blue-600' 
            : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
        )}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className={clsx(
            'absolute -top-0.5 -right-0.5 flex items-center justify-center',
            'min-w-[20px] h-5 px-1.5 rounded-full',
            'bg-red-500 text-white text-[10px] font-bold',
            'animate-bounce-in shadow-lg shadow-red-500/25'
          )}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-[420px] max-h-[500px] bg-white rounded-2xl shadow-2xl border border-gray-200/80 overflow-hidden animate-slide-down z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200/80 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-blue-600" />
              <span className="font-semibold text-gray-900">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-medium">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="p-1.5 text-gray-400 hover:text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-4 h-4" />
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={handleClearAll}
                  className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  title="Clear all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Notification List */}
          <div className="overflow-y-auto max-h-[400px] scrollbar-thin">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4">
                <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                  <Bell className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-sm font-medium text-gray-600">No notifications</p>
                <p className="text-xs text-gray-400 mt-1">You're all caught up!</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={clsx(
                    'group relative flex items-start gap-3 px-4 py-3 border-b border-gray-100/80 transition-all duration-200 cursor-pointer',
                    !notification.read ? 'bg-blue-50/50 hover:bg-blue-50' : 'hover:bg-gray-50',
                    'hover:pl-5'
                  )}
                  onClick={() => handleNotificationClick(notification)}
                >
                  {/* Unread dot */}
                  {!notification.read && (
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-500" />
                  )}

                  {/* Icon */}
                  <div className={clsx(
                    'flex-shrink-0 p-1.5 rounded-lg border',
                    getTypeColor(notification.type)
                  )}>
                    {getIcon(notification.type)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {notification.title}
                      </p>
                      <span className="text-[10px] text-gray-400 whitespace-nowrap">
                        {formatTime(notification.createdAt)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2">
                      {notification.message}
                    </p>
                    {notification.link && (
                      <span className="text-[10px] text-blue-600 font-medium mt-0.5 inline-block">
                        Click to view →
                      </span>
                    )}
                  </div>

                  {/* Delete button (hover) */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteNotification(notification.id);
                    }}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-all duration-200"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2.5 border-t border-gray-200/80 bg-gray-50/50 text-center">
              <p className="text-[10px] text-gray-400">
                {notifications.filter(n => !n.read).length} unread · {notifications.length} total
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}