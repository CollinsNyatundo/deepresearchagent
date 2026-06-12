import { useEffect, useState } from 'react';
import { Box, Text, Group, ActionIcon, Tooltip } from '@mantine/core';
import { IconPlayerPause, IconPlayerPlay, IconArrowRight } from '@tabler/icons-react';

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
    <Box
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      style={{
        backgroundColor: '#020617',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        width: '100%',
        maxWidth: '750px',
        height: '420px',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      {/* Window Title Bar */}
      <Group
        px="md"
        py="xs"
        justify="space-between"
        style={{
          borderBottom: '1px solid #1e293b',
          backgroundColor: '#0b1329',
          userSelect: 'none',
        }}
      >
        <Group gap={6}>
          <Box style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ef4444' }} />
          <Box style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#eab308' }} />
          <Box style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#22c55e' }} />
        </Group>
        <Text size="xs" c="dimmed" style={{ fontFamily: 'Fira Code, monospace', fontWeight: 500 }}>
          deepresearch-cli - bash
        </Text>
        <Group gap="xs">
          <Tooltip label={isPaused ? 'Resume simulation' : 'Pause simulation'}>
            <ActionIcon
              size="xs"
              variant="transparent"
              c="dimmed"
              onClick={(e) => {
                e.stopPropagation();
                setIsPaused((prev) => !prev);
              }}
            >
              {isPaused ? <IconPlayerPlay size={12} /> : <IconPlayerPause size={12} />}
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Skip to end">
            <ActionIcon
              size="xs"
              variant="transparent"
              c="dimmed"
              onClick={(e) => {
                e.stopPropagation();
                skipToEnd();
              }}
            >
              <IconArrowRight size={12} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {/* Terminal Screen Body */}
      <Box
        p="md"
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
          fontFamily: 'Fira Code, monospace',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          textAlign: 'left',
        }}
      >
        {/* CLI Prompt */}
        <Group gap={4} wrap="nowrap" align="flex-start">
          <Text span c="#10b981" fw={600} style={{ whiteSpace: 'nowrap' }}>
            collins@deepresearch:~$
          </Text>
          <Text
            span
            c="#f59e0b"
            className={step === 0 ? 'blink-cursor' : ''}
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {typedInput}
          </Text>
        </Group>

        {/* Streaming Logs */}
        <Box mt="xs" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {activeLogs.map((log, index) => {
            const isLast = index === activeLogs.length - 1;
            return (
              <Text
                key={index}
                c={getLogColor(log.type)}
                className={isLast && step === 1 ? 'blink-cursor' : ''}
                style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {log.text}
              </Text>
            );
          })}
        </Box>

        {/* Completed status with cursor */}
        {step === 2 && (
          <Box mt="sm" style={{ borderTop: '1px dashed #1e293b', paddingTop: '8px' }}>
            <Text c="#10b981" fw={600} className="blink-cursor">
              collins@deepresearch:~$ 
            </Text>
          </Box>
        )}
      </Box>

      {/* Control Info Overlay at bottom */}
      <Box
        px="sm"
        py={4}
        style={{
          borderTop: '1px solid #1e293b',
          backgroundColor: '#0b1329',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text size="10px" c="dimmed" style={{ fontFamily: 'Fira Code, monospace' }}>
          [Hover to Pause] [Click Skip to finish]
        </Text>
        {isPaused && (
          <Text size="10px" c="amber" style={{ fontFamily: 'Fira Code, monospace', fontWeight: 600 }}>
            PAUSED
          </Text>
        )}
      </Box>
    </Box>
  );
}
