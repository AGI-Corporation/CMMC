
import React, { useState, useEffect } from 'react';

interface Evidence {
  id: string;
  control_id: string;
  zt_pillar: string;
  title: string;
  evidence_type: string;
  source_system: string;
  created_at: string;
  metadata?: any;
}

const EvidenceManager: React.FC = () => {
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchEvidence = async () => {
    setLoading(true);
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

  useEffect(() => {
    fetchEvidence();
  }, []);

  const handleReview = async (id: string, status: string) => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      await fetch(`${baseUrl}/api/evidence/${id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer_notes: reviewNotes, status })
      });
      setReviewingId(null);
      setReviewNotes('');
      fetchEvidence();
    } catch (err) {
      console.error(err);
    }
  };

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
                <td className="px-6 py-4">
                    <button
                        onClick={() => setReviewingId(ev.id)}
                        className="text-[10px] font-bold text-blue-600 hover:text-blue-800 uppercase tracking-tighter"
                    >
                        Review
                    </button>
                    {ev.metadata?.review_status && (
                        <div className={`mt-1 text-[8px] font-black uppercase ${ev.metadata.review_status === 'approved' ? 'text-green-600' : 'text-amber-600'}`}>
                            {ev.metadata.review_status}
                        </div>
                    )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {reviewingId && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-8 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-gray-900 mb-4 text-center">Evidence Review</h3>
            <textarea
              className="w-full border border-gray-300 rounded-lg p-3 text-sm h-32 outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              placeholder="Add your review notes here..."
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleReview(reviewingId, 'approved')}
                className="bg-green-600 text-white py-2 rounded-lg font-bold hover:bg-green-700 transition"
              >
                Approve
              </button>
              <button
                onClick={() => handleReview(reviewingId, 'needs_work')}
                className="bg-amber-500 text-white py-2 rounded-lg font-bold hover:bg-amber-600 transition"
              >
                Needs Work
              </button>
            </div>
            <button
                onClick={() => setReviewingId(null)}
                className="w-full mt-4 text-gray-400 text-xs font-bold uppercase"
            >
                Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvidenceManager;
