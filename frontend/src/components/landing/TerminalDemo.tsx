import { useEffect, useState } from 'react';
import { Pause, Play, ArrowRight } from 'lucide-react';

interface LogLine {
  text: string;
  type: 'input' | 'planning' | 'search' | 'scrape' | 'synthesis' | 'complete';
}

const COMMAND = 'research_engine --query "superconductor breakthroughs" --depth 2';

const SIMULATED_LOGS: LogLine[] = [
  { text: '[PLANNING] Loading LLM models (Nemotron 120B)...', type: 'planning' },
  { text: '[PLANNING] Decomposing topic into research vectors:', type: 'planning' },
  { text: '  * Vector 1: Zero-resistance properties at room temp', type: 'planning' },
  { text: '  * Vector 2: Chemical composition synthesis techniques', type: 'planning' },
  { text: '  * Vector 3: Critical magnetic field tests & replication attempts', type: 'planning' },
  { text: '[SEARCH] Dispatching query to Tavily, Exa, and Brave Search...', type: 'search' },
  { text: '[SEARCH] 🔍 Searching: "Zero-resistance superconductor validation 2026"', type: 'search' },
  { text: '[SEARCH] 🔍 Searching: "high-temperature superconductor chemical synthesis"', type: 'search' },
  { text: '[SEARCH] Retrieved 18 raw search result links.', type: 'search' },
  { text: '[SCRAPE] Fetching web contents using Camoufox StealthyFetcher...', type: 'scrape' },
  { text: '[SCRAPE] 🌐 Scraped page: nature.com/articles/supercond_2026 (Cache hit)', type: 'scrape' },
  { text: '[SCRAPE] 🌐 Scraped page: arxiv.org/abs/2604.1234 (Fetched successfully)', type: 'scrape' },
  { text: '[SCRAPE] 🌐 Scraped page: physicalreview.org/l123 (Fetched successfully)', type: 'scrape' },
  { text: '[SCRAPE] Filtered out duplicate contents and parsed markdown.', type: 'scrape' },
  { text: '[SYNTHESIS] Analyzing scraped contexts (128k tokens total)...', type: 'synthesis' },
  { text: '[SYNTHESIS] Cross-referencing findings & constructing citations...', type: 'synthesis' },
  { text: '[SYNTHESIS] Generating final markdown report...', type: 'synthesis' },
  { text: '[COMPLETE] Research session completed in 3 cycles!', type: 'complete' },
  { text: '[COMPLETE] Citation report written to outputs/run_9b1a/report.md', type: 'complete' },
  { text: '[COMPLETE] Knowledge graph built (24 nodes, 48 edges).', type: 'complete' },
];

