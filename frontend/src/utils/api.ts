const API_BASE = '/api';

export interface AnalysisParams {
  app_url: string;
  goal?: string;
  max_reviews: number;
}

export function startAnalysis(
  params: AnalysisParams,
  onEvent: (event: Record<string, unknown>) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
          } catch { /* skip */ }
        }
      }
    }
    onComplete();
  }).catch((err) => {
    if (err.name !== 'AbortError') onError(err);
    onComplete();
  });

  return controller;
}

export async function importAndAnalyze(
  file: File, format: 'json' | 'csv',
  goal?: string, appName?: string,
): Promise<Record<string, unknown>> {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('format', format);
  if (goal) fd.append('goal', goal);
  if (appName) fd.append('app_name', appName);

  const res = await fetch(`${API_BASE}/import/analyze`, { method: 'POST', body: fd });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch { return false; }
}
