'use client';

import { useEffect, useState } from 'react';

interface Defect {
  id: number;
  department: string;
  severity: string;
  description: string;
}

export default function Home() {
  const [defects, setDefects] = useState<Defect[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState('Checking...');

  useEffect(() => {
    // Check backend health
    fetch('http://localhost:8000/api/health')
      .then(res => res.json())
      .then(() => setBackendStatus('✅ Online'))
      .catch(() => setBackendStatus('❌ Offline'));

    // Fetch defects
    fetch('http://localhost:8000/api/defects')
      .then(res => res.json())
      .then(data => {
        setDefects(data.defects);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching defects:', err);
        setLoading(false);
      });
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold text-blue-600">🚂 The Flow</h1>
          <div className="px-4 py-2 bg-white rounded-lg shadow">
            Backend: {backendStatus}
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Defects</h2>
          
          {loading ? (
            <p className="text-gray-500">Loading defects...</p>
          ) : defects.length === 0 ? (
            <p className="text-gray-500">No defects found</p>
          ) : (
            <div className="space-y-3">
              {defects.map((defect) => (
                <div key={defect.id} className="border rounded-lg p-4 hover:shadow-md transition">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold">{defect.description}</h3>
                      <p className="text-sm text-gray-500">Department: {defect.department}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      defect.severity === 'Critical' ? 'bg-red-100 text-red-800' :
                      defect.severity === 'High' ? 'bg-orange-100 text-orange-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {defect.severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-8 text-center text-gray-500 text-sm">
          🚀 The Flow - Railway Block Planning System
        </div>
      </div>
    </main>
  );
}