export function TerminalDemo() {
  const [typedInput, setTypedInput] = useState('');
  const [activeLogs, setActiveLogs] = useState<LogLine[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [step, setStep] = useState(0); // 0: typing cmd, 1: printing logs, 2: finished
  
  // Main simulation loop
  useEffect(() => {
    if (isPaused) return;

    if (step === 0) {
      // Typing prompt command
      let transitionTimer: ReturnType<typeof setTimeout> | null = null;
      const timer = setInterval(() => {
        setTypedInput((prev) => {
          if (prev.length < COMMAND.length) {
            return COMMAND.slice(0, prev.length + 1);
          } else {
            clearInterval(timer);
            // Wait 600ms before starting logs
            transitionTimer = setTimeout(() => {
              setStep(1);
            }, 600);
            return prev;
          }
        });
      }, 100);
      return () => {
        clearInterval(timer);
        if (transitionTimer) clearTimeout(transitionTimer);
      };
    } else if (step === 1) {
      // Appending log lines
      const timer = setInterval(() => {
        setActiveLogs((prev) => {
          if (prev.length < SIMULATED_LOGS.length) {
            return [...prev, SIMULATED_LOGS[prev.length]];
          } else {
            clearInterval(timer);
            setStep(2);
            return prev;
          }
        });
      }, 200);
      return () => clearInterval(timer);
    } else if (step === 2) {
      // Finished / Idle state - auto-restart after a longer delay
      const timer = setTimeout(() => {
        resetSimulation();
      }, 12000);
      return () => clearTimeout(timer);
    }
  }, [step, isPaused]);

  const resetSimulation = () => {
    setTypedInput('');
    setActiveLogs([]);
    setStep(0);
  };

  const skipToEnd = () => {
    setTypedInput(COMMAND);
    setActiveLogs(SIMULATED_LOGS);
    setStep(2);
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case 'planning':
        return '#f59e0b'; // Gold
      case 'search':
        return '#38bdf8'; // Sky blue
      case 'scrape':
        return '#f43f5e'; // Rose
      case 'synthesis':
        return '#a855f7'; // Purple
      case 'complete':
        return '#10b981'; // Mint
      default:
        return '#f1f5f9';
    }
  };

  return (
    <div
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      className="w-full max-w-[750px] h-[420px] flex flex-col relative overflow-hidden rounded-xl border border-[#1a1a1a] bg-black"
      style={{ boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}
    >
      {/* Window Title Bar */}
      <div
        className="flex justify-between items-center px-4 py-1 select-none bg-[#050505]"
        style={{ borderBottom: '1px solid #1a1a1a' }}
      >
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ef4444]" />
          <div className="w-3 h-3 rounded-full bg-[#eab308]" />
          <div className="w-3 h-3 rounded-full bg-[#22c55e]" />
        </div>
        <span className="text-xs text-[#555] font-medium font-mono">
          deepresearch-cli - bash
        </span>
        <div className="flex items-center gap-1">
          <button
            title={isPaused ? 'Resume simulation' : 'Pause simulation'}
            className="w-5 h-5 rounded flex items-center justify-center text-[#555] hover:text-[#999] transition-colors duration-150"
            onClick={(e) => {
              e.stopPropagation();
              setIsPaused((prev) => !prev);
            }}
          >
            {isPaused ? <Play size={12} /> : <Pause size={12} />}
          </button>
          <button
            title="Skip to end"
            className="w-5 h-5 rounded flex items-center justify-center text-[#555] hover:text-[#999] transition-colors duration-150"
            onClick={(e) => {
              e.stopPropagation();
              skipToEnd();
            }}
          >
            <ArrowRight size={12} />
          </button>
        </div>
      </div>

      {/* Terminal Screen Body */}
      <div
        className="flex-1 overflow-y-auto p-4 flex flex-col items-stretch text-left font-mono text-[0.85rem] leading-relaxed"
      >
        {/* CLI Prompt */}
        <div className="flex gap-1 flex-nowrap items-start">
          <span className="text-[#10b981] font-semibold whitespace-nowrap">
            collins@deepresearch:~$
          </span>
          <span
            className={`text-[#f59e0b] whitespace-pre-wrap break-all ${step === 0 ? 'blink-cursor' : ''}`}
          >
            {typedInput}
          </span>
        </div>

        {/* Streaming Logs */}
        <div className="mt-1 flex flex-col gap-1">
          {activeLogs.map((log, index) => {
            const isLast = index === activeLogs.length - 1;
            return (
              <span
                key={index}
                className={`whitespace-pre-wrap break-all ${isLast && step === 1 ? 'blink-cursor' : ''}`}
                style={{ color: getLogColor(log.type) }}
              >
                {log.text}
              </span>
            );
          })}
        </div>

        {/* Completed status with cursor */}
        {step === 2 && (
          <div className="mt-2 pt-2" style={{ borderTop: '1px dashed #1a1a1a' }}>
            <span className="text-[#10b981] font-semibold blink-cursor">
              collins@deepresearch:~$ 
            </span>
          </div>
        )}
      </div>

      {/* Control Info Overlay at bottom */}
      <div
        className="px-2 py-1 flex justify-between items-center bg-[#050505]"
        style={{ borderTop: '1px solid #1a1a1a' }}
      >
        <span className="text-[10px] text-[#555] font-mono">
          [Hover to Pause] [Click Skip to finish]
        </span>
        {isPaused && (
          <span className="text-[10px] text-[#f59e0b] font-mono font-semibold">
            PAUSED
          </span>
        )}
      </div>
    </div>
  );
}
