import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { ControlResponse } from '../types/api';
import { AlertTriangle, Clock, CheckCircle2, XCircle, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  implemented: { label: 'Implemented', color: 'text-emerald-400 bg-emerald-900/30', icon: CheckCircle2 },
  partially_implemented: { label: 'Partial', color: 'text-amber-400 bg-amber-900/30', icon: AlertTriangle },
  partial: { label: 'Partial', color: 'text-amber-400 bg-amber-900/30', icon: AlertTriangle },
  planned: { label: 'Planned', color: 'text-blue-400 bg-blue-900/30', icon: Clock },
  not_implemented: { label: 'Not Implemented', color: 'text-red-400 bg-red-900/30', icon: XCircle },
  not_started: { label: 'Not Started', color: 'text-gray-400 bg-gray-800', icon: XCircle },
  not_applicable: { label: 'N/A', color: 'text-gray-500 bg-gray-800', icon: CheckCircle2 },
};

const DOMAINS = ['AC', 'AU', 'CM', 'IA', 'IR', 'MA', 'MP', 'PS', 'PE', 'RA', 'CA', 'SA', 'SC', 'SI'];
const LEVELS = ['Level 1', 'Level 2', 'Level 3'];
const STATUSES = ['implemented', 'partially_implemented', 'planned', 'not_implemented', 'not_started'];

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG['not_started'];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function ControlRow({ cr }: { cr: ControlResponse }) {
  const c = cr.control;
  return (
    <Link
      to={`/controls/${c.id}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-gray-800/60 transition-colors border-b border-gray-800/60 last:border-0"
    >
      <code className="text-xs font-mono text-violet-400 w-20 shrink-0">{c.id}</code>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-gray-200 truncate">{c.title}</div>
        <div className="text-xs text-gray-500 mt-0.5 flex gap-2">
          <span>{c.domain}</span>
          <span>•</span>
          <span>{c.level}</span>
          {cr.evidence_count > 0 && <span>• {cr.evidence_count} evidence</span>}
          {cr.confidence > 0 && <span>• {Math.round(cr.confidence * 100)}% confidence</span>}
        </div>
      </div>
      <StatusBadge status={cr.implementation_status ?? 'not_started'} />
      <ChevronRight className="w-4 h-4 text-gray-600 shrink-0" />
    </Link>
  );
}

export default function ControlsGrid() {
  const [domain, setDomain] = useState('');
  const [level, setLevel] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['controls', domain, level, status],
    queryFn: () => api.getControls({ domain: domain || undefined, level: level || undefined, status: status || undefined }),
  });

  const controls = (data?.controls ?? []).filter(cr => {
    if (!search) return true;
    const q = search.toLowerCase();
    return cr.control.id.toLowerCase().includes(q) || cr.control.title.toLowerCase().includes(q);
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">CMMC Controls</h1>
        <span className="text-sm text-gray-400">{controls.length} controls</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search controls…"
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-violet-600 w-48"
        />
        <select
          value={domain}
          onChange={e => setDomain(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-violet-600"
        >
          <option value="">All Domains</option>
          {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          value={level}
          onChange={e => setLevel(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-violet-600"
        >
          <option value="">All Levels</option>
          {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
        <select
          value={status}
          onChange={e => setStatus(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-violet-600"
        >
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{STATUS_CONFIG[s]?.label ?? s}</option>)}
        </select>
      </div>

      {/* Controls list */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-gray-500">Loading controls…</div>
        ) : controls.length === 0 ? (
          <div className="py-16 text-center text-gray-500">No controls match your filters.</div>
        ) : (
          controls.map(cr => <ControlRow key={cr.control.id} cr={cr} />)
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2">
        {Object.entries(STATUS_CONFIG).slice(0, 5).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-gray-500">
            <cfg.icon className={`w-3 h-3 ${cfg.color.split(' ')[0]}`} />
            {cfg.label}
          </div>
        ))}
      </div>
    </div>
  );
}
