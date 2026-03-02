
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ControlExplorer from './components/ControlExplorer';
import EvidenceManager from './components/EvidenceManager';
import ReportCenter from './components/ReportCenter';
import AgentFleetPage from './components/AgentFleetPage';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex min-h-screen bg-gray-50">
    <Sidebar />
    <main className="flex-1 overflow-auto">
      {children}
    </main>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/controls" element={<div className="p-8"><ControlExplorer /></div>} />
          <Route path="/evidence" element={<EvidenceManager />} />
          <Route path="/reports" element={<ReportCenter />} />
          <Route path="/agents" element={<AgentFleetPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
