import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ControlsGrid from './pages/ControlsGrid';
import BlockchainExplorer from './pages/BlockchainExplorer';
import AttestationWizard from './pages/AttestationWizard';
import Reports from './pages/Reports';
import PublicVerify from './pages/PublicVerify';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/controls" element={<ControlsGrid />} />
            <Route path="/chain" element={<BlockchainExplorer />} />
            <Route path="/attest" element={<AttestationWizard />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/verify" element={<PublicVerify />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
