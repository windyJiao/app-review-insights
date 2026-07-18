import { useState } from 'react';
import { useTr } from '../i18n/LanguageContext';

interface Props {
  onStart: (p: { app_url: string; goal?: string; max_reviews: number }) => void;
  isRunning: boolean;
}

export default function InputForm({ onStart, isRunning }: Props) {
  const { tr } = useTr();
  const [appUrl, setAppUrl] = useState('https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684');
  const [goal, setGoal] = useState('');
  const [maxReviews, setMaxReviews] = useState(200);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!appUrl.trim()) return;
    onStart({ app_url: appUrl.trim(), goal: goal.trim() || undefined, max_reviews: maxReviews });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">{tr('input.url')}</label>
          <input type="url" value={appUrl} onChange={(e) => setAppUrl(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            required disabled={isRunning} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{tr('input.maxReviews')}</label>
          <select value={maxReviews} onChange={(e) => setMaxReviews(Number(e.target.value))}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            disabled={isRunning}>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={300}>300</option>
            <option value={500}>500</option>
          </select>
        </div>
      </div>
      <div className="mt-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">{tr('input.goal')}</label>
        <input type="text" value={goal} onChange={(e) => setGoal(e.target.value)}
          placeholder={tr('input.goalPlaceholder')}
          className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          disabled={isRunning} />
      </div>
      <div className="mt-6 flex items-center gap-4">
        <button type="submit" disabled={isRunning || !appUrl.trim()}
          className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition flex items-center gap-2">
          {isRunning ? (
            <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg> {tr('input.running')}</>
          ) : tr('input.start')}
        </button>
        {!isRunning && <span className="text-xs text-gray-400">{tr('input.hint')}</span>}
      </div>
    </form>
  );
}
