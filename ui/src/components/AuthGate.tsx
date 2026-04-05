import { useState, useEffect } from "react";
import { Lock, Unlock, AlertCircle } from "lucide-react";

interface AuthGateProps {
  children: React.ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const gatePin = import.meta.env.VITE_DASHBOARD_PIN;
  
  // If no PIN is configured, skip authentication entirely
  if (!gatePin) {
    return <>{children}</>;
  }

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [pin, setPin] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    // Check if user previously authenticated
    const storedAuth = localStorage.getItem("openminions_auth");
    if (storedAuth === "true") {
      setIsAuthenticated(true);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pin === gatePin) {
      setIsAuthenticated(true);
      setError(false);
      localStorage.setItem("openminions_auth", "true");
    } else {
      setError(true);
      setPin("");
    }
  };

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen w-full flex-col bg-background text-gray-100 overflow-hidden font-sans items-center justify-center p-4 min-h-[400px]">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="glass-panel w-full max-w-sm p-8 flex flex-col items-center z-10 relative border-white/10 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-surface to-background border border-white/5 flex items-center justify-center mb-6 shadow-inner relative overflow-hidden">
             <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
             {error ? (
                <Lock size={28} className="text-[#ff003c] animate-pulse" />
             ) : (
                <Lock size={28} className="text-gray-400" />
             )}
        </div>
        
        <h1 className="text-2xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 mb-2">
            SECURE ACCESS
        </h1>
        <p className="text-sm text-gray-500 mb-8 text-center px-4">
            Enter the dashboard configuration PIN to proceed.
        </p>

        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
          <div className="relative">
            <input
              type="password"
              value={pin}
              onChange={(e) => {
                  setPin(e.target.value);
                  setError(false);
              }}
              placeholder="••••••••"
              autoFocus
              className={`w-full bg-black/40 border ${error ? 'border-[#ff003c]/50 focus:border-[#ff003c]' : 'border-white/10 focus:border-primary/50'} rounded-lg px-4 py-3 text-center tracking-[0.5em] font-mono text-xl outline-none transition-all placeholder:text-gray-600/50`}
            />
          </div>

          {error && (
            <div className="flex items-center justify-center gap-2 text-[#ff003c] text-xs font-medium">
              <AlertCircle size={14} />
              <span>ACCESS DENIED</span>
            </div>
          )}

          <button
            type="submit"
            className="w-full mt-2 bg-gradient-to-r from-primary to-secondary hover:opacity-90 text-white font-bold tracking-widest uppercase text-sm py-3 rounded-lg transition-all shadow-[0_0_15px_rgba(255,0,60,0.3)] hover:shadow-[0_0_25px_rgba(255,0,60,0.5)] flex items-center justify-center gap-2"
          >
            Authenticate <Unlock size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
