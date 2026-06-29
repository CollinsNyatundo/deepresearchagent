import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { z } from 'zod';
import { api } from '../api/client';
import type { ResearchEvent, PlanPreview, TelemetryResponse } from '../types/api';

export type AppState = 'idle' | 'plan_loading' | 'plan_review' | 'streaming' | 'results';

const researchSchema = z.object({
  query: z.string().min(3, 'Query must be at least 3 characters'),
  model: z.string().min(1, 'Model is required'),
  depth: z.number().min(1).max(5),
  mode: z.enum(['web', 'github']),
  provider: z.enum(['openrouter', 'groq']),
});

interface ResearchContextType {
  selectedWorkspaceId: string | null;
  setSelectedWorkspaceId: (id: string | null) => void;
  selectedRunId: string | null;
  setSelectedRunId: (id: string | null) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  refreshKey: number;
  setRefreshKey: React.Dispatch<React.SetStateAction<number>>;
  globalView: 'research' | 'code-arch';
  setGlobalView: (v: 'research' | 'code-arch') => void;
  appState: AppState;
  setAppState: (state: AppState) => void;
  resultsSidebarExpanded: boolean;
  setResultsSidebarExpanded: (v: boolean) => void;
  advancedOpen: boolean;
  setAdvancedOpen: (v: boolean) => void;
  query: string;
  setQuery: (q: string) => void;
  model: string;
  setModel: (m: string) => void;
  provider: 'openrouter' | 'groq';
  setProvider: (p: 'openrouter' | 'groq') => void;
  depth: number;
  setDepth: (d: number) => void;
  mode: 'web' | 'github';
  setMode: (m: 'web' | 'github') => void;
  isSubmitting: boolean;
  setIsSubmitting: (b: boolean) => void;
  planPreview: PlanPreview | null;
  setPlanPreview: (p: PlanPreview | null) => void;
  planQuery: string;
  setPlanQuery: (q: string) => void;
  streamEvents: ResearchEvent[];
  setStreamEvents: React.Dispatch<React.SetStateAction<ResearchEvent[]>>;
  isStreaming: boolean;
  setIsStreaming: (b: boolean) => void;
  telemetry: TelemetryResponse | null;
  setTelemetry: (t: TelemetryResponse | null) => void;
  fetchTelemetry: () => Promise<void>;

  handleProviderChange: (val: 'openrouter' | 'groq') => void;
  handleGeneratePlan: () => Promise<void>;
  handleApproveAndStart: (steps: string[], subQueries: string[], exportFormats: string[]) => void;
  handleQuickStart: () => Promise<void>;
  resetToIdle: () => void;
  reconnectToRun: (runId: string) => void;
}

const ResearchContext = createContext<ResearchContextType | undefined>(undefined);

