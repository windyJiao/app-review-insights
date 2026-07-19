import { useState, useRef } from 'react';
import { useTr } from '../i18n/LanguageContext';

interface Props {
  onImport: (file: File, format: 'json' | 'csv', goal?: string, appName?: string, lang?: string) => Promise<void>;
  isRunning: boolean;
  lang?: string;
}

export default function ImportPanel({ onImport, isRunning, lang }: Props) {
  const { tr } = useTr();
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState<'json' | 'csv'>('json');
  const [goal, setGoal] = useState('');
  const [appName, setAppName] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setFile(f); if (f.name.endsWith('.csv')) setFormat('csv'); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    await onImport(file, format, goal.trim() || undefined, appName.trim() || undefined, lang);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <input ref={fileRef} type="file" accept=".json,.csv" onChange={handleFile} className="hidden" disabled={isRunning} />
        <div onClick={() => !isRunning && fileRef.current?.click()} className={isRunning ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}>
          <span className="text-4xl">📁</span>
          <p className="mt-2 text-sm font-medium text-gray-700">{file ? file.name : tr('import.dropHint')}</p>
          <p className="mt-1 text-xs text-gray-400">{tr('import.dropSub')}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{tr('import.format')}</label>
          <select value={format} onChange={(e) => setFormat(e.target.value as 'json'|'csv')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white" disabled={isRunning}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{tr('import.appName')}</label>
          <input type="text" value={appName} onChange={(e) => setAppName(e.target.value)}
            placeholder="My App" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" disabled={isRunning} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{tr('import.goal')}</label>
          <input type="text" value={goal} onChange={(e) => setGoal(e.target.value)}
            placeholder={tr('import.goalPlaceholder')} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" disabled={isRunning} />
        </div>
      </div>
      <div className="mt-6">
        <button type="submit" disabled={!file || isRunning}
          className="px-6 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition">
          {isRunning ? tr('input.running') : tr('import.submit')}
        </button>
      </div>
    </form>
  );
}
