import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line,
} from 'recharts';
import { ShieldCheck, TrendingUp, AlertTriangle, Link2, Lock, CheckCircle2 } from 'lucide-react';

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex gap-4 items-start">
      <div className={`p-2.5 rounded-lg ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-gray-400">{label}</div>
        {sub && <div className="text-xs text-gray-600 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: dash, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
  });
  const { data: chain } = useQuery({
    queryKey: ['blockchain-status'],
    queryFn: api.getBlockchainStatus,
    refetchInterval: 15000,
  });
  const { data: sprsHistory } = useQuery({
    queryKey: ['sprs-history'],
    queryFn: api.getSPRSHistory,
  });

  if (dashLoading) {
    return <div className="flex justify-center items-center h-64 text-gray-500">Loading compliance data…</div>;
  }

  const domainData = dash
    ? Object.entries(dash.by_domain).map(([domain, d]) => ({
        domain,
        pct: d.total > 0 ? Math.round((d.implemented / d.total) * 100) : 0,
      }))
    : [];

  const radarData = domainData.map(d => ({ subject: d.domain, value: d.pct, fullMark: 100 }));

  const sprsData = sprsHistory?.anchors
    .slice(0, 10)
    .reverse()
    .map((a, i) => ({ name: `#${i + 1}`, score: a.sprs_score })) ?? [];

  const sprsColor =
    (dash?.sprs_score ?? 0) >= 88 ? '#22c55e' : (dash?.sprs_score ?? 0) >= 0 ? '#f59e0b' : '#ef4444';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">CMMC Compliance Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">cmmc.blockchain — tamper-evident compliance ledger</p>
        </div>
        {chain && (
          <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-900/20 border border-emerald-800 rounded-lg px-3 py-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Block #{chain.latest_block_height} • {chain.total_transactions} TXs
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="SPRS Score"
          value={dash?.sprs_score ?? '—'}
          sub="Max: 110"
          icon={TrendingUp}
          color="bg-violet-700"
        />
        <StatCard
          label="Controls Implemented"
          value={`${dash?.implemented ?? 0} / ${dash?.total_controls ?? 0}`}
          sub={`${dash?.compliance_percentage ?? 0}%`}
          icon={CheckCircle2}
          color="bg-emerald-700"
        />
        <StatCard
          label="Gaps (POA&M)"
          value={(dash?.not_implemented ?? 0) + (dash?.not_started ?? 0)}
          sub="Remediation required"
          icon={AlertTriangle}
          color="bg-amber-700"
        />
        <StatCard
          label="On-Chain TXs"
          value={chain?.total_transactions ?? '—'}
          sub={chain?.ledger_mode ?? 'local'}
          icon={Link2}
          color="bg-blue-700"
        />
      </div>

      {/* Readiness banner */}
      {dash && (
        <div className={`rounded-xl px-5 py-4 border flex items-center gap-3 ${
          dash.compliance_percentage >= 100
            ? 'bg-emerald-900/20 border-emerald-700 text-emerald-300'
            : dash.compliance_percentage >= 80
            ? 'bg-amber-900/20 border-amber-700 text-amber-300'
            : 'bg-red-900/20 border-red-800 text-red-300'
        }`}>
          <ShieldCheck className="w-5 h-5 shrink-0" />
          <span className="font-medium">{dash.readiness}</span>
          <span className="text-sm opacity-70 ml-auto">
            SPRS Score: <span style={{ color: sprsColor }} className="font-bold">{dash.sprs_score}</span> / 110
          </span>
        </div>
      )}

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Domain radar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Compliance by Domain</h2>
          <ResponsiveContainer width="100%" height={250}>
            <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 9 }} />
              <Radar name="Implementation %" dataKey="value" stroke="#7c3aed" fill="#7c3aed" fillOpacity={0.35} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* SPRS trend */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">SPRS Score History (On-Chain)</h2>
          {sprsData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[250px] text-gray-600 text-sm gap-2">
              <Lock className="w-8 h-8" />
              <span>No SPRS anchors yet — anchor your score on-chain</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={sprsData}>
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis domain={[-203, 110]} tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#e5e7eb' }} />
                <Line type="monotone" dataKey="score" stroke="#7c3aed" strokeWidth={2} dot={{ fill: '#7c3aed', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Domain bar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Implementation % by Domain</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={domainData} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="domain" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip
                formatter={(v) => [`${v}%`, 'Implemented']}
                contentStyle={{ background: '#111827', border: '1px solid #374151', color: '#e5e7eb' }}
              />
              <Bar dataKey="pct" fill="#7c3aed" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