export const ResearchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('report');
  const [refreshKey, setRefreshKey] = useState(0);

  const [globalView, setGlobalView] = useState<'research' | 'code-arch'>('research');
  const [appState, setAppState] = useState<AppState>('idle');
  const [resultsSidebarExpanded, setResultsSidebarExpanded] = useState(true);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const [query, setQuery] = useState('');
  const [model, setModel] = useState('nvidia/nemotron-3-super-120b-a12b:free');
  const [provider, setProvider] = useState<'openrouter' | 'groq'>('openrouter');
  const [depth, setDepth] = useState(5);
  const [mode, setMode] = useState<'web' | 'github'>('web');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);
  const [planQuery, setPlanQuery] = useState('');

  const [streamEvents, setStreamEvents] = useState<ResearchEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // Clean up streaming on provider unmount (rare, e.g. logout)
  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  const handleProviderChange = (val: 'openrouter' | 'groq') => {
    setProvider(val);
    if (val === 'groq') {
      setModel('llama-3.3-70b-versatile');
    } else {
      setModel('nvidia/nemotron-3-super-120b-a12b:free');
    }
  };

  const fetchTelemetry = useCallback(async () => {
    try {
      const data = await api.getTelemetry();
      setTelemetry(data);
    } catch (err) {
      console.error('Telemetry failed:', err);
    }
  }, []);

  const handleGeneratePlan = useCallback(async () => {
    const validation = researchSchema.safeParse({ query, model, depth, mode, provider });
    if (!validation.success) {
      toast.error(validation.error.issues[0].message);
      return;
    }
    if (!selectedWorkspaceId) {
      toast.error('Please select or create a workspace first');
      return;
    }
    setIsSubmitting(true);
    setAppState('plan_loading');
    try {
      const preview = await api.generatePlan({
        query: query.trim(),
        model,
        depth,
        mode,
        provider,
        workspace_id: selectedWorkspaceId,
      });
      setPlanPreview(preview);
      setPlanQuery(query.trim());
      setAppState('plan_review');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Plan generation failed');
      setAppState('idle');
    } finally {
      setIsSubmitting(false);
    }
  }, [query, model, depth, mode, provider, selectedWorkspaceId]);

  const handleApproveAndStart = useCallback(
    (steps: string[], subQueries: string[], exportFormats: string[]) => {
      if (!selectedWorkspaceId) {
        toast.error('Please select or create a workspace first');
        return;
      }
      if (abortRef.current) {
        abortRef.current.abort();
      }
      setStreamEvents([]);
      setIsStreaming(true);
      setAppState('streaming');
      setActiveTab('progress');

      const controller = api.streamApprovedPlan(
        {
          query: planQuery,
          plan: { steps },
          sub_queries: subQueries,
          model,
          depth,
          mode,
          provider,
          export_formats: exportFormats,
          workspace_id: selectedWorkspaceId,
        },
        (event) => setStreamEvents((prev) => [...prev, event]),
        (data) => {
          setIsStreaming(false);
          if (data.run_id) {
            setSelectedRunId(data.run_id);
            setRefreshKey((k) => k + 1);
            setActiveTab('report');
            setAppState('results');
          }
        },
        (errorMsg) => {
          setIsStreaming(false);
          toast.error(errorMsg);
        }
      );
      abortRef.current = controller;
    },
    [planQuery, model, depth, mode, provider, selectedWorkspaceId]
  );

  const handleQuickStart = useCallback(async () => {
    const validation = researchSchema.safeParse({ query, model, depth, mode, provider });
    if (!validation.success) {
      toast.error(validation.error.issues[0].message);
      return;
    }
    if (!selectedWorkspaceId) {
      toast.error('Please select or create a workspace first');
      return;
    }
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setIsSubmitting(true);
    setStreamEvents([]);
    setIsStreaming(true);
    setAppState('streaming');
    setActiveTab('progress');

    const controller = api.streamResearch(
      {
        query: query.trim(),
        model,
        depth,
        mode,
        provider,
        workspace_id: selectedWorkspaceId,
      },
      (event) => setStreamEvents((prev) => [...prev, event]),
      (data) => {
        setIsStreaming(false);
        setIsSubmitting(false);
        if (data.run_id) {
          setSelectedRunId(data.run_id);
          setRefreshKey((k) => k + 1);
          setActiveTab('report');
          setAppState('results');
        }
      },
      (errorMsg) => {
        setIsStreaming(false);
        setIsSubmitting(false);
        toast.error(errorMsg);
      }
    );
    abortRef.current = controller;
    setQuery('');
  }, [query, model, depth, mode, provider, selectedWorkspaceId]);

  const resetToIdle = useCallback(() => {
    setPlanPreview(null);
    setPlanQuery('');
    setStreamEvents([]);
    setIsStreaming(false);
    setAppState('idle');
    setSelectedRunId(null);
    setActiveTab('report');
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const reconnectToRun = useCallback(
    (runId: string) => {
      if (!selectedWorkspaceId) return;
      if (abortRef.current) {
        abortRef.current.abort();
      }
      setStreamEvents([]);
      setIsStreaming(true);
      setAppState('streaming');
      setActiveTab('progress');
      setSelectedRunId(runId);

      const controller = api.streamResearch(
        {
          run_id: runId,
          query: '',
          model: '',
          depth: 1,
          mode: 'web',
          provider: 'openrouter',
          workspace_id: selectedWorkspaceId,
        },
        (event) => setStreamEvents((prev) => [...prev, event]),
        (data) => {
          setIsStreaming(false);
          if (data.run_id) {
            setSelectedRunId(data.run_id);
            setRefreshKey((k) => k + 1);
            setActiveTab('report');
            setAppState('results');
          }
        },
        (errorMsg) => {
          setIsStreaming(false);
          toast.error(errorMsg);
        }
      );
      abortRef.current = controller;
    },
    [selectedWorkspaceId]
  );

  return (
    <ResearchContext.Provider
      value={{
        selectedWorkspaceId,
        setSelectedWorkspaceId,
        selectedRunId,
        setSelectedRunId,
        activeTab,
        setActiveTab,
        refreshKey,
        setRefreshKey,
        globalView,
        setGlobalView,
        appState,
        setAppState,
        resultsSidebarExpanded,
        setResultsSidebarExpanded,
        advancedOpen,
        setAdvancedOpen,
        query,
        setQuery,
        model,
        setModel,
        provider,
        setProvider,
        depth,
        setDepth,
        mode,
        setMode,
        isSubmitting,
        setIsSubmitting,
        planPreview,
        setPlanPreview,
        planQuery,
        setPlanQuery,
        streamEvents,
        setStreamEvents,
        isStreaming,
        setIsStreaming,
        telemetry,
        setTelemetry,
        fetchTelemetry,
        handleProviderChange,
        handleGeneratePlan,
        handleApproveAndStart,
        handleQuickStart,
        resetToIdle,
        reconnectToRun,
      }}
    >
      {children}
    </ResearchContext.Provider>
  );
};

export const useResearch = () => {
  const context = useContext(ResearchContext);
  if (context === undefined) {
    throw new Error('useResearch must be used within a ResearchProvider');
  }
  return context;
};
