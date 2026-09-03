// src/pages/_app.tsx
import type { AppProps } from 'next/app';
import { Toaster } from 'react-hot-toast';
import { TopNav } from '@/components/shared/TopNav';
import { StatusBar } from '@/components/shared/StatusBar';
import '@/styles/globals.css';
import { useEffect } from 'react';
import { useStore } from '@/store/useStore';

export default function App({ Component, pageProps }: AppProps) {
  const loadStatus = useStore(state => state.loadStatus);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
            borderRadius: '8px',
            fontSize: '14px',
          },
          success: {
            style: {
              background: '#22C55E',
            },
          },
          error: {
            style: {
              background: '#EF4444',
            },
          },
        }}
      />
      <TopNav />
      <main className="flex-1 pb-14">
        <Component {...pageProps} />
      </main>
      <StatusBar />
    </div>
  );
}