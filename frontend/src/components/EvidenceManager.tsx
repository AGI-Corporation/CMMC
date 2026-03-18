
import React, { useState, useEffect } from 'react';

interface Evidence {
  id: string;
  control_id: string;
  zt_pillar: string;
  title: string;
  evidence_type: string;
  source_system: string;
  created_at: string;
}

const EvidenceManager: React.FC = () => {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvidence = async () => {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      try {
        const res = await fetch(`${baseUrl}/api/evidence/`);
        const data = await res.json();
        setEvidence(data.evidence || []);
      } catch (error) {
        console.error('Error fetching evidence:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchEvidence();
  }, []);

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Evidence Vault</h1>
        <p className="text-gray-600">Secure storage and mapping for compliance evidence.</p>
      </header>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 text-[10px] text-gray-500 uppercase font-bold">
            <tr>
              <th className="px-6 py-3 text-left">Title & Type</th>
              <th className="px-6 py-3 text-left">Source System</th>
              <th className="px-6 py-3 text-left">Control Mapping</th>
              <th className="px-6 py-3 text-left">ZT Pillar</th>
              <th className="px-6 py-3 text-left">Timestamp</th>
              <th className="px-6 py-3 text-left">Fingerprint</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200 text-sm">
            {loading ? (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">Loading evidence...</td></tr>
            ) : evidence.length === 0 ? (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">No evidence recorded yet.</td></tr>
            ) : evidence.map((ev) => (
              <tr key={ev.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="font-semibold text-gray-900">{ev.title}</div>
                  <div className="text-[10px] text-gray-400 uppercase font-bold">{ev.evidence_type}</div>
                </td>
                <td className="px-6 py-4 text-gray-600 font-medium">{ev.source_system}</td>
                <td className="px-6 py-4 text-blue-700 font-bold">{ev.control_id}</td>
                <td className="px-6 py-4">
                  <span className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-[10px] font-black uppercase tracking-wider">{ev.zt_pillar}</span>
                </td>
                <td className="px-6 py-4 text-gray-500 text-xs">{new Date(ev.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 font-mono text-[10px] text-gray-400">
                  {ev.id.substring(0, 16)}...
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EvidenceManager;
