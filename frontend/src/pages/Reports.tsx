import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { FileText, Download } from 'lucide-react';

export default function Reports() {
  const { data: sprs } = useQuery({
    queryKey: ['sprs'],
    queryFn: api.getSPRS,
  });

  const handleDownload = async (type: 'ssp' | 'poam') => {
    const res = await fetch(`/api/reports/${type}`);
    const text = await res.text();
    const blob = new Blob([text], { type: type === 'poam' ? 'text/csv' : 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cmmc_${type}_${new Date().toISOString().split('T')[0]}.${type === 'poam' ? 'csv' : 'md'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-white">Reports & Export</h1>

      {sprs && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-sm space-y-3">
          <div className="text-gray-300 font-semibold">Current SPRS Summary</div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div><div className="text-gray-500">Organization</div><div className="text-gray-200">{sprs.organization}</div></div>
            <div><div className="text-gray-500">System Name</div><div className="text-gray-200">{sprs.system_name}</div></div>
            <div><div className="text-gray-500">SPRS Score</div><div className="text-gray-200 font-bold text-lg">{sprs.sprs_score} / 110</div></div>
            <div><div className="text-gray-500">Certification Level</div><div className="text-gray-200">{sprs.certification_level}</div></div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <span className="font-semibold text-gray-200">System Security Plan</span>
          </div>
          <p className="text-xs text-gray-400">
            NIST OSCAL-aligned SSP in Markdown format. Covers all 14 CMMC domains with current implementation status.
          </p>
          <button
            onClick={() => handleDownload('ssp')}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-blue-800 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            Download SSP (.md)
          </button>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-amber-400" />
            <span className="font-semibold text-gray-200">Plan of Action & Milestones</span>
          </div>
          <p className="text-xs text-gray-400">
            DoD-format POAM listing all controls that require remediation, with deductions and priority.
          </p>
          <button
            onClick={() => handleDownload('poam')}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-amber-800 hover:bg-amber-700 text-white text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            Download POAM (.csv)
          </button>
        </div>
      </div>
    </div>
  );
}
