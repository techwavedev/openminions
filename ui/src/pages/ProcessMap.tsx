import { useCallback, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useSquadStore } from '@/store/useSquadStore';
import { Map as MapIcon } from 'lucide-react';

export function ProcessMap() {
  const { squads, activeStates, selectedSquad } = useSquadStore();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!selectedSquad) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const info = squads.get(selectedSquad);
    const state = activeStates.get(selectedSquad);
    
    let currentAgents = state?.agents || [];
    
    // Fallback if no active state yet.
    const agentList = currentAgents.length > 0 
      ? currentAgents 
      : info?.agents.map((agentPath, i) => ({
          id: `fake-${i}`,
          name: agentPath.split('/').pop()?.replace('.yaml', '') || 'Agent',
          icon: '🤖',
          status: 'idle'
        })) || [];

    const newNodes = agentList.map((agent, index) => ({
      id: agent.id,
      position: { x: index * 280, y: 150 }, // Simple horizontal layout
      data: { 
        label: (
          <div className="flex flex-col items-center justify-center p-4 min-w-[180px] rounded-xl bg-[#0f1219]/80 backdrop-blur-md border border-white/10 shadow-[auto]">
            <span className="text-4xl mb-3 drop-shadow-lg">{agent.icon || '🤖'}</span>
            <span className="font-bold text-white text-md tracking-wider uppercase">{agent.name}</span>
            {agent.status && (
                <span className={`text-xs mt-3 px-3 py-1 rounded-full uppercase tracking-widest font-bold ${
                  agent.status === 'working' ? 'bg-[#ff003c]/20 text-[#ff003c]' :
                  agent.status === 'done' ? 'bg-emerald-500/20 text-emerald-400' :
                  'bg-white/5 text-gray-500'
                }`}>
                  {agent.status}
                </span>
            )}
          </div>
        )
      },
      style: {
        background: 'transparent',
        border: 'none',
        padding: 0,
        boxShadow: agent.status === 'working' ? '0 0 25px rgba(255,0,60,0.4)' : 'none',
        borderRadius: '0.75rem',
      }
    }));

    const newEdges = [];
    for (let i = 0; i < newNodes.length - 1; i++) {
        // Find if the left agent is done or working to animate the edge
        const prevAgent = agentList[i];
        const isAnimated = prevAgent.status === 'working' || prevAgent.status === 'done';
        
        newEdges.push({
            id: `e-${newNodes[i].id}-${newNodes[i+1].id}`,
            source: newNodes[i].id,
            target: newNodes[i+1].id,
            animated: isAnimated,
            style: { 
                stroke: isAnimated ? '#ff003c' : '#333333', 
                strokeWidth: 2,
                opacity: 0.8
            },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                color: isAnimated ? '#ff003c' : '#333333',
            },
        });
    }

    setNodes(newNodes);
    setEdges(newEdges);
  }, [selectedSquad, squads, activeStates, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: any) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  if (!selectedSquad) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 h-full">
        <MapIcon size={48} className="mb-4 opacity-50" />
        <h3 className="text-xl font-bold tracking-widest text-gray-400">NO SQUAD SELECTED</h3>
        <p className="mt-2 text-sm">Select a squad from the left panel to view its process map</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full fade-in relative">
        <div className="absolute top-6 left-6 z-10 pointer-events-none">
            <h2 className="text-xl font-black text-white flex items-center gap-3 tracking-widest uppercase">
                <span className="text-[#ff003c]">PROCESS MAP</span>
                <span className="text-white/20">|</span>
                <span className="opacity-90">{squads.get(selectedSquad)?.name || selectedSquad}</span>
            </h2>
            <p className="text-xs text-gray-400 mt-2 tracking-widest uppercase ml-1">Live Pipeline Visualization</p>
        </div>
        
        <div className="w-full h-full rounded-2xl overflow-hidden shadow-2xl relative bg-zinc-950/40">
           <ReactFlow
               nodes={nodes}
               edges={edges}
               onNodesChange={onNodesChange}
               onEdgesChange={onEdgesChange}
               onConnect={onConnect}
               fitView
               fitViewOptions={{ padding: 0.5 }}
               className="bg-transparent"
           >
               <Background color="#ffffff" gap={24} style={{ opacity: 0.03 }} />
           </ReactFlow>
        </div>
    </div>
  );
}
