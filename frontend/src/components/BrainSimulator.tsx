
import React, { useEffect, useState } from 'react';

interface SimNode {
  id: string;
  label: string;
  group: string;
  level: number;
  firing: boolean;
}

interface SimEdge {
  from: string;
  to: string;
  type: string;
}

const BrainSimulator: React.FC = () => {
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [edges, setEdges] = useState<SimEdge[]>([]);
  const [load, setLoad] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchSimulation = async () => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    try {
      const res = await fetch(`${baseUrl}/api/simulation/state`);
      const data = await res.json();
      setNodes(data.nodes);
      setEdges(data.edges);
      setLoad(data.brain_load);
    } catch (err) {
      console.error('Simulation fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulation();
    const interval = setInterval(fetchSimulation, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-4 text-center">Initializing Neural Core...</div>;

  return (
    <div className="bg-slate-900 rounded-xl shadow-2xl border border-blue-500/30 overflow-hidden text-white mb-8">
      <div className="bg-slate-800/50 px-6 py-3 border-b border-blue-500/20 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-black tracking-tighter text-blue-400">AGI NEURAL CORE</h3>
          <p className="text-[10px] text-blue-300/60 uppercase font-bold">Active Brain Simulation (OAGD Protocol)</p>
        </div>
        <div className="text-right">
          <span className="text-xs font-mono text-blue-400">LOAD: {load}%</span>
          <div className="w-24 h-1 bg-slate-700 rounded-full mt-1 overflow-hidden">
            <div
              className="h-full bg-blue-500 shadow-[0_0_8px_#3b82f6] transition-all duration-1000"
              style={{ width: `${load}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="p-6 relative h-[300px] flex items-center justify-center overflow-hidden">
        {/* Connection Lines (Simplified) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
          {edges.map((edge, i) => {
            const fromNode = nodes.find(n => n.id === edge.from);
            const toNode = nodes.find(n => n.id === edge.to);
            if (!fromNode || !toNode) return null;
            return (
              <line
                key={i}
                x1="50%" y1="50%" x2={Math.random()*100 + "%"} y2={Math.random()*100 + "%"}
                stroke="#3b82f6" strokeWidth="1"
              />
            );
          })}
        </svg>

        {/* Neurons (Nodes) */}
        <div className="grid grid-cols-5 gap-4 relative z-10">
          {nodes.map(node => (
            <div
              key={node.id}
              className={`flex flex-col items-center justify-center transition-all duration-500 transform ${node.firing ? 'scale-110' : 'scale-100'}`}
            >
              <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center mb-1 ${
                node.firing
                  ? 'bg-blue-500 border-blue-300 shadow-[0_0_15px_#3b82f6] animate-pulse'
                  : 'bg-slate-800 border-slate-700'
              }`}>
                <span className="text-[8px] font-bold">{node.label.substring(0,3)}</span>
              </div>
              <span className={`text-[8px] uppercase tracking-tighter ${node.firing ? 'text-blue-300' : 'text-slate-500'}`}>
                {node.id}
              </span>
            </div>
          ))}
        </div>

        {/* Activity Sparks */}
        <div className="absolute inset-0 pointer-events-none">
           {[...Array(5)].map((_, i) => (
             <div
               key={i}
               className="absolute w-1 h-1 bg-blue-400 rounded-full animate-ping"
               style={{
                 top: Math.random()*100 + '%',
                 left: Math.random()*100 + '%' ,
                 animationDelay: i*0.5 + 's'
               }}
             ></div>
           ))}
        </div>
      </div>

      <div className="bg-slate-800/30 px-6 py-2 border-t border-blue-500/10">
        <div className="flex justify-between items-center text-[10px] font-mono text-blue-400/50">
          <span>SYNAPTIC THROUGHPUT: {(load * 12.4).toFixed(1)} MTPS</span>
          <span>NEURAL MAPPING: ACTIVE</span>
        </div>
      </div>
    </div>
  );
};

export default BrainSimulator;
