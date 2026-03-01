
import React, { useState, useEffect } from 'react';

interface Control {
  id: string;
  title: string;
  description: string;
  domain: string;
  level: string;
}

interface ControlResponse {
  control: Control;
  implementation_status: string;
  evidence_count: number;
  confidence: number;
  poam_required: boolean;
}

const ControlExplorer: React.FC = () => {
  const [controls, setControls] = useState<ControlResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');

  const fetchControls = async () => {
    setLoading(true);
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/api/controls/`);
      const data = await res.json();
      setControls(data.controls);
    } catch (error) {
      console.error('Error fetching controls:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchControls();
  }, []);

  const filtered = controls.filter(c =>
    (c.control.id.toLowerCase().includes(filter.toLowerCase()) ||
     c.control.title.toLowerCase().includes(filter.toLowerCase())) &&
    (domainFilter === '' || c.control.domain === domainFilter)
  );

  const domains = Array.from(new Set(controls.map(c => c.control.domain))).sort();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 mt-12 overflow-hidden">
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-gray-800">CMMC Control Explorer</h3>
          <p className="text-xs text-gray-500 uppercase tracking-widest">Browse, filter, and audit all CMMC practices</p>
        </div>
        <div className="flex gap-4">
            <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="text-sm border border-gray-300 rounded-md px-2 py-1"
            >
                <option value="">All Domains</option>
                {domains.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <input
                type="text"
                placeholder="Search ID or title..."
                className="text-sm border border-gray-300 rounded-md px-2 py-1"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
            />
        </div>
      </div>
      <div className="p-0 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 text-[10px] text-gray-500 uppercase font-bold">
            <tr>
              <th className="px-6 py-3 text-left">ID</th>
              <th className="px-6 py-3 text-left">Practice Title</th>
              <th className="px-6 py-3 text-left">Level</th>
              <th className="px-6 py-3 text-left">Status</th>
              <th className="px-6 py-3 text-left">Evidence</th>
              <th className="px-6 py-3 text-left">Confidence</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200 text-sm">
            {loading ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">Loading controls...</td></tr>
            ) : filtered.map((c) => (
              <tr key={c.control.id} className="hover:bg-gray-50 transition">
                <td className="px-6 py-4 font-bold text-blue-700">{c.control.id}</td>
                <td className="px-6 py-4 text-gray-900">{c.control.title}</td>
                <td className="px-6 py-4 text-xs">
                    <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded">{c.control.level}</span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-black uppercase ${
                    c.implementation_status === 'implemented' ? 'bg-green-100 text-green-700' :
                    c.implementation_status === 'partially_implemented' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {c.implementation_status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">{c.evidence_count}</td>
                <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5 w-12">
                            <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${c.confidence * 100}%` }}></div>
                        </div>
                        <span className="text-[10px] font-bold">{Math.round(c.confidence * 100)}%</span>
                    </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ControlExplorer;
