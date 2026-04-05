import { useState } from "react";
import { useSquadSocket } from "@/hooks/useSquadSocket";
import { SquadSelector } from "@/components/SquadSelector";
import { PhaserGame } from "@/office/PhaserGame";
import { StatusBar } from "@/components/StatusBar";
import { Bot, Activity, Map, Settings, PlusCircle, History } from "lucide-react";

import { SquadBuilder } from "@/pages/SquadBuilder";
import { ProcessMap } from "@/pages/ProcessMap";
import { SquadHistory } from "@/pages/SquadHistory";
import { LogsPanel } from "@/components/LogsPanel";

export function App() {
  useSquadSocket();
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="flex h-screen w-full flex-col bg-background text-gray-100 overflow-hidden font-sans">
      
      {/* Header */}
      <header className="flex flex-col md:flex-row items-center justify-between px-4 md:px-6 py-2 md:py-0 md:h-14 border-b border-white/5 bg-surface/80 backdrop-blur-md z-10 relative">
        <div className="flex items-center justify-between w-full md:w-auto mb-2 md:mb-0">
          <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-secondary flex items-center justify-center shadow-[0_0_15px_rgba(255,0,60,0.5)]">
            <Bot size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-gray-100 to-gray-400">
            openminions
          </span>
        </div>
        <div className="flex md:hidden items-center">
          <button className="p-2 text-gray-400 hover:text-white transition-colors">
            <Settings size={20} />
          </button>
        </div>
      </div>
        
        <nav className="flex space-x-1 w-full md:w-auto overflow-x-auto no-scrollbar pb-1 md:pb-0">
          {[
            { id: "overview", icon: Activity, label: "Live Overview" },
            { id: "builder", icon: PlusCircle, label: "Squad Builder" },
            { id: "map", icon: Map, label: "Process Map" },
            { id: "history", icon: History, label: "History" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 md:px-4 py-2 rounded-md text-sm font-medium transition-all duration-300 whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-white/10 text-white shadow-[inset_0_1px_rgba(255,255,255,0.1)]"
                  : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
              }`}
            >
              <tab.icon size={16} className={activeTab === tab.id ? "text-secondary" : ""} />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="hidden md:flex items-center">
          <button className="p-2 text-gray-400 hover:text-white transition-colors">
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Main content grid */}
      <div className="flex flex-col md:flex-row flex-1 overflow-hidden relative p-4 gap-4 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-surface via-background to-background">
        
        {/* Left Sidebar - Squad selection glass panel */}
        <div className="w-full h-1/3 min-h-[200px] shrink-0 md:h-auto md:w-80 flex flex-col gap-4 z-10 animate-fade-in">
          <div className="glass-panel flex-1 flex flex-col overflow-hidden relative">
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
            <SquadSelector />
          </div>
        </div>

        {/* Center / Right - Phaser visualization & logs OR Builder UI */}
        <div className="flex-1 flex flex-col gap-4 relative z-0 animate-[fadeIn_0.5s_ease-out]">
          <div className="glass-panel flex-1 overflow-hidden relative group">
            {activeTab === "builder" ? (
              <SquadBuilder />
            ) : activeTab === "map" ? (
              <ProcessMap />
            ) : activeTab === "history" ? (
              <SquadHistory />
            ) : (
              <>
               {/* Glow effect behind phaser */}
               <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-secondary/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-secondary/20 transition-all duration-700"></div>
               <PhaserGame />
               <LogsPanel />
              </>
            )}
          </div>
        </div>

      </div>

      {/* Footer */}
      <div className="h-10 border-t border-white/5 bg-surface/90 backdrop-blur-md z-20">
        <StatusBar />
      </div>
    </div>
  );
}
