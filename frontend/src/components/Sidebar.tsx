
import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldCheck,
  FileText,
  Archive,
  Users,
  Settings,
  HelpCircle,
  Activity
} from 'lucide-react';

const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { name: 'Controls', icon: ShieldCheck, path: '/controls' },
    { name: 'Evidence', icon: Archive, path: '/evidence' },
    { name: 'Reports', icon: FileText, path: '/reports' },
    { name: 'Agents', icon: Users, path: '/agents' },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white">
          <ShieldCheck size={24} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">SENTIENT</h1>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none">Compliance Platform</p>
        </div>
      </div>

      <nav className="flex-1 px-4 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <item.icon size={20} />
            {item.name}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 mt-auto border-t border-gray-100">
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Status</span>
          </div>
          <p className="text-sm font-bold text-gray-700">All Agents Online</p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
