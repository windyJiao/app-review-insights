import { useState } from 'react';
import { useTr } from '../i18n/LanguageContext';
import type { StageEvent } from '../types';

interface Props { events: StageEvent[]; resultData: Record<string, unknown>; }

type TabId = 'overview' | 'reviews' | 'topics' | 'findings' | 'prd' | 'tests' | 'trace';
const TABS: { id: TabId; key: string }[] = [
  { id: 'overview', key: 'tab.overview' },
  { id: 'reviews', key: 'tab.reviews' },
  { id: 'topics', key: 'tab.topics' },
  { id: 'findings', key: 'tab.findings' },
  { id: 'prd', key: 'tab.prd' },
  { id: 'tests', key: 'tab.tests' },
  { id: 'trace', key: 'tab.trace' },
];

export default function ResultsTabs({ events, resultData }: Props) {
  const { tr } = useTr();
  const [tab, setTab] = useState<TabId>('overview');

  const content = () => {
    switch (tab) {
      case 'overview': return <Overview events={events} data={resultData} />;
      case 'reviews': return <ReviewsTab data={resultData} events={events} />;
      case 'topics': return <TopicsTab data={resultData} />;
      case 'findings': return <FindingsTab data={resultData} />;
      case 'prd': return <PRDTab data={resultData} />;
      case 'tests': return <TestsTab data={resultData} />;
      case 'trace': return <TraceTab data={resultData} />;
    }
  };

  return (
    <div className="mt-6">
      <nav className="flex space-x-2 -mb-px overflow-x-auto border-b border-gray-200">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-3 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition ${
              tab === t.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {tr(t.key)}
          </button>
        ))}
      </nav>
      <div className="mt-4">{content()}</div>
    </div>
  );
}

/* ===== Sub-components with translations ===== */

