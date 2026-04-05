import { useEffect, useState, useRef } from "react";
import { Terminal } from "lucide-react";
import { useSquadStore } from "@/store/useSquadStore";

export function LogsPanel() {
  const selectedSquad = useSquadStore((s) => s.selectedSquad);
  const [logs, setLogs] = useState<string>("Waiting for logs...");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!selectedSquad) return;

    let disposed = false;
    
    const fetchLogs = async () => {
      if (disposed) return;
      try {
        const res = await fetch(`/api/logs/${encodeURIComponent(selectedSquad)}`, { cache: "no-store" });
        if (res.ok) {
          const text = await res.text();
          setLogs(text);
          // scroll to bottom smoothly
          bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        }
      } catch (e) {
        // quiet fail on interval
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);

    return () => {
      disposed = true;
      clearInterval(interval);
    };
  }, [selectedSquad]);

  if (!selectedSquad) return null;

  return (
    <div className="absolute top-4 right-4 bottom-4 w-[calc(100%-2rem)] max-w-[400px] bg-[#050505]/90 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden flex flex-col shadow-2xl z-20">
      <div className="h-10 px-4 border-b border-white/5 flex items-center gap-2 bg-white/5">
        <Terminal size={14} className="text-secondary" />
        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Activity Log
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 font-mono text-[11px] leading-relaxed text-gray-300 scrollbar-thin scrollbar-thumb-white/10">
        <pre className="whitespace-pre-wrap">{logs}</pre>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
