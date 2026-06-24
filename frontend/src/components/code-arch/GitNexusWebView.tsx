/**
 * GitNexusWebView — embeds the official GitNexus web UI (gitnexus.vercel.app)
 * inside an iframe and manages the local `gitnexus serve` bridge process.
 *
 * Architecture:
 *   1. User clicks "Start Local Server"
 *   2. We call POST /gitnexus/serve/start → backend spawns `npx gitnexus serve --port 4747`
 *   3. The iframe loads https://gitnexus.vercel.app which auto-detects localhost:4747
 *   4. GitNexus web UI connects and shows the full interactive codebase graph
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Code,
  Play,
  Square,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  Info,
  X,
} from 'lucide-react';
import { api } from '../../api/client';

interface ServeStatus {
  running: boolean;
  pid: number | null;
  port: number;
  web_ui_url: string;
}

const GITNEXUS_WEB_UI = 'https://gitnexus.vercel.app';
const POLL_INTERVAL_MS = 15_000; // 15s — serve status rarely changes

export function GitNexusWebView() {
  const [status, setStatus] = useState<ServeStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0); // force iframe reload
  const [showIframe, setShowIframe] = useState(false);

  // ── Poll serve status ─────────────────────────────────────────────
  const fetchStatus = useCallback(async (silent = false) => {
    try {
      const s = await api.getGitnexusServeStatus();
      setStatus(s);
      if (s.running && !silent) setShowIframe(true);
    } catch {
      // silently swallow — server might just be starting up
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(() => fetchStatus(true), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  // ── Start / Stop ──────────────────────────────────────────────────
  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await api.startGitnexusServe();
      await fetchStatus();
      setShowIframe(true);
      setIframeKey((k) => k + 1); // reload iframe after server comes up
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start gitnexus serve');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    setError(null);
    try {
      await api.stopGitnexusServe();
      await fetchStatus();
      setShowIframe(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop gitnexus serve');
    } finally {
      setIsStopping(false);
    }
  };

  const isRunning = status?.running ?? false;

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* ── Header controls ── */}
      <div className="liquid-glass rounded-xl p-4">
        <div className="flex justify-between items-center flex-nowrap">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#c8956c]/15 text-[#c8956c]">
              <Code size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-semibold text-sm text-[#e0e0e0]">GitNexus Web UI</span>
                {isRunning ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-[#7dac5a]/20 text-[#7dac5a]">
                    <CheckCircle size={10} />
                    Server Running
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-white/[0.03] text-[#999] border border-white/[0.06]">
                    Server Stopped
                  </span>
                )}
                {isRunning && status?.pid && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#c8956c]/15 text-[#c8956c]">
                    PID {status.pid}
                  </span>
                )}
              </div>
              <p className="text-xs text-[#999]">
                Powered by{' '}
                <a href="https://gitnexus.vercel.app" target="_blank" rel="noopener noreferrer" className="text-[#d4a574] hover:text-[#c8956c] transition-colors duration-150">
                  gitnexus.vercel.app
                </a>
                {' '}— interactive codebase topology, community detection &amp; process flows
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {isRunning && (
              <>
                <button
                  title="Reload iframe"
                  className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] transition-colors duration-150"
                  onClick={() => setIframeKey((k) => k + 1)}
                >
                  <RefreshCw size={16} />
                </button>
                <a
                  title="Open in new tab"
                  href={GITNEXUS_WEB_UI}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] transition-colors duration-150"
                >
                  <ExternalLink size={16} />
                </a>
              </>
            )}

            {!isRunning ? (
              <button
                className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleStart}
                disabled={isStarting}
              >
                {isStarting ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Play size={16} />
                )}
                {isStarting ? 'Starting…' : 'Start Local Server'}
              </button>
            ) : (
              <button
                className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-xl bg-[#c45a5a]/15 hover:bg-[#c45a5a]/25 text-[#c45a5a] font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleStop}
                disabled={isStopping}
              >
                {isStopping ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Square size={16} />
                )}
                {isStopping ? 'Stopping…' : 'Stop Server'}
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-3 rounded-xl bg-[#c45a5a]/10 border border-[#c45a5a]/30 p-4 text-[#c45a5a]">
            <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
            <span className="text-sm flex-1">{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-[#c45a5a] hover:text-[#e0e0e0] transition-colors duration-150"
            >
              <X size={14} />
            </button>
          </div>
        )}
      </div>

      {/* ── Not running: instructional empty state ── */}
      {!isRunning && !isStarting && (
        <div className="flex flex-col items-center justify-center gap-8 flex-1 min-h-[400px]">
          <div className="w-20 h-20 rounded-full flex items-center justify-center bg-[#c8956c]/15 text-[#c8956c]">
            <Code size={48} />
          </div>
          <div className="flex flex-col items-center gap-1 max-w-[540px]">
            <h3 className="text-xl font-bold text-[#e0e0e0]">GitNexus Web UI</h3>
            <p className="text-[#999] text-center">
              Click <strong>Start Local Server</strong> above to launch{' '}
              <code className="px-1 py-0.5 rounded bg-white/[0.06] text-[#e0e0e0] font-mono text-xs">
                npx gitnexus serve
              </code>{' '}
              on port 4747. The official GitNexus web interface will auto-connect and display your full codebase graph —
              no configuration required.
            </p>
          </div>

          <div className="liquid-glass rounded-xl p-4 max-w-[480px] w-full">
            <div className="flex items-center gap-1 mb-1">
              <Info size={16} className="text-[#c8956c]" />
              <span className="text-sm font-semibold text-[#e0e0e0]">What you'll see</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {[
                '🕸️  Interactive force-graph of every file, class & function',
                '🏘️  Auto-detected community clusters (functional modules)',
                '🔄  Execution flow traces end-to-end through your code',
                '🔍  Hybrid semantic + BM25 search across the entire codebase',
                '📄  Built-in code inspector with syntax highlighting',
              ].map((item) => (
                <p key={item} className="text-sm text-[#999]">{item}</p>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              className="inline-flex items-center gap-2 text-lg px-6 py-3 rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleStart}
              disabled={isStarting}
            >
              <Play size={20} />
              Start Local Server
            </button>
            <a
              href={GITNEXUS_WEB_UI}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-lg px-6 py-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] text-[#e0e0e0] border border-white/[0.06] transition-colors duration-150"
            >
              <ExternalLink size={20} />
              Open Web UI Directly
            </a>
          </div>

          <p className="text-xs text-[#999]">
            Requires the GitNexus index (run{' '}
            <code className="px-1 py-0.5 rounded bg-white/[0.06] text-[#e0e0e0] font-mono text-xs">
              npx gitnexus analyze
            </code>{' '}
            first if you haven't already)
          </p>
        </div>
      )}

      {/* ── Starting spinner ── */}
      {isStarting && (
        <div className="flex flex-col items-center justify-center gap-4 flex-1 min-h-[400px]">
          <div className="w-12 h-12 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#999]">
            Starting <code className="px-1 py-0.5 rounded bg-white/[0.06] text-[#e0e0e0] font-mono text-xs">npx gitnexus serve</code> on port 4747…
          </p>
          <p className="text-xs text-[#999]">
            The GitNexus web UI will appear automatically once the server is ready.
          </p>
        </div>
      )}

      {/* ── Iframe ── */}
      {isRunning && showIframe && (
        <div
          className="flex-1 min-h-[600px] rounded-xl overflow-hidden border border-[#c8956c]/20"
          style={{ boxShadow: '0 4px 24px rgba(200,149,108,0.12)' }}
        >
          <iframe
            key={iframeKey}
            src={GITNEXUS_WEB_UI}
            title="GitNexus Web UI"
            className="w-full h-full min-h-[600px] block border-none"
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        </div>
      )}

      {/* ── Running but iframe hidden (user manually toggled) ── */}
      {isRunning && !showIframe && (
        <div className="flex flex-col items-center justify-center gap-4 flex-1 min-h-[300px]">
          <CheckCircle size={48} className="text-[#7dac5a]" />
          <p className="font-semibold text-[#e0e0e0]">Server is running on port 4747</p>
          <div className="flex items-center gap-4">
            <button
              className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] font-medium transition-colors duration-150"
              onClick={() => setShowIframe(true)}
            >
              Show Web UI
            </button>
            <a
              href={GITNEXUS_WEB_UI}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] text-[#e0e0e0] border border-white/[0.06] transition-colors duration-150"
            >
              <ExternalLink size={16} />
              Open in New Tab
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