function Stat({ label, value, warn }: { label: string; value: string | number; warn?: boolean }) {
  return (
    <div className={`p-3 rounded-lg ${warn && value !== 0 && value !== '-' ? 'bg-red-50' : 'bg-gray-50'}`}>
      <div className={`text-2xl font-bold ${warn && value !== 0 && value !== '-' ? 'text-red-600' : 'text-gray-900'}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function Overview({ events, data }: Props) {
  const { tr } = useTr();
  const validation = data.validation as Record<string, unknown> | undefined;
  const findings = data.findings as unknown[] | undefined;
  const summary = events.filter((e) => e.status === 'completed');

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="font-semibold mb-4">{tr('overview.pipeline')}</h3>
        <div className="space-y-2">
          {summary.map((evt, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span className="text-gray-600">{evt.stage}</span>
              <span className="text-green-600">✓ {evt.message}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="font-semibold mb-4">{tr('overview.metrics')}</h3>
        <div className="grid grid-cols-2 gap-3">
          <Stat label={tr('overview.findings')} value={findings?.length ?? '-'} />
          <Stat label={tr('overview.testCases')} value={data.count as number ?? '-'} />
          <Stat label={tr('overview.fullyTraced')} value={validation?.requirements_fully_traced as number ?? '-'} />
          <Stat label={tr('overview.orphanTests')} value={validation?.orphan_tests as number ?? '-'} warn />
        </div>
      </div>
    </div>
  );
}

function ReviewsTab({ data, events }: Props) {
  const { tr } = useTr();
  const stats = data.cleaning_stats as Record<string, number> | undefined
    || events.find((e) => e.stats)?.stats as Record<string, number> | undefined;
  const reviews = (data.cleaned_reviews || []) as Record<string, unknown>[];

  return (
    <div className="space-y-4">
      {stats && (
        <div className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold mb-4">{tr('reviews.title')}</h3>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <Stat label={tr('reviews.totalRaw')} value={stats.total_raw} />
            <Stat label={tr('reviews.cleaned')} value={stats.total_cleaned} />
            <Stat label={tr('reviews.kept')} value={stats.total_kept} />
            <Stat label={tr('reviews.duplicates')} value={stats.duplicates_removed} />
          </div>
          {stats.rating_distribution && (
            <div>
              <h4 className="text-sm font-medium mb-3">{tr('reviews.ratingDist')}</h4>
              <div className="space-y-2">
                {Object.entries(stats.rating_distribution as Record<string, number>).sort(([a], [b]) => Number(b) - Number(a)).map(([r, c]) => {
                  const total = Object.values(stats.rating_distribution as Record<string, number>).reduce((a, b) => a + b, 0);
                  return (
                    <div key={r} className="flex items-center gap-3">
                      <span className="text-sm w-16">{'⭐'.repeat(Number(r))}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-5"><div className="bg-yellow-400 h-5 rounded-full" style={{ width: `${total > 0 ? (c / total) * 100 : 0}%` }} /></div>
                      <span className="text-sm text-gray-600 w-12 text-right">{c}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      {reviews.length > 0 && (
        <div className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold mb-4">📝 {tr('tab.reviews')} ({reviews.length})</h3>
          <div className="space-y-3">
            {reviews.map((r, i) => (
              <div key={i} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="font-medium text-sm">{r.title as string}</span>
                    <span className="ml-2">{'⭐'.repeat(r.rating as number)}</span>
                  </div>
                  <div className="flex gap-2 text-xs text-gray-400">
                    <span>{r.author as string}</span>
                    <span>{r.date as string}</span>
                    {(r.version as string) && <span>v{r.version as string}</span>}
                  </div>
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-line">{r.content as string}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {!stats && reviews.length === 0 && (
        <p className="text-sm text-gray-500">{tr('reviews.noData')}</p>
      )}
    </div>
  );
}

function TopicsTab({ data }: { data: Record<string, unknown> }) {
  const { tr } = useTr();
  const topics = (data.topics || []) as Record<string, unknown>[];
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">{tr('topics.title')} ({topics.length})</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {topics.map((t, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium">{t.topic_name as string}</h4>
              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${
                t.primary_sentiment === 'negative' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                {tr(`sentiment.${t.primary_sentiment}`)}
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{t.description as string}</p>
            <span className="text-xs text-gray-400">{t.review_count as number} {tr('topics.reviews')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FindingsTab({ data }: { data: Record<string, unknown> }) {
  const { tr } = useTr();
  const findings = (data.findings || []) as Record<string, unknown>[];
  return (
    <div className="bg-white rounded-lg border p-5">
      <div className="flex justify-between mb-4 items-center">
        <h3 className="font-semibold">{tr('findings.title')} ({findings.length})</h3>
        <div className="flex gap-3 text-xs">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500 inline-block" /> {tr('findings.modelHint')}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-500 inline-block" /> {tr('findings.statHint')}</span>
        </div>
      </div>
      <div className="space-y-4">
        {findings.map((f, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium">{f.title as string}</h4>
              <div className="flex gap-2">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${
                  f.severity === 'critical' ? 'bg-red-100 text-red-800' : f.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                  f.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>{tr(`severity.${f.severity}`)}</span>
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-800">
                  {typeof f.confidence === 'number' ? `${(f.confidence * 100).toFixed(0)}%` : '?'}
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-3">{f.description as string}</p>
            <div>
              <p className="text-xs font-medium text-gray-700">{tr('findings.supporting')} ({f.supporting_review_count || (f.supporting_review_ids as string[])?.length} {tr('findings.reviews')}):</p>
              {(f.supporting_excerpts as string[])?.slice(0, 3).map((ex, j) => (
                <p key={j} className="text-xs text-gray-500 italic border-l-2 border-green-200 pl-2 mb-1">"{ex}"</p>
              ))}
            </div>
            {(f.conflicting_excerpts as string[])?.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-gray-700">{tr('findings.conflicting')}:</p>
                {(f.conflicting_excerpts as string[]).slice(0, 2).map((ex, j) => (
                  <p key={j} className="text-xs text-gray-500 italic border-l-2 border-red-200 pl-2 mb-1">"{ex}"</p>
                ))}
              </div>
            )}
            {(f.uncertainty_notes || f.data_limitations) && (
              <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
                {f.uncertainty_notes && <p>🔮 {tr('findings.uncertainty')}: {f.uncertainty_notes as string}</p>}
                {f.data_limitations && <p>📏 {tr('findings.limitations')}: {f.data_limitations as string}</p>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function PRDTab({ data }: { data: Record<string, unknown> }) {
  const { tr } = useTr();
  const versions = (data.versions || (data.prd as Record<string, unknown>)?.versions || []) as Record<string, unknown>[];
  const execSummary = data.executive_summary || (data.prd as Record<string, unknown>)?.executive_summary;
  return (
    <div className="space-y-4">
      {execSummary && (
        <div className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold mb-3">{tr('prd.executiveSummary')}</h3>
          <p className="text-sm text-gray-700 whitespace-pre-line">{execSummary as string}</p>
        </div>
      )}
      <h3 className="text-lg font-semibold">{tr('prd.versionPlan')}</h3>
      {versions.map((v, i) => {
        const reqs = (v.requirements || []) as Record<string, unknown>[];
        return (
          <div key={i} className="bg-white rounded-lg border p-5">
            <div className="flex justify-between mb-3">
              <div>
                <h4 className="font-semibold text-lg">{v.version_name as string}</h4>
                <p className="text-sm text-gray-500">{v.description as string}</p>
              </div>
              {v.timeline_estimate && <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100">{v.timeline_estimate as string}</span>}
            </div>
            <p className="text-sm mb-4"><strong>{tr('prd.goal')}:</strong> {v.goal as string}</p>
            <div className="space-y-2">
              <h5 className="font-medium text-sm">{reqs.length} {tr('prd.requirements')}</h5>
              {reqs.map((r, j) => (
                <div key={j} className="border rounded p-3 bg-gray-50">
                  <div className="flex justify-between mb-1">
                    <h6 className="font-medium text-sm">{r.is_assumption ? '🔮 ' : ''}{r.title as string}</h6>
                    <div className="flex gap-1">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${r.priority === 'P0' ? 'bg-red-100 text-red-800' : r.priority === 'P1' ? 'bg-orange-100 text-orange-800' : 'bg-gray-100'}`}>{r.priority as string}</span>
                      {r.is_assumption && <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-800">{tr('prd.assumption')}</span>}
                    </div>
                  </div>
                  <p className="text-xs text-gray-600">{r.description as string}</p>
                  {r.assumption_rationale && <p className="mt-1 text-xs text-purple-600">{r.assumption_rationale as string}</p>}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TestsTab({ data }: { data: Record<string, unknown> }) {
  const { tr } = useTr();
  const tests = (data.test_cases || []) as Record<string, unknown>[];
  if (tests.length === 0) return <p className="text-sm text-gray-500">{tr('tests.noData')}</p>;
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">{tr('tests.title')} ({tests.length})</h3>
      <div className="space-y-3">
        {tests.map((tc, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium text-sm">{tc.title as string}</h4>
              <div className="flex gap-1">
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">{tr(`testType.${tc.test_type}`)}</span>
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${tc.priority === 'P0' ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>{tr(`priority.${tc.priority}`)}</span>
              </div>
            </div>
            <p className="text-xs text-gray-600 mb-3">{tc.description as string}</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><p className="font-medium">{tr('tests.preconditions')}</p><p className="text-gray-600">{tc.preconditions as string}</p></div>
              <div><p className="font-medium">{tr('tests.expected')}</p><p className="text-gray-600">{tc.expected_result as string}</p></div>
            </div>
            <div className="mt-2">
              <p className="text-xs font-medium">{tr('tests.steps')}</p>
              <ol className="list-decimal list-inside text-xs text-gray-600">
                {(tc.steps as string[])?.map((s, si) => <li key={si}>{s}</li>)}
              </ol>
            </div>
            <div className="mt-2 flex gap-4 text-xs text-gray-400 border-t pt-2">
              <span>Req: {tc.linked_req_id as string}</span>
              <span>Reviews: {(tc.linked_review_ids as string[])?.join(', ') || 'none'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TraceTab({ data }: { data: Record<string, unknown> }) {
  const { tr } = useTr();
  const v = data.validation as Record<string, unknown> | undefined;
  if (!v) return <p className="text-sm text-gray-500">{tr('trace.noData')}</p>;

  const totalFindings = (v.total_findings as number) || 0;
  const totalReqs = (v.total_requirements as number) || 0;
  const totalTests = (v.total_tests as number) || 0;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-5">
        <h3 className="font-semibold mb-3">{tr('trace.title')}</h3>
        <p className="text-sm text-gray-600 mb-4">
          从 {totalFindings} 条结论 → {totalReqs} 个需求 → {totalTests} 个测试，每步都需要评论支撑。
          {totalFindings < 3 && ' 当前评论量偏少，大部分需求为 AI 推测，已标注。'}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label={tr('trace.findingsWithSupport')} value={v.findings_with_support as number} />
          <Stat label={tr('trace.withoutSupport')} value={v.findings_without_support as number} warn />
          <Stat label={tr('trace.fullyTraced')} value={v.requirements_fully_traced as number} />
          <Stat label={tr('trace.orphanTests')} value={v.orphan_tests as number} warn />
        </div>
      </div>
      {(v.marked_assumptions as string[])?.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="font-medium text-purple-800 mb-1">{tr('trace.assumptions')}</h4>
          <p className="text-xs text-purple-600 mb-2">以下需求缺乏直接评论支撑，是 AI 根据趋势推测的：</p>
          {(v.marked_assumptions as string[]).map((a, i) => <p key={i} className="text-sm text-purple-700">🔮 {a}</p>)}
        </div>
      )}
      {(v.issues as string[])?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="font-medium text-red-800">{tr('trace.issues')}</h4>
          {(v.issues as string[]).map((iss, i) => <p key={i} className="text-sm text-red-700">{iss}</p>)}
        </div>
      )}
      <div className="bg-white rounded-lg border p-5">
        <h4 className="font-medium text-sm mb-3">数据溯源链</h4>
        <div className="flex items-center justify-center gap-2 text-xs py-3 flex-wrap">
          <span className="px-3 py-1.5 bg-blue-50 rounded border font-bold text-blue-700">💬 评论</span>
          <span className="text-gray-300">→</span>
          <span className="px-3 py-1.5 bg-green-50 rounded border font-bold text-green-700">🔍 结论</span>
          <span className="text-gray-300">→</span>
          <span className="px-3 py-1.5 bg-purple-50 rounded border font-bold text-purple-700">📋 需求</span>
          <span className="text-gray-300">→</span>
          <span className="px-3 py-1.5 bg-orange-50 rounded border font-bold text-orange-700">✅ 测试</span>
        </div>
        <p className="text-xs text-gray-400 mt-3 text-center">{tr('trace.flowText')}</p>
      </div>
    </div>
  );
}
