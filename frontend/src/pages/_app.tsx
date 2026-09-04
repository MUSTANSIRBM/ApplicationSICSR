// src/pages/_app.tsx
import type { AppProps } from 'next/app';
import { Toaster } from 'react-hot-toast';
import { TopNav } from '@/components/shared/TopNav';
import { StatusBar } from '@/components/shared/StatusBar';
import { useAuthStore } from '@/store/useAuthStore';
import { useNotificationStore } from '@/store/useNotificationStore';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import '@/styles/globals.css';
import Head from 'next/head';

// Import with explicit path to ensure it's loaded
import '../styles/globals.css';

// Pages that don't require authentication
const publicPages = ['/login', '/register', '/forgot-password'];

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);
  const isPublicPage = publicPages.includes(router.pathname);

  // Initialize notification store
  useEffect(() => {
    const { getUnreadCount } = useNotificationStore.getState();
    getUnreadCount();
  }, []);

  // Force CSS reload on authentication change
  useEffect(() => {
    const styleTag = document.getElementById('global-css');
    if (styleTag) {
      styleTag.setAttribute('data-force-reload', Date.now().toString());
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const initAuth = async () => {
      await checkAuth();
      setIsInitialized(true);
    };
    initAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (!isInitialized) return;
    if (!isAuthenticated && !isPublicPage) {
      router.push('/login');
      return;
    }
    if (isAuthenticated && isPublicPage) {
      router.push('/board');
      return;
    }
  }, [isAuthenticated, isInitialized, isPublicPage, router]);

  // Show loading while checking auth
  if (!isInitialized || (isLoading && !isPublicPage)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-3xl shadow-lg animate-bounce-in">
            🚂
          </div>
          <div className="spinner" />
          <p className="text-sm text-gray-500 animate-pulse">Loading...</p>
        </div>
      </div>
    );
  }

  const showNavigation = isAuthenticated && !isPublicPage;

  return (
    <>
      <Head>
        <title>AI Block Planning</title>
        <meta name="description" content="Intelligent defect scheduling and planning" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <div className="min-h-screen bg-gray-50">
        {showNavigation && <TopNav />}
        <main className={showNavigation ? 'pb-14' : ''}>
          <Component {...pageProps} />
        </main>
        {showNavigation && <StatusBar />}
      </div>
      
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#FFFFFF',
            color: '#1F2937',
            borderRadius: '12px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.12)',
            padding: '16px 20px',
            fontSize: '14px',
            fontWeight: '500',
          },
          success: {
            iconTheme: {
              primary: '#22C55E',
              secondary: '#FFFFFF',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#FFFFFF',
            },
          },
        }}
      />
    </>
  );
}