import type { SquadInfo, SquadState } from "@/types/state";
import { StatusBadge } from "./StatusBadge";
import { ChevronRight } from "lucide-react";

interface SquadCardProps {
  squad: SquadInfo;
  state: SquadState | undefined;
  isSelected: boolean;
  onSelect: () => void;
}

export function SquadCard({ squad, state, isSelected, onSelect }: SquadCardProps) {
  const isActive = !!state;
  const status = state?.status ?? "inactive";

  return (
    <button
      onClick={onSelect}
      className={`group relative flex items-center gap-3 w-full p-3 rounded-lg border text-left transition-all duration-300 ${
        isSelected
          ? "bg-white/10 border-white/20 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
          : "bg-surface/30 border-transparent hover:bg-white/5 hover:border-white/10"
      }`}
    >
      {/* Selection indicator line */}
      <div 
        className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 rounded-r-md transition-all duration-300 ${
          isSelected ? "h-8 bg-secondary shadow-[0_0_8px_rgba(0,240,255,0.8)]" : "h-0 bg-transparent"
        }`}
      />

      <div className="flex-shrink-0 z-10">
        <StatusBadge status={status} />
      </div>

      <div className="flex-1 min-w-0 flex flex-col z-10">
        <div className="flex items-center gap-2">
          <span>{squad.icon}</span>
          <span className={`truncate text-sm font-semibold tracking-wide ${isActive || isSelected ? "text-gray-100" : "text-gray-400"}`}>
            {squad.name}
          </span>
        </div>
        
        {state?.step && (
          <div className="flex items-center mt-1">
            <div className="h-1 flex-1 bg-black/50 rounded-full overflow-hidden">
               <div 
                  className="h-full bg-gradient-to-r from-secondary to-primary transition-all duration-500 rounded-full"
                  style={{ width: `${(state.step.current / state.step.total) * 100}%` }}
               />
            </div>
            <span className="text-[10px] text-gray-500 ml-2 font-mono">
              {state.step.current}/{state.step.total}
            </span>
          </div>
        )}
      </div>

      <ChevronRight 
        size={16} 
        className={`flex-shrink-0 transition-transform duration-300 ${
          isSelected ? "text-secondary translate-x-0 opacity-100" : "text-gray-600 -translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0"
        }`} 
      />
    </button>
  );
}
