
import React, { useState } from 'react';
import { FileText, Download, Shield, FileCheck } from 'lucide-react';

const ReportCenter: React.FC = () => {
  const [framework, setFramework] = useState('CMMC');
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const handleDownloadSSP = () => {
    window.open(`${baseUrl}/api/reports/ssp?framework=${framework}`, '_blank');
  };

  const handleDownloadPOAM = () => {
    window.open(`${baseUrl}/api/reports/poam?framework=${framework}`, '_blank');
  };

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Report Center</h1>
        <p className="text-gray-600">Generate compliance documentation and audit-ready reports.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Configuration Card */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Shield className="text-blue-600" size={20} />
            Report Configuration
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-1">Target Framework</label>
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-2 font-medium text-gray-700 outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="CMMC">CMMC 2.0</option>
                <option value="NIST">NIST 800-171</option>
                <option value="HIPAA">HIPAA Security</option>
                <option value="FHIR">FHIR Privacy</option>
              </select>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-700">
                Reports are generated dynamically based on the latest verified assessment findings and evidence mappings for the selected framework.
              </p>
            </div>
          </div>
        </div>

        {/* Available Reports Card */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
            <FileCheck className="text-green-600" size={20} />
            Available Reports
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50 transition">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                  <FileText size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">System Security Plan (SSP)</h4>
                  <p className="text-xs text-gray-500">Comprehensive Markdown documentation</p>
                </div>
              </div>
              <button
                onClick={handleDownloadSSP}
                className="flex items-center gap-2 bg-white border border-gray-300 px-4 py-2 rounded-lg text-sm font-bold hover:bg-gray-50 transition"
              >
                <Download size={16} />
                Generate
              </button>
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50 transition">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 text-green-600 rounded-lg">
                  <FileText size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">Plan of Action & Milestones (POA&M)</h4>
                  <p className="text-xs text-gray-500">Remediation tracking in CSV format</p>
                </div>
              </div>
              <button
                onClick={handleDownloadPOAM}
                className="flex items-center gap-2 bg-white border border-gray-300 px-4 py-2 rounded-lg text-sm font-bold hover:bg-gray-50 transition"
              >
                <Download size={16} />
                Generate
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportCenter;
