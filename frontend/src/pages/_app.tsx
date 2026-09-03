// src/pages/_app.tsx
import type { AppProps } from 'next/app';
import { TopNav } from '@/components/shared/TopNav';
import { StatusBar } from '@/components/shared/StatusBar';
import '@/styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <TopNav />
      <Component {...pageProps} />
      <StatusBar />
    </>
  );
}
