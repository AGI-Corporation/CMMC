import { Link, useLocation } from 'react-router-dom';
import { ShieldCheck, Link2, BarChart3, FileSearch, List, BookOpen } from 'lucide-react';

const nav = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/controls', label: 'Controls', icon: List },
  { to: '/chain', label: 'Blockchain Explorer', icon: Link2 },
  { to: '/attest', label: 'Attestation', icon: ShieldCheck },
  { to: '/reports', label: 'Reports', icon: BookOpen },
  { to: '/verify', label: 'Public Verify', icon: FileSearch },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top bar */}
      <header className="border-b border-violet-900/40 bg-gray-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-violet-400 hover:text-violet-300">
            <ShieldCheck className="w-6 h-6" />
            <span>cmmc<span className="text-violet-300">.blockchain</span></span>
          </Link>
          <nav className="hidden md:flex items-center gap-1">
            {nav.map(({ to, label, icon: Icon }) => {
              const active = pathname === to || (to !== '/' && pathname.startsWith(to));
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                    active
                      ? 'bg-violet-700/30 text-violet-300'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
          <span className="text-xs text-gray-500 font-mono">AGI Corporation • 2026</span>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {children}
      </main>

      <footer className="border-t border-gray-800 text-center py-4 text-xs text-gray-600">
        cmmc.blockchain — Tamper-evident CMMC 2.0 compliance powered by SHA-256 Merkle ledger • AGI Corporation 2026
      </footer>
    </div>
  );
}
