// src/pages/_app.tsx
import type { AppProps } from 'next/app';
import { Toaster } from 'react-hot-toast';
import { TopNav } from '@/components/shared/TopNav';
import { StatusBar } from '@/components/shared/StatusBar';
import '@/styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <div className="min-h-screen bg-gray-50">
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
      <main className="pb-12">
        <Component {...pageProps} />
      </main>
      <StatusBar />
    </div>
  );
}