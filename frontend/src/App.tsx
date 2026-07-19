import { useState } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import InputForm from './components/InputForm';
import ImportPanel from './components/ImportPanel';
import ProgressPanel from './components/ProgressPanel';
import ResultsTabs from './components/ResultsTabs';
import { healthCheck } from './utils/api';
import { LanguageProvider, useTr } from './i18n/LanguageContext';

function AppContent() {
  const { tr, lang, toggleLang } = useTr();
  const { stages, isRunning, events, error, completed, importResult,
    runAnalysis, cancelAnalysis, importData, resetAll } = useAnalysis();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [mode, setMode] = useState<'analyze' | 'import'>('analyze');

  useState(() => { healthCheck().then(setBackendOnline); });

  const resultData = importResult || (() => {
    const r: Record<string, unknown> = {};
    for (const evt of events) {
      for (const k of Object.keys(evt)) {
        if (!['stage', 'status', 'message', 'progress', 'timestamp'].includes(k)) {
          r[k] = evt[k];
        }
      }
    }
    return r;
  })();

  const backendStatus = backendOnline === null
    ? tr('app.checking') : backendOnline ? tr('app.connected') : tr('app.offline');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-3">{tr('app.title')}</h1>
              <p className="mt-1 text-sm text-gray-500">{tr('app.subtitle')}</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={toggleLang}
                className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition"
              >
                {lang === 'en' ? '🇨🇳 中文' : '🇺🇸 English'}
              </button>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${backendOnline === null ? 'bg-yellow-400' : backendOnline ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="text-xs text-gray-400">{backendStatus}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex space-x-4 mb-6">
          {(['analyze', 'import'] as const).map((m) => (
            <button key={m} onClick={() => { setMode(m); resetAll(); }}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition ${
                mode === m ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border hover:bg-gray-50'}`}>
              {m === 'analyze' ? tr('tab.analyze') : tr('tab.import')}
            </button>
          ))}
        </div>

        {mode === 'analyze'
          ? <InputForm onStart={runAnalysis} isRunning={isRunning} lang={lang} />
          : <ImportPanel onImport={importData} isRunning={isRunning} lang={lang} />}

        {(isRunning || completed) && (
          <ProgressPanel stages={stages} isRunning={isRunning} onCancel={cancelAnalysis} />
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h3 className="font-medium text-red-800">{tr('error.title')}</h3>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        )}

        {events.length > 0 && (
          <details className="mt-4 bg-white rounded-lg border overflow-hidden">
            <summary className="px-4 py-3 cursor-pointer hover:bg-gray-50 font-medium">
              {tr('eventLog.title')} ({events.length})
            </summary>
            <div className="max-h-64 overflow-y-auto px-4 py-2 border-t">
              {events.map((evt, i) => (
                <div key={i} className="text-xs font-mono py-1 flex gap-3">
                  <span className={evt.status === 'completed' ? 'text-green-600' : evt.status === 'failed' ? 'text-red-600' : 'text-blue-600'}>[{evt.stage}]</span>
                  <span className="text-gray-600 truncate">{evt.message}</span>
                </div>
              ))}
            </div>
          </details>
        )}

        {completed && <ResultsTabs events={events} resultData={resultData} />}
      </main>

      <footer className="mt-12 py-6 border-t bg-white">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-400">
          <p>{tr('footer.text')}</p>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}
