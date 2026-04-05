import { useSquadStore } from "@/store/useSquadStore";
import { SquadCard } from "./SquadCard";
import { Users } from "lucide-react";

export function SquadSelector() {
  const squads = useSquadStore((s) => s.squads);
  const activeStates = useSquadStore((s) => s.activeStates);
  const selectedSquad = useSquadStore((s) => s.selectedSquad);
  const selectSquad = useSquadStore((s) => s.selectSquad);

  // Sort: active squads first, then alphabetical
  const squadList = Array.from(squads.values()).sort((a, b) => {
    const aActive = activeStates.has(a.code) ? 0 : 1;
    const bActive = activeStates.has(b.code) ? 0 : 1;
    if (aActive !== bActive) return aActive - bActive;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="flex flex-col h-full relative z-10 w-full">
      <div className="p-4 bg-surface/50 border-b border-white/5 backdrop-blur-sm flex items-center gap-2">
        <Users size={16} className="text-gray-400" />
        <h2 className="text-xs font-bold tracking-widest text-gray-400 uppercase">
          Active Squads
        </h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {squadList.length === 0 && (
          <div className="flex flex-col items-center justify-center h-40 text-center px-4">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-3">
              <Users size={20} className="text-gray-500" />
            </div>
            <p className="text-sm text-gray-500 font-medium">No squads deployed</p>
            <p className="text-xs text-gray-600 mt-1">Run \`openminions run --intent "..."\` to spawn a new squad.</p>
          </div>
        )}
        
        {squadList.map((squad) => (
          <SquadCard
            key={squad.code}
            squad={squad}
            state={activeStates.get(squad.code)}
            isSelected={selectedSquad === squad.code}
            onSelect={() => selectSquad(squad.code)}
          />
        ))}
      </div>
    </div>
  );
}
