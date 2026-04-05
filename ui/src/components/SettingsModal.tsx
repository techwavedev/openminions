import { X, Save, Shield } from "lucide-react";
import { useState, useEffect } from "react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [theme, setTheme] = useState("dark");
  const [pinEnabled, setPinEnabled] = useState(false);
  const [telemetry, setTelemetry] = useState(false);

  useEffect(() => {
    // Determine if PIN is enabled from env
    const gatePin = import.meta.env.VITE_DASHBOARD_PIN;
    setPinEnabled(!!gatePin);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-white/10 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col relative animate-scale-in">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
          <h2 className="text-lg font-bold tracking-wide text-gray-200">System Preferences</h2>
          <button 
            onClick={onClose}
            className="p-1 rounded-md text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex flex-col gap-6">
          
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Appearance</h3>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input 
                  type="radio" 
                  name="theme" 
                  value="dark" 
                  checked={theme === "dark"}
                  onChange={() => setTheme("dark")}
                  className="bg-background border-white/20"
                />
                Dark Theme
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-300 opacity-50 cursor-not-allowed" title="Light theme coming soon">
                <input 
                  type="radio" 
                  name="theme" 
                  value="light" 
                  disabled
                  className="bg-background border-white/20"
                />
                Light Theme
              </label>
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Security</h3>
            <div className="flex items-center justify-between p-3 rounded-lg bg-black/20 border border-white/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-secondary/10 text-secondary">
                  <Shield size={18} />
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-200">Dashboard PIN Protection</div>
                  <div className="text-xs text-gray-500">Requires a strict PIN code to access the UI workspace.</div>
                </div>
              </div>
              <div className="text-sm font-bold">
                {pinEnabled ? (
                  <span className="text-green-400">ENABLED</span>
                ) : (
                  <span className="text-red-400">DISABLED</span>
                )}
              </div>
            </div>
            {!pinEnabled && (
              <p className="text-xs text-gray-500 px-1">
                To enable, set <code className="text-gray-400">VITE_DASHBOARD_PIN</code> in your <code className="text-gray-400">ui/.env.local</code> file and restart the server.
              </p>
            )}
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Telemetry</h3>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition-colors" onClick={() => setTelemetry(!telemetry)}>
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-200">Opt-in Usage Analytics</span>
                <span className="text-xs text-gray-500">Help openminions improve by sending anonymous crash reports.</span>
              </div>
              <div className={`w-10 h-6 rounded-full flex items-center p-1 transition-colors ${telemetry ? 'bg-primary' : 'bg-gray-700'}`}>
                <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${telemetry ? 'translate-x-4' : 'translate-x-0'}`} />
              </div>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-white/5 bg-background/50">
          <button 
            onClick={onClose}
            className="px-4 py-2 rounded-md text-sm font-medium text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={onClose}
            className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-primary text-white hover:opacity-90 shadow-lg shadow-primary/20 transition-all"
          >
            <Save size={16} />
            Save Changes
          </button>
        </div>

      </div>
    </div>
  );
}
