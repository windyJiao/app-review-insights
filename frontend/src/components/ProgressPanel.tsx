import type { StageState } from '../types';

const LABELS: Record<string, string> = {
  collect: '📥 Collecting Reviews',
  clean: '🧹 Cleaning Data',
  classify: '🏷️ Discovering Topics',
  analyze: '🔍 Analyzing Findings',
  prd: '📝 Generating PRD',
  tests: '✅ Test Cases',
  validate: '🔗 Traceability',
};

interface Props {
  stages: StageState[];
  isRunning: boolean;
  onCancel: () => void;
}

export default function ProgressPanel({ stages, isRunning, onCancel }: Props) {
  const overallProgress = Math.max(...stages.map((s) => (s.status !== 'pending' ? s.progress : 0)), 0);

  return (
    <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Analysis Progress</h3>
        {isRunning && <button onClick={onCancel} className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg">Cancel</button>}
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2.5 mb-6">
        <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${overallProgress}%` }} />
      </div>
      <div className="space-y-3">
        {stages.map((stage) => (
          <div key={stage.stage} className="flex items-center gap-4">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
              stage.status === 'completed' ? 'bg-green-100 text-green-600' :
              stage.status === 'running' ? 'bg-blue-100 text-blue-600 animate-pulse' :
              stage.status === 'failed' ? 'bg-red-100 text-red-600' :
              'bg-gray-100 text-gray-400'}`}>
              {stage.status === 'completed' ? '✓' : stage.status === 'running' ? '⋯' : stage.status === 'failed' ? '✗' : '·'}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-medium ${
                stage.status === 'completed' ? 'text-green-700' :
                stage.status === 'running' ? 'text-blue-700' :
                stage.status === 'failed' ? 'text-red-700' : 'text-gray-400'}`}>
                {LABELS[stage.stage] || stage.stage}
              </div>
              {stage.message && <p className="text-xs text-gray-500 truncate">{stage.message}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
