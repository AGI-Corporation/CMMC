
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
  notes?: string;
  confidence: number;
  poam_required: boolean;
  assessor?: string;
  assessment_date?: string;
  fingerprint?: string;
}

const ControlExplorer: React.FC<{ framework?: string }> = ({ framework: initialFramework }) => {
  const [framework, setFramework] = useState(initialFramework || 'CMMC');
  const [controls, setControls] = useState<ControlResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [selectedControl, setSelectedControl] = useState<ControlResponse | null>(null);
  const [mappings, setMappings] = useState<any[]>([]);
  const [remediationScript, setRemediationScript] = useState<string | null>(null);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  const fetchControls = async () => {
    setLoading(true);
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/api/controls/?framework=${framework}`);
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
  }, [framework]);

  useEffect(() => {
    if (selectedControl) {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        fetch(`${baseUrl}/api/assessment/mapping/${selectedControl.control.id}`)
            .then(res => res.json())
            .then(data => setMappings(data.mapped_controls || []))
            .catch(err => console.error(err));
    } else {
        setMappings([]);
        setRemediationScript(null);
    }
  }, [selectedControl]);

  const generateRemediation = async () => {
    if (!selectedControl) return;
    setIsGeneratingScript(true);
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
        const res = await fetch(`${baseUrl}/api/agents/mistral/remediation-script`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                control_id: selectedControl.control.id,
                gap_summary: selectedControl.notes || "Control is not fully implemented."
            })
        });
        const data = await res.json();
        setRemediationScript(data.script);
    } catch (err) {
        console.error(err);
    } finally {
        setIsGeneratingScript(false);
    }
  };

  const filtered = controls.filter(c =>
    (c.control.id.toLowerCase().includes(filter.toLowerCase()) ||
     c.control.title.toLowerCase().includes(filter.toLowerCase())) &&
    (domainFilter === '' || c.control.domain === domainFilter)
  );

  const domains = Array.from(new Set(controls.map(c => c.control.domain))).sort();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div className="flex items-center gap-6">
          <div>
            <h3 className="text-lg font-bold text-gray-800">{framework} Control Explorer</h3>
            <p className="text-xs text-gray-500 uppercase tracking-widest">Browse, filter, and audit all {framework} practices</p>
          </div>
          <div className="h-8 w-px bg-gray-200"></div>
          <div>
              <label className="text-[10px] font-bold text-gray-400 uppercase block mb-0.5">Framework</label>
              <select
                  value={framework}
                  onChange={(e) => setFramework(e.target.value)}
                  className="bg-white border border-gray-300 rounded-md px-2 py-1 text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500"
              >
                  <option value="CMMC">CMMC 2.0</option>
                  <option value="NIST">NIST 800-171</option>
                  <option value="HIPAA">HIPAA Security</option>
                  <option value="FHIR">FHIR Privacy</option>
              </select>
          </div>
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
              <tr key={c.control.id} onClick={() => setSelectedControl(c)} className="hover:bg-gray-50 transition cursor-pointer">
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

      {selectedControl && (
        <div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm flex items-center justify-center p-8 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-gray-100 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-black text-gray-900">{selectedControl.control.id}</h2>
                <h3 className="text-lg font-bold text-gray-600">{selectedControl.control.title}</h3>
              </div>
              <button onClick={() => setSelectedControl(null)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-6">
              <div>
                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Description</h4>
                <p className="text-gray-700 leading-relaxed">{selectedControl.control.description}</p>
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Implementation Status</h4>
                  <span className={`px-3 py-1 rounded-full text-xs font-black uppercase ${
                    selectedControl.implementation_status === 'implemented' ? 'bg-green-100 text-green-700' :
                    selectedControl.implementation_status === 'partially_implemented' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {selectedControl.implementation_status.replace('_', ' ')}
                  </span>
                </div>
                <div>
                  <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Confidence Score</h4>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 bg-gray-100 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${selectedControl.confidence * 100}%` }}></div>
                    </div>
                    <span className="text-sm font-black text-blue-600">{Math.round(selectedControl.confidence * 100)}%</span>
                  </div>
                </div>
              </div>
              {selectedControl.notes && (
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                  <h4 className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-2">Assessor Findings & Guidance</h4>
                  <div className="space-y-2">
                    {selectedControl.notes.split(' | ').map((note, i) => (
                      <p key={i} className="text-sm text-blue-900 leading-relaxed">
                        {note.includes(': ') ? (
                          <>
                            <span className="font-bold">{note.split(': ')[0]}:</span> {note.split(': ').slice(1).join(': ')}
                          </>
                        ) : note}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {mappings.length > 0 && (
                <div>
                  <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                    <svg className="w-3 h-3 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>
                    Cross-Framework Mappings
                  </h4>
                  <div className="space-y-2">
                    {mappings.map(m => (
                      <div key={m.id} className="flex items-center justify-between bg-blue-50/50 border border-blue-100 rounded-lg px-4 py-2">
                        <div>
                          <span className="text-[10px] font-black text-blue-600 mr-2">{m.framework}</span>
                          <span className="text-xs font-bold text-gray-700">{m.id}</span>
                          <p className="text-[10px] text-gray-500 truncate w-48">{m.title}</p>
                        </div>
                        <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded ${
                          m.status === 'implemented' ? 'bg-green-100 text-green-700' :
                          m.status === 'partially_implemented' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-200 text-gray-500'
                        }`}>
                          {m.status.replace('_', ' ')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center text-[10px] font-bold">
                  <span className="text-gray-400 uppercase tracking-widest">Assessor</span>
                  <span className="text-gray-900">{selectedControl.assessor || 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-bold">
                  <span className="text-gray-400 uppercase tracking-widest">Assessment Date</span>
                  <span className="text-gray-900">{selectedControl.assessment_date ? new Date(selectedControl.assessment_date).toLocaleString() : 'N/A'}</span>
                </div>
                {selectedControl.fingerprint && (
                  <div className="pt-2 border-t border-gray-200">
                    <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest block mb-1">OML Fingerprint</span>
                    <code className="text-[9px] text-blue-600 break-all bg-blue-50 px-1 py-0.5 rounded leading-tight">
                      {selectedControl.fingerprint}
                    </code>
                  </div>
                )}
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
              {selectedControl.implementation_status !== 'implemented' ? (
                <button
                  onClick={generateRemediation}
                  disabled={isGeneratingScript}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-black uppercase shadow-lg shadow-blue-200 hover:bg-blue-700 transition flex items-center gap-2"
                >
                  {isGeneratingScript ? 'Generating...' : 'AI Remediation Script'}
                </button>
              ) : <div />}
              <button onClick={() => setSelectedControl(null)} className="px-6 py-2 bg-gray-900 text-white rounded-lg font-bold text-sm hover:bg-gray-800 transition shadow-lg shadow-gray-200">
                Close
              </button>
            </div>

            {remediationScript && (
              <div className="p-6 bg-slate-900 text-blue-400 font-mono text-xs overflow-x-auto max-h-48 border-t border-slate-800">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[10px] font-black text-slate-500 uppercase">AI-Generated Remediation Code</span>
                  <button onClick={() => setRemediationScript(null)} className="text-slate-500 hover:text-white">✕</button>
                </div>
                <pre>{remediationScript}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ControlExplorer;
