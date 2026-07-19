import { useState, useRef, useCallback } from 'react';
import { startAnalysis, importAndAnalyzeStream, AnalysisParams } from '../utils/api';
import type { StageEvent, StageState, AnalysisStage } from '../types';

const STAGES: AnalysisStage[] = [
  'collect', 'clean', 'classify', 'analyze', 'prd', 'tests', 'validate'
];

export function useAnalysis() {
  const [stages, setStages] = useState<StageState[]>(
    STAGES.map((s) => ({ stage: s, status: 'pending', message: '', progress: 0 }))
  );
  const [currentStage, setCurrentStage] = useState<AnalysisStage>('idle');
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const updateStage = useCallback((stage: string, status: string, message: string, progress: number) => {
    setStages((prev) => prev.map((s) =>
      s.stage === stage ? { ...s, status: status as StageState['status'], message, progress } : s
    ));
  }, []);

  const resetAll = useCallback(() => {
    setStages(STAGES.map((s) => ({ stage: s, status: 'pending', message: '', progress: 0 })));
    setCurrentStage('idle');
    setIsRunning(false);
    setEvents([]);
    setError(null);
    setCompleted(false);
    setImportResult(null);
    abortRef.current = null;
  }, []);

  const runAnalysis = useCallback((params: AnalysisParams) => {
    resetAll();
    setIsRunning(true);
    setCurrentStage('collect');

    abortRef.current = startAnalysis(
      params,
      (event) => {
        const evt = event as unknown as StageEvent;
        setEvents((prev) => [...prev, evt]);
        const stage = evt.stage as AnalysisStage;
        if (stage && stage !== 'complete' && stage !== 'error') {
          setCurrentStage(stage);
          updateStage(stage, evt.status, evt.message, evt.progress);
        }
        if (stage === 'complete') { setCompleted(true); setIsRunning(false); }
        if (stage === 'error') { setError(evt.message || 'Error'); setIsRunning(false); }
      },
      (err) => { setError(err.message); setIsRunning(false); },
      () => { setIsRunning(false); },
    );
  }, [resetAll, updateStage]);

  const cancelAnalysis = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
  }, []);

  const importData = useCallback(async (
    file: File, format: 'json' | 'csv', goal?: string, appName?: string, lang?: string,
  ) => {
    resetAll();
    setIsRunning(true);
    setCurrentStage('collect');

    abortRef.current = importAndAnalyzeStream(
      file, format, goal, appName, lang,
      (event) => {
        const evt = event as unknown as StageEvent;
        setEvents((prev) => [...prev, evt]);
        const stage = evt.stage as AnalysisStage;
        if (stage && stage !== 'complete' && stage !== 'error') {
          setCurrentStage(stage);
          updateStage(stage, evt.status, evt.message, evt.progress);
        }
        if (stage === 'complete') { setCompleted(true); setIsRunning(false); }
        if (stage === 'error') { setError(evt.message || 'Error'); setIsRunning(false); }
      },
      (err) => { setError(err.message); setIsRunning(false); },
      () => { setIsRunning(false); },
    );
  }, [resetAll, updateStage]);

  return {
    stages, currentStage, isRunning, events, error,
    completed, importResult,
    runAnalysis, cancelAnalysis, importData, resetAll,
  };
}
