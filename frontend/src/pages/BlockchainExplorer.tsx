import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { BlockchainTx } from '../types/api';
import { Link2, ShieldCheck, TrendingUp, FileText, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';

const TX_TYPE_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  attestation: { label: 'Attestation', color: 'text-violet-400 bg-violet-900/30 border-violet-800', icon: ShieldCheck },
  sprs_anchor: { label: 'SPRS Anchor', color: 'text-blue-400 bg-blue-900/30 border-blue-800', icon: TrendingUp },
  evidence: { label: 'Evidence', color: 'text-emerald-400 bg-emerald-900/30 border-emerald-800', icon: FileText },
  assessment: { label: 'Assessment', color: 'text-amber-400 bg-amber-900/30 border-amber-800', icon: CheckCircle2 },
};

function TxTypeBadge({ type }: { type: string }) {
  const cfg = TX_TYPE_CONFIG[type] ?? { label: type, color: 'text-gray-400 bg-gray-800 border-gray-700', icon: Link2 };
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded border font-medium ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function TxRow({ tx }: { tx: BlockchainTx }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-b border-gray-800/60 last:border-0">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800/40 transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-600 font-mono w-10 shrink-0">#{tx.block_height}</span>
        <TxTypeBadge type={tx.tx_type} />
        <span className="font-mono text-xs text-gray-500 hidden sm:block">{tx.id.substring(0, 8)}…</span>
        {tx.control_id && (
          <code className="text-xs text-violet-400 bg-violet-900/20 px-1.5 py-0.5 rounded">{tx.control_id}</code>
        )}
        <span className="flex-1" />
        <span className="text-xs text-gray-500 shrink-0">{new Date(tx.created_at).toLocaleString()}</span>
        <span className="text-gray-600 ml-1">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <div>
              <div className="text-gray-500 mb-1">Transaction ID</div>
              <code className="text-gray-300 break-all">{tx.id}</code>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Payload Hash (SHA-256)</div>
              <code className="text-gray-300 break-all">{tx.payload_hash}</code>
            </div>
            {tx.previous_tx_hash && (
              <div className="sm:col-span-2">
                <div className="text-gray-500 mb-1">Previous Hash (Chain Link)</div>
                <code className="text-gray-300 break-all">{tx.previous_tx_hash}</code>
              </div>
            )}
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">Payload</div>
            <pre className="text-xs text-gray-400 bg-gray-950 rounded-lg p-3 overflow-x-auto border border-gray-800">
              {JSON.stringify(tx.payload, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BlockchainExplorer() {
  const [filter, setFilter] = useState('');
  const [limit, setLimit] = useState(25);

  const { data: status } = useQuery({
    queryKey: ['blockchain-status'],
    queryFn: api.getBlockchainStatus,
    refetchInterval: 10000,
  });
  const { data: audit, isLoading, refetch } = useQuery({
    queryKey: ['audit-trail', limit, filter],
    queryFn: () => api.getAuditTrail(limit, 0, filter || undefined),
    refetchInterval: 15000,
  });
  const { data: integrity } = useQuery({
    queryKey: ['integrity'],
    queryFn: api.getLedgerIntegrity,
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Blockchain Explorer</h1>
          <p className="text-gray-400 text-sm mt-1">Tamper-evident audit trail — every write is cryptographically chained</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 rounded-lg px-3 py-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Ledger stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Latest Block', value: status?.latest_block_height ?? '—' },
          { label: 'Total Transactions', value: status?.total_transactions ?? '—' },
          { label: 'Ledger Mode', value: status?.ledger_mode ?? '—' },
          { label: 'Chain ID', value: (status?.chain_id?.slice(0, 20) ?? '') + '…' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-lg font-bold text-white">{String(value)}</div>
            <div className="text-xs text-gray-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Integrity badge */}
      {integrity && (
        <div className={`flex items-center gap-3 rounded-xl px-4 py-3 border text-sm ${
          integrity.chain_valid
            ? 'bg-emerald-900/20 border-emerald-800 text-emerald-300'
            : 'bg-red-900/20 border-red-800 text-red-300'
        }`}>
          {integrity.chain_valid
            ? <CheckCircle2 className="w-5 h-5 shrink-0" />
            : <AlertTriangle className="w-5 h-5 shrink-0" />}
          <span>
            {integrity.chain_valid
              ? `Chain integrity verified — ${integrity.blocks_checked} blocks checked, all HMAC signatures valid`
              : `Chain integrity issues detected: ${integrity.issues_found} problem(s)`}
          </span>
        </div>
      )}

      {/* Filter + transaction list */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <span className="text-sm font-semibold text-gray-300">Transactions</span>
          <span className="text-xs text-gray-600">{audit?.total_transactions ?? 0} total</span>
          <div className="flex-1" />
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none"
          >
            <option value="">All types</option>
            {Object.keys(TX_TYPE_CONFIG).map(t => <option key={t} value={t}>{TX_TYPE_CONFIG[t].label}</option>)}
          </select>
          <select
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none"
          >
            {[25, 50, 100].map(n => <option key={n} value={n}>Show {n}</option>)}
          </select>
        </div>
        {isLoading ? (
          <div className="py-12 text-center text-gray-500">Loading ledger…</div>
        ) : !audit?.transactions?.length ? (
          <div className="py-12 text-center text-gray-600 text-sm">
            No transactions yet. Submit an attestation to start the blockchain ledger.
          </div>
        ) : (
          audit.transactions.map(tx => <TxRow key={tx.id} tx={tx} />)
        )}
      </div>
    </div>
  );
}
