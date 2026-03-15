
import React from 'react';

interface ProvenanceProps {
  id: string;
  fingerprint: string;
  timestamp: string;
  agent: string;
}

const ProvenanceDetail: React.FC<ProvenanceProps> = ({ id, fingerprint, timestamp, agent }) => {
  return (
    <div className="bg-slate-900 text-slate-300 p-4 rounded-lg font-mono text-[10px] border border-slate-700 shadow-inner">
      <div className="flex justify-between border-b border-slate-800 pb-2 mb-2">
        <span className="text-slate-500 uppercase">Provenance Attestation</span>
        <span className="text-blue-400">ID: {id}</span>
      </div>
      <div className="space-y-1">
        <div className="flex gap-2">
          <span className="text-slate-500 w-16 text-right">FINGERPRINT</span>
          <span className="text-green-400 break-all">{fingerprint}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-slate-500 w-16 text-right">TIMESTAMP</span>
          <span>{timestamp}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-slate-500 w-16 text-right">SOURCE</span>
          <span className="text-yellow-500">Sentient OML / Agent: {agent}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-slate-500 w-16 text-right">STATUS</span>
          <span className="bg-green-900 text-green-300 px-1">VERIFIED</span>
        </div>
      </div>
    </div>
  );
};

export default ProvenanceDetail;
