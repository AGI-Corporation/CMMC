import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';

export default function PublicVerify() {
  const { data: status } = useQuery({
    queryKey: ['blockchain-status'],
    queryFn: api.getBlockchainStatus,
  });
  const { data: sprs } = useQuery({
    queryKey: ['sprs'],
    queryFn: api.getSPRS,
  });
  const { data: sprsHistory } = useQuery({
    queryKey: ['sprs-history'],
    queryFn: api.getSPRSHistory,
  });
  const { data: integrity } = useQuery({
    queryKey: ['integrity'],
    queryFn: api.getLedgerIntegrity,
  });

  const latestAnchor = sprsHistory?.anchors?.[0];
  const certColor = (sprs?.sprs_score ?? 0) >= 88 ? 'emerald' : (sprs?.sprs_score ?? 0) >= 0 ? 'amber' : 'red';

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <div className="flex justify-center">
          <ShieldCheck className="w-16 h-16 text-violet-400" />
        </div>
        <h1 className="text-3xl font-bold text-white">cmmc.blockchain</h1>
        <p className="text-gray-400">
          Public CMMC 2.0 compliance verification powered by tamper-evident blockchain ledger
        </p>
        <p className="text-xs font-mono text-gray-600">{status?.chain_id}</p>
      </div>

      {/* Certification card */}
      {sprs && (
        <div className={`rounded-2xl border p-6 text-center space-y-3 bg-${certColor}-900/10 border-${certColor}-800`}>
          <div className="text-sm text-gray-400">AGI Corporation — CMMC Compliance Status</div>
          <div className={`text-5xl font-black text-${certColor}-400`}>{sprs.sprs_score}</div>
          <div className="text-gray-400 text-sm">SPRS Score (max 110)</div>
          <div className={`inline-block px-4 py-1.5 rounded-full text-sm font-semibold bg-${certColor}-900/30 text-${certColor}-300 border border-${certColor}-800`}>
            {sprs.certification_level}
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {sprs.controls_implemented} of {sprs.controls_assessed} controls implemented
          </div>
        </div>
      )}

      {/* Chain integrity */}
      {integrity && (
        <div className={`rounded-xl border p-5 flex items-start gap-4 ${
          integrity.chain_valid
            ? 'bg-emerald-900/10 border-emerald-800'
            : 'bg-red-900/10 border-red-800'
        }`}>
          {integrity.chain_valid
            ? <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
            : <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />}
          <div>
            <div className={`font-semibold ${integrity.chain_valid ? 'text-emerald-300' : 'text-red-300'}`}>
              {integrity.chain_valid ? 'Ledger Integrity: VERIFIED' : 'Ledger Integrity: ISSUES DETECTED'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {integrity.blocks_checked} blocks checked • {integrity.issues_found} issues found
            </div>
            {!integrity.chain_valid && integrity.issues.map((issue, i) => (
              <div key={i} className="text-xs text-red-400 mt-1">• {issue}</div>
            ))}
          </div>
        </div>
      )}

      {/* Latest SPRS anchor */}
      {latestAnchor && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="text-sm font-semibold text-gray-300">Latest On-Chain SPRS Anchor</div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              { label: 'Block Height', value: `#${latestAnchor.block_height}` },
              { label: 'SPRS Score', value: latestAnchor.sprs_score },
              { label: 'Timestamp', value: new Date(latestAnchor.timestamp).toLocaleString() },
              { label: 'Controls Implemented', value: `${latestAnchor.implemented} / ${latestAnchor.total_controls}` },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-gray-500">{label}</div>
                <div className="text-gray-200 font-mono mt-0.5">{String(value)}</div>
              </div>
            ))}
            <div className="col-span-2">
              <div className="text-gray-500">Payload Hash (SHA-256)</div>
              <code className="text-gray-400 break-all mt-0.5 text-xs">{latestAnchor.payload_hash}</code>
            </div>
            <div className="col-span-2">
              <div className="text-gray-500">Transaction ID</div>
              <code className="text-gray-400 break-all mt-0.5 text-xs">{latestAnchor.tx_id}</code>
            </div>
          </div>
        </div>
      )}

      {/* About */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-sm text-gray-400 space-y-2">
        <div className="font-semibold text-gray-300">About cmmc.blockchain</div>
        <p>
          This page provides public, verifiable proof of CMMC 2.0 compliance status.
          All compliance events are cryptographically anchored using SHA-256 Merkle chaining —
          each transaction includes the hash of the previous record, making tampering detectable.
        </p>
        <p>
          No CUI (Controlled Unclassified Information) is stored on-chain.
          Only compliance status, confidence scores, and SHA-256 evidence hashes are recorded.
        </p>
        <p className="text-xs text-gray-600">
          Powered by the CMMC Compliance Platform • AGI Corporation 2026 • MIT License
        </p>
      </div>
    </div>
  );
}
