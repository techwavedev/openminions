import { useState } from "react";
import { Sparkles, TerminalSquare, Loader2, Bot } from "lucide-react";

export function SquadBuilder() {
  const [intent, setIntent] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [output, setOutput] = useState("");

  const handleGenerate = async () => {
    if (!intent.trim()) return;
    setIsGenerating(true);
    setOutput("");

    try {
      const res = await fetch("/api/create-squad", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent }),
      });
      const data = await res.json();
      if (res.ok) {
        setOutput(data.output);
      } else {
        setOutput(`Error: ${data.error}`);
      }
    } catch (e: any) {
      setOutput(`Failed to communicate with server: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-surface/30 p-8 pt-6 animate-fade-in gap-6 overflow-y-auto">
      
      <div className="flex items-center gap-3 border-b border-white/5 pb-4">
        <Sparkles className="text-secondary" size={24} />
        <h1 className="text-2xl font-bold tracking-tight">AI Squad Builder</h1>
      </div>

      <div className="flex flex-col gap-2 max-w-3xl">
        <label className="text-sm font-medium text-gray-300">Natural Language Intent</label>
        <p className="text-xs text-gray-500 mb-2">
          Describe the problem you want to solve, and the intelligence layer will auto-discover the necessary tools, cross-reference the Qdrant memory, and orchestrate a dedicated multi-agent sub-team to solve it.
        </p>
        <div className="relative group">
          <textarea
            className="w-full h-32 bg-background/50 border border-white/10 rounded-xl p-4 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-secondary/50 focus:border-secondary/50 transition-all text-gray-200 placeholder:text-gray-600 shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)]"
            placeholder="e.g. Build an autonomous team that searches for mentions of our brand on Twitter and compiles a daily reputation report."
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
          />
        </div>
        <div className="flex justify-end mt-2">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !intent.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-secondary/80 to-primary/80 hover:from-secondary hover:to-primary text-white rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(0,240,255,0.2)] hover:shadow-[0_0_25px_rgba(0,240,255,0.4)]"
          >
            {isGenerating ? <Loader2 size={18} className="animate-spin" /> : <Bot size={18} />}
            {isGenerating ? "Synthesizing Pipeline..." : "Generate Squad"}
          </button>
        </div>
      </div>

      {(output || isGenerating) && (
        <div className="flex flex-col gap-2 flex-1 min-h-[300px] max-w-3xl animate-[fadeIn_0.5s_ease-out]">
          <div className="flex items-center gap-2 mt-4 text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-white/5 pb-2">
            <TerminalSquare size={14} />
            Orchestrator Output
          </div>
          <div className="flex-1 bg-[#050505] border border-white/10 rounded-xl p-4 overflow-y-auto font-mono text-xs shadow-[inset_0_5px_20px_rgba(0,0,0,1)] relative group">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-secondary to-primary opacity-50"></div>
            {isGenerating && !output ? (
              <div className="flex items-center gap-3 text-secondary/70 p-4">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse animation-delay-200">●</span>
                <span className="animate-pulse animation-delay-400">●</span>
                <span className="ml-2 font-sans tracking-wide">Connecting to Qdrant Auto-Discovery...</span>
              </div>
            ) : (
              <pre className="text-gray-300 whitespace-pre-wrap leading-relaxed">
                {output}
              </pre>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
