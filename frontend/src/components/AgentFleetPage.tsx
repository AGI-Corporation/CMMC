
import React, { useEffect, useState } from 'react';
import { Users, Shield, Cpu, Activity, Search } from 'lucide-react';

interface AgentFacts {
  agent_id: string;
  name: string;
  version: string;
  trust_level: string;
  capabilities: string[];
  endpoint: string;
  last_verified: string;
}

const AgentFleetPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentFacts[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchAgents = async () => {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      try {
        const res = await fetch(`${baseUrl}/api/nanda/`);
        const data = await res.json();
        setAgents(data.agents || []);
      } catch (err) {
        console.error('Error fetching agents:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAgents();
  }, []);

  const filteredAgents = agents.filter(agent =>
    agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.agent_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.capabilities.some(cap => cap.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="p-8">
      <header className="mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agent Fleet</h1>
          <p className="text-gray-600">NANDA-registered AI agents with verified capabilities and cryptographic identity.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search agents or capabilities..."
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg w-80 outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-gray-200 animate-pulse">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
                <div className="flex-1 h-4 bg-gray-200 rounded"></div>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-gray-200 rounded w-full"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </div>
            </div>
          ))
        ) : filteredAgents.map(agent => (
          <div key={agent.agent_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:border-blue-400 transition group">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  {agent.name.toLowerCase().includes('mistral') ? <Cpu size={24} /> : <Users size={24} />}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{agent.name}</h3>
                  <p className="text-xs text-gray-400 font-mono">v{agent.version}</p>
                </div>
              </div>
              <span className={`text-[10px] font-black uppercase px-2 py-1 rounded-full ${
                agent.trust_level === 'verified' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {agent.trust_level}
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 block">Capabilities</span>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities.map(cap => (
                    <span key={cap} className="text-xs bg-gray-50 text-gray-600 px-2 py-1 rounded border border-gray-100">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2 text-gray-500">
                  <Activity size={14} />
                  <span className="text-[10px] font-medium">Ready</span>
                </div>
                <span className="text-[10px] font-mono text-gray-400">{agent.agent_id.substring(0, 8)}...</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentFleetPage;
