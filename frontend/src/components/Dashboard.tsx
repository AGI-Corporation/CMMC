
import React, { useEffect, useState } from 'react';
import AgentFleet from './AgentFleet';
import ProvenanceDetail from './ProvenanceDetail';
import ComplianceAdvisor from './ComplianceAdvisor';
import ControlExplorer from './ControlExplorer';

export interface DashboardSummary {
  total_controls: number;
  implemented: number;
  not_implemented: number;
  partially_implemented: number;
  not_started: number;
  compliance_percentage: number;
  sprs_score: number;
  by_domain: Record<string, any>;
  by_level: Record<string, any>;
  readiness: string;
}

export interface ZTPillarScore {
  pillar: string;
  total_controls: number;
  implemented: number;
  partial: number;
  not_implemented: number;
  maturity_pct: number;
  confidence_avg: number;
}

const Dashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [ztScorecard, setZtScorecard] = useState<ZTPillarScore[]>([]);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRunningAssessment, setIsRunningAssessment] = useState(false);
  const [framework, setFramework] = useState('CMMC');

  const fetchData = async () => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const [sumRes, ztRes, reportRes] = await Promise.all([
        fetch(`${baseUrl}/api/assessment/dashboard?framework=${framework}`),
        fetch(`${baseUrl}/api/orchestrator/scorecard?framework=${framework}`),
        fetch(`${baseUrl}/api/orchestrator/report?framework=${framework}`)
      ]);
      const sumData = await sumRes.json();
      const ztData = await ztRes.json();
      const reportData = await reportRes.json();
      setSummary(sumData);
      setZtScorecard(ztData.scorecard);
      setRecentRuns(reportData.agent_runs || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAssessment = async () => {
    setIsRunningAssessment(true);
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/api/orchestrator/run?framework=${framework}`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchData(); // Refresh all data
      }
    } catch (error) {
      console.error('Error running assessment:', error);
    } finally {
      setIsRunningAssessment(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [framework]);

  if (loading) return <div className="p-8 text-center">Loading Compliance Dashboard...</div>;

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{framework} Compliance Dashboard</h1>
          <p className="text-gray-600">AI-Powered Compliance Automation with NANDA & OML</p>
        </div>
        <div className="flex gap-4 items-center">
            <div className="flex flex-col">
                <label className="text-[10px] font-bold text-gray-400 uppercase">Framework</label>
                <select
                    value={framework}
                    onChange={(e) => setFramework(e.target.value)}
                    className="bg-white border border-gray-300 rounded-lg px-3 py-2 font-bold text-gray-700 shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="CMMC">CMMC 2.0</option>
                    <option value="NIST">NIST 800-171</option>
                    <option value="HIPAA">HIPAA Security</option>
                    <option value="FHIR">FHIR Privacy</option>
                </select>
            </div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 text-center">
          <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">SPRS Score</span>
          <div className={`text-4xl font-black ${summary?.sprs_score && summary.sprs_score > 80 ? 'text-green-600' : 'text-red-600'}`}>
            {summary?.sprs_score}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <div className="lg:col-span-2 space-y-8">
          {/* Main Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Readiness</h3>
              <p className="text-xl font-semibold text-gray-800">{summary?.readiness}</p>
              <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${summary?.compliance_percentage}%` }}></div>
              </div>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex justify-around items-center">
              <div className="text-center">
                <span className="block text-2xl font-bold text-green-600">{summary?.implemented}</span>
                <span className="text-xs text-gray-400 uppercase">Impl</span>
              </div>
              <div className="text-center">
                <span className="block text-2xl font-bold text-yellow-600">{summary?.partially_implemented}</span>
                <span className="text-xs text-gray-400 uppercase">Partial</span>
              </div>
            </div>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Levels</h3>
              <div className="flex gap-2">
                {Object.keys(summary?.by_level || {}).map(lvl => (
                  <div key={lvl} className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded">
                    {lvl}: {summary?.by_level[lvl].implemented}/{summary?.by_level[lvl].total}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ZT Scorecard */}
          <div>
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">Zero Trust Maturity Index</h2>
                {ztScorecard.some(p => p.confidence_avg < 0.7) && (
                    <div className="bg-amber-50 border border-amber-200 text-amber-700 px-3 py-1 rounded-full text-[10px] font-black uppercase flex items-center gap-2 animate-pulse">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                        Low Confidence Signals Detected
                    </div>
                )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ztScorecard.map(pillar => (
                <div key={pillar.pillar} className={`bg-white p-4 rounded-lg shadow-sm border ${pillar.confidence_avg < 0.7 ? 'border-amber-200 bg-amber-50/20' : 'border-gray-200'}`}>
                  <div className="flex justify-between">
                    <h4 className="font-bold text-gray-700">{pillar.pillar}</h4>
                    <span className="text-xs text-gray-400 uppercase">Confidence: {Math.round(pillar.confidence_avg * 100)}%</span>
                  </div>
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex-1 bg-gray-100 rounded-full h-2">
                      <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${pillar.maturity_pct}%` }}></div>
                    </div>
                    <span className="text-lg font-black text-blue-700">{pillar.maturity_pct}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-8">
          <ComplianceAdvisor />
          <AgentFleet />

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-800">Integrity Feed</h3>
              <p className="text-xs text-gray-500 uppercase tracking-widest">OML Cryptographic Provenance</p>
            </div>
            <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
              {recentRuns.map((run, idx) => (
                <div key={idx} className="border-l-2 border-blue-500 pl-4 py-1">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-bold text-gray-700">{run.agent.toUpperCase()} Execution</span>
                    <span className="text-[10px] text-gray-400">{new Date(run.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[10px] text-gray-500 mb-2 italic">{run.scope}</p>
                  <ProvenanceDetail
                    id={run.agent}
                    fingerprint={run.fingerprint}
                    timestamp={run.created_at}
                    agent={run.agent}
                  />
                </div>
              ))}
              {recentRuns.length === 0 && <p className="text-center text-gray-400 text-sm py-4">No recent agent activity recorded.</p>}
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleRunAssessment}
          disabled={isRunningAssessment}
          className={`${isRunningAssessment ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'} text-white px-8 py-3 rounded-lg font-bold shadow-lg transition transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2`}
        >
          {isRunningAssessment ? (
            <>
              <svg className="animate-spin h-5 w-5 mr-3 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Running...
            </>
          ) : 'Trigger Full Assessment'}
        </button>
        <button onClick={fetchData} className="bg-white text-gray-700 border border-gray-300 px-8 py-3 rounded-lg font-bold hover:bg-gray-50 transition transform hover:-translate-y-0.5">
          Refresh Dashboard
        </button>
        <button onClick={() => window.open(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/reports/ssp`, '_blank')} className="bg-white text-blue-600 border-2 border-blue-600 px-8 py-3 rounded-lg font-bold hover:bg-blue-50 transition transform hover:-translate-y-0.5 ml-auto">
          Generate SSP Report
        </button>
      </div>

    </div>
  );
};

export default Dashboard;
