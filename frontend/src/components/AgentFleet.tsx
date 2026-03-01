
import React, { useEffect, useState } from 'react';

interface AgentFacts {
  agent_id: string;
  name: string;
  version: string;
  trust_level: string;
  capabilities: string[];
  endpoint: string;
  last_verified: string;
}

const AgentFleet: React.FC = () => {
  const [agents, setAgents] = useState<AgentFacts[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${baseUrl}/api/nanda/`)
      .then(res => res.json())
      .then(data => {
        setAgents(data.agents);
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  if (loading) return <div>Loading Agent Fleet...</div>;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-bold text-gray-800">NANDA Agent Fleet</h3>
        <p className="text-xs text-gray-500 uppercase tracking-widest">Verified Decentralized Registry</p>
      </div>
      <div className="divide-y divide-gray-100">
        {agents.map(agent => (
          <div key={agent.agent_id} className="px-6 py-4 hover:bg-blue-50 transition flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-gray-900">{agent.name}</span>
                <span className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">v{agent.version}</span>
              </div>
              <div className="flex gap-1 mt-1">
                {agent.capabilities.slice(0, 2).map(cap => (
                  <span key={cap} className="text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full border border-blue-100">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <span className={`text-xs font-bold uppercase px-2 py-1 rounded ${
                agent.trust_level === 'verified' ? 'text-green-700 bg-green-50' : 'text-blue-700 bg-blue-50'
              }`}>
                {agent.trust_level}
              </span>
              <p className="text-[9px] text-gray-400 mt-1">Ref: {agent.agent_id}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentFleet;
