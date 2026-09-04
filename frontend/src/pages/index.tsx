// src/pages/index.tsx
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { LayoutDashboard, ArrowRight } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  
  useEffect(() => {
    // Auto-redirect to board after a short delay
    const timer = setTimeout(() => {
      router.push('/board');
    }, 800);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="text-center animate-fade-in">
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-4xl shadow-xl animate-bounce-in">
            🚂
          </div>
        </div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-2">
          Block Planner
        </h1>
        <p className="text-gray-500 mb-6">AI-Powered Defect Scheduling</p>
        <div className="flex items-center justify-center gap-2 text-sm text-blue-600 font-medium animate-pulse">
          <span>Redirecting to Board</span>
          <LayoutDashboard className="w-4 h-4" />
          <ArrowRight className="w-4 h-4" />
        </div>
        <div className="mt-4 flex justify-center">
          <div className="spinner-sm" />
        </div>
      </div>
    </div>
  );
}