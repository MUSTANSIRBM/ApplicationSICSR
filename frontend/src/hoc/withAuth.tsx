// src/hoc/withAuth.tsx
import { useEffect, ComponentType } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store/useAuthStore';

export function withAuth<P extends object>(WrappedComponent: ComponentType<P>) {
  return function WithAuthComponent(props: P) {
    const router = useRouter();
    const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

    useEffect(() => {
      const verifyAuth = async () => {
        const isValid = await checkAuth();
        if (!isValid) {
          router.push('/login');
        }
      };
      
      if (!isAuthenticated) {
        verifyAuth();
      }
    }, [isAuthenticated, checkAuth, router]);

    // Show loading while checking auth
    if (isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
          <div className="flex flex-col items-center gap-4">
            <div className="spinner" />
            <p className="text-sm text-gray-500 animate-pulse">Verifying authentication...</p>
          </div>
        </div>
      );
    }

    // If not authenticated, return null (will redirect)
    if (!isAuthenticated) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}