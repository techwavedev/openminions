import { useEffect, useState } from "react";
import { useSquadStore } from "@/store/useSquadStore";
import { formatElapsed } from "@/lib/formatTime";
import { Clock, CheckSquare } from "lucide-react";

export function StatusBar() {
  const selectedSquad = useSquadStore((s) => s.selectedSquad);
  const state = useSquadStore((s) =>
    s.selectedSquad ? s.activeStates.get(s.selectedSquad) : undefined
  );
  const isConnected = useSquadStore((s) => s.isConnected);

  // Elapsed timer
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!state?.startedAt) {
      setElapsed(0);
      return;
    }

    const startTime = new Date(state.startedAt).getTime();
    const tick = () => setElapsed(Date.now() - startTime);
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [state?.startedAt]);

  if (!selectedSquad || !state) {
    return (
      <footer className="flex items-center justify-between px-4 w-full h-full text-sm">
        <span className="text-gray-500 font-mono text-xs">
          IDLE: SELECT A SQUAD TO MONITOR
        </span>
        <ConnectionDot connected={isConnected} />
      </footer>
    );
  }

  return (
    <footer className="flex items-center justify-between px-4 w-full h-full text-sm">
      <div className="flex items-center gap-6 flex-1 min-w-0">
        
        {/* Step indicator */}
        <div className="flex items-center gap-2 text-gray-200 bg-white/5 px-3 py-1 rounded-full border border-white/10">
          <CheckSquare size={14} className="text-secondary" />
          <span className="font-mono text-xs">
            {state.step.current}/{state.step.total}
          </span>
          {state.step.label && (
            <>
              <div className="w-px h-3 bg-white/20"></div>
              <span className="text-xs truncate max-w-[200px]">{state.step.label}</span>
            </>
          )}
        </div>

        {/* Timer */}
        {state.startedAt && (
          <div className="flex items-center gap-1.5 text-gray-400 font-mono text-xs">
            <Clock size={13} />
            <span>{formatElapsed(elapsed)}</span>
          </div>
        )}

        {/* Handoff Message */}
        {state.handoff && (
          <div className="flex-1 overflow-hidden">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-primary font-bold">{state.handoff.from}</span>
              <span className="text-gray-600">→</span>
              <span className="text-secondary font-bold">{state.handoff.to}</span>
              <span className="text-gray-400 truncate flex-1 italic bg-white/5 px-2 py-0.5 rounded ml-2">
                "{state.handoff.message}"
              </span>
            </div>
          </div>
        )}
      </div>
      <ConnectionDot connected={isConnected} />
    </footer>
  );
}

function ConnectionDot({ connected }: { connected: boolean }) {
  return (
    <div className="flex items-center gap-2 ml-4 flex-shrink-0">
      <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">
        {connected ? "Live" : "Offline"}
      </span>
      <div className="relative flex h-2.5 w-2.5">
        {connected && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
        )}
        <span 
          className={`relative inline-flex rounded-full h-2.5 w-2.5 ${connected ? "bg-secondary" : "bg-red-500"}`}
        ></span>
      </div>
    </div>
  );
}
