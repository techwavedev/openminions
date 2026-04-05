import { useEffect, useState } from "react";
import { useSquadStore } from "@/store/useSquadStore";
import { History, Database, ArrowRight, PlayCircle, Loader2 } from "lucide-react";

interface QdrantMemory {
  id: string;
  type: string;
  content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

export function SquadHistory() {
  const { selectedSquad, squads } = useSquadStore();
  const [history, setHistory] = useState<QdrantMemory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedSquad) {
      setHistory([]);
      return;
    }

    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/history/${selectedSquad}`);
        if (!res.ok) throw new Error("Failed to fetch history");
        
        const data = await res.json();
        // memory_manager.py might return {"context_chunks": [...]} or full objects
        if (data.results) {
          setHistory(data.results);
        } else if (data.context_chunks) {
            // mock objects from strings
            setHistory(data.context_chunks.map((c: string, i: number) => ({
                id: `chunk-${i}`,
                type: 'decision',
                content: c,
                created_at: new Date().toISOString()
            })));
        } else if (Array.isArray(data)) {
            setHistory(data);
        } else {
            setHistory([]);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [selectedSquad]);

  if (!selectedSquad) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 h-full">
        <History size={48} className="mb-4 opacity-50" />
        <h3 className="text-xl font-bold tracking-widest text-gray-400">NO SQUAD SELECTED</h3>
        <p className="mt-2 text-sm">Select a squad to view its Qdrant memory history</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-4 fade-in">
        <div className="w-full h-full rounded-xl overflow-hidden glass-panel border border-white/10 relative flex flex-col">
            <div className="p-4 border-b border-white/5 bg-black/20 shrink-0">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Database className="text-primary" size={20} />
                    <span className="text-primary tracking-wider uppercase">QDRANT MEMORY:</span> 
                    {squads.get(selectedSquad)?.name || selectedSquad}
                </h2>
                <p className="text-xs text-gray-400 mt-1">Past executions, decisions, and deliverables</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {loading ? (
                    <div className="flex items-center justify-center h-40">
                        <Loader2 className="animate-spin text-primary opacity-50" size={32} />
                    </div>
                ) : error ? (
                    <div className="text-primary/80 bg-primary/10 p-4 rounded-lg flex gap-3 text-sm">
                        <ArrowRight className="shrink-0" />
                        <p>{error} (Is agi-agent-kit running / Qdrant ready?)</p>
                    </div>
                ) : history.length === 0 ? (
                    <div className="flex flex-col items-center justify-center text-gray-500 h-full p-10">
                        <Database size={32} className="mb-3 opacity-30" />
                        <p>No historical runs found in Qdrant for this squad.</p>
                        <p className="text-xs mt-2 opacity-50">Once the pipeline completes, it will be stored here.</p>
                    </div>
                ) : (
                    history.map((mem, i) => (
                        <div key={mem.id || i} className="bg-surface/50 border border-white/5 rounded-lg p-5 hover:border-white/10 transition-colors group">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex gap-2">
                                    <span className="bg-white/10 text-gray-300 text-xs px-2 py-0.5 rounded font-mono">
                                        RUN #{history.length - i}
                                    </span>
                                    <span className="bg-primary/20 text-primary text-xs px-2 py-0.5 rounded font-mono uppercase tracking-widest">
                                        DELIVERABLE
                                    </span>
                                </div>
                                <button className="text-xs flex items-center gap-1 text-gray-400 hover:text-white transition-colors">
                                    <PlayCircle size={14} /> Replay
                                </button>
                            </div>
                            <div className="text-sm text-gray-300 whitespace-pre-wrap font-mono leading-relaxed bg-black/30 p-4 rounded border border-white/5">
                                {mem.content}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    </div>
  );
}
