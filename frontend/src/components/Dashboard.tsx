
import React, { useEffect, useState } from 'react';

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
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [sumRes, ztRes] = await Promise.all([
        fetch('http://localhost:8000/api/assessment/dashboard'),
        fetch('http://localhost:8000/api/orchestrator/scorecard')
      ]);
      const sumData = await sumRes.json();
      const ztData = await ztRes.json();
      setSummary(sumData);
      setZtScorecard(ztData.scorecard);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) return <div className="p-8 text-center">Loading Compliance Dashboard...</div>;

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">CMMC Compliance Dashboard</h1>
          <p className="text-gray-600">AI-Powered Compliance Automation</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 text-center">
          <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">SPRS Score</span>
          <div className={`text-4xl font-black ${summary?.sprs_score && summary.sprs_score > 80 ? 'text-green-600' : 'text-red-600'}`}>
            {summary?.sprs_score}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Readiness Status</h3>
          <p className="text-xl font-semibold text-gray-800">{summary?.readiness}</p>
          <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${summary?.compliance_percentage}%` }}></div>
          </div>
          <p className="text-right text-xs mt-1 text-gray-500">{summary?.compliance_percentage}% Complete</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex justify-around items-center">
          <div className="text-center">
            <span className="block text-2xl font-bold text-green-600">{summary?.implemented}</span>
            <span className="text-xs text-gray-400 uppercase">Implemented</span>
          </div>
          <div className="text-center">
            <span className="block text-2xl font-bold text-yellow-600">{summary?.partially_implemented}</span>
            <span className="text-xs text-gray-400 uppercase">Partial</span>
          </div>
          <div className="text-center">
            <span className="block text-2xl font-bold text-red-600">{summary?.not_implemented}</span>
            <span className="text-xs text-gray-400 uppercase">Remaining</span>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
           <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Controls Filter</h3>
           <div className="flex gap-2">
              {Object.keys(summary?.by_level || {}).map(lvl => (
                <div key={lvl} className="text-xs bg-gray-100 px-2 py-1 rounded">
                  {lvl}: {summary?.by_level[lvl].implemented}/{summary?.by_level[lvl].total}
                </div>
              ))}
           </div>
        </div>
      </div>

      <h2 className="text-2xl font-bold text-gray-800 mb-4">Zero Trust Maturity</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {ztScorecard.map(pillar => (
          <div key={pillar.pillar} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <h4 className="font-bold text-gray-700">{pillar.pillar}</h4>
            <div className="flex justify-between items-end mt-2">
              <span className="text-2xl font-black text-blue-700">{pillar.maturity_pct}%</span>
              <span className="text-xs text-gray-400">Conf: {Math.round(pillar.confidence_avg * 100)}%</span>
            </div>
            <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
               <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pillar.maturity_pct}%` }}></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-12 flex gap-4">
        <button
          onClick={fetchData}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg font-bold shadow-md hover:bg-blue-700 transition"
        >
          Refresh Data
        </button>
        <button
          className="bg-white text-blue-600 border border-blue-600 px-6 py-2 rounded-lg font-bold hover:bg-blue-50 transition"
          onClick={() => window.open('http://localhost:8000/api/reports/ssp', '_blank')}
        >
          View SSP Report
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
