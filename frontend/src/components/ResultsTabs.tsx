import { useState } from 'react';
import type { StageEvent } from '../types';

interface Props { events: StageEvent[]; resultData: Record<string, unknown>; }

type TabId = 'overview' | 'reviews' | 'topics' | 'findings' | 'prd' | 'tests' | 'trace';
const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: '📊' },
  { id: 'reviews', label: 'Reviews', icon: '📝' },
  { id: 'topics', label: 'Topics', icon: '🏷️' },
  { id: 'findings', label: 'Findings', icon: '🔍' },
  { id: 'prd', label: 'PRD', icon: '📋' },
  { id: 'tests', label: 'Test Cases', icon: '✅' },
  { id: 'trace', label: 'Traceability', icon: '🔗' },
];

export default function ResultsTabs({ events, resultData }: Props) {
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
            {t.icon} {t.label}
          </button>
        ))}
      </nav>
      <div className="mt-4">{content()}</div>
    </div>
  );
}

/* ===== Overview ===== */
function Overview({ events, data }: Props) {
  const validation = data.validation as Record<string, unknown> | undefined;
  const findings = data.findings as unknown[] | undefined;
  const summary = events.filter((e) => e.status === 'completed');

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="font-semibold mb-4">Pipeline Summary</h3>
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
        <h3 className="font-semibold mb-4">Key Metrics</h3>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Findings" value={findings?.length ?? '-'} />
          <Stat label="Test Cases" value={data.count as number ?? '-'} />
          <Stat label="Fully Traced" value={validation?.requirements_fully_traced as number ?? '-'} />
          <Stat label="Orphan Tests" value={validation?.orphan_tests as number ?? '-'} warn />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, warn }: { label: string; value: string | number; warn?: boolean }) {
  return (
    <div className={`p-3 rounded-lg ${warn && value !== 0 && value !== '-' ? 'bg-red-50' : 'bg-gray-50'}`}>
      <div className={`text-2xl font-bold ${warn && value !== 0 && value !== '-' ? 'text-red-600' : 'text-gray-900'}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

/* ===== Reviews ===== */
function ReviewsTab({ data, events }: Props) {
  const stats = events.find((e) => e.stats)?.stats as Record<string, number> | undefined;
  if (!stats) return <p className="text-sm text-gray-500">Run analysis to see review data.</p>;
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">Review Statistics</h3>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Stat label="Total Raw" value={stats.total_raw} />
        <Stat label="Cleaned" value={stats.total_cleaned} />
        <Stat label="Kept" value={stats.total_kept} />
        <Stat label="Duplicates" value={stats.duplicates_removed} />
      </div>
      {stats.rating_distribution && (
        <div>
          <h4 className="text-sm font-medium mb-3">Rating Distribution</h4>
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
  );
}

/* ===== Topics ===== */
function TopicsTab({ data }: { data: Record<string, unknown> }) {
  const topics = (data.topics || []) as Record<string, unknown>[];
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">Discovered Topics ({topics.length})</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {topics.map((t, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium">{t.topic_name as string}</h4>
              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${
                t.primary_sentiment === 'negative' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                {t.primary_sentiment as string}
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{t.description as string}</p>
            <span className="text-xs text-gray-400">{t.review_count as number} reviews</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== Findings ===== */
function FindingsTab({ data }: { data: Record<string, unknown> }) {
  const findings = (data.findings || []) as Record<string, unknown>[];
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">Findings ({findings.length})</h3>
      <div className="space-y-4">
        {findings.map((f, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium">{f.title as string}</h4>
              <div className="flex gap-2">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${
                  f.severity === 'critical' ? 'bg-red-100 text-red-800' : f.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                  f.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>{f.severity as string}</span>
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-800">
                  {(f.confidence as number)?.toFixed(0) !== undefined ? `${(f.confidence as number * 100).toFixed(0)}%` : '?'}
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-3">{f.description as string}</p>
            <div>
              <p className="text-xs font-medium text-gray-700">Supporting ({f.supporting_review_count || (f.supporting_review_ids as string[])?.length} reviews):</p>
              {(f.supporting_excerpts as string[])?.slice(0, 3).map((ex, j) => (
                <p key={j} className="text-xs text-gray-500 italic border-l-2 border-green-200 pl-2 mb-1">"{ex}"</p>
              ))}
            </div>
            {(f.conflicting_excerpts as string[])?.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-medium text-gray-700">Conflicting:</p>
                {(f.conflicting_excerpts as string[]).slice(0, 2).map((ex, j) => (
                  <p key={j} className="text-xs text-gray-500 italic border-l-2 border-red-200 pl-2 mb-1">"{ex}"</p>
                ))}
              </div>
            )}
            {(f.uncertainty_notes || f.data_limitations) && (
              <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
                {f.uncertainty_notes && <p>🔮 {f.uncertainty_notes as string}</p>}
                {f.data_limitations && <p>📏 {f.data_limitations as string}</p>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== PRD ===== */
function PRDTab({ data }: { data: Record<string, unknown> }) {
  const versions = (data.versions || data.prd?.versions || []) as Record<string, unknown>[];
  return (
    <div className="space-y-4">
      {data.executive_summary && (
        <div className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold mb-3">Executive Summary</h3>
          <p className="text-sm text-gray-700 whitespace-pre-line">{data.executive_summary as string}</p>
        </div>
      )}
      <h3 className="text-lg font-semibold">Version Plan</h3>
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
            <p className="text-sm mb-4"><strong>Goal:</strong> {v.goal as string}</p>
            <div className="space-y-2">
              <h5 className="font-medium text-sm">{reqs.length} Requirements</h5>
              {reqs.map((r, j) => (
                <div key={j} className="border rounded p-3 bg-gray-50">
                  <div className="flex justify-between mb-1">
                    <h6 className="font-medium text-sm">{r.is_assumption ? '🔮 ' : ''}{r.title as string}</h6>
                    <div className="flex gap-1">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${r.priority === 'P0' ? 'bg-red-100 text-red-800' : r.priority === 'P1' ? 'bg-orange-100 text-orange-800' : 'bg-gray-100'}`}>{r.priority as string}</span>
                      {r.is_assumption && <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-purple-100 text-purple-800">assumption</span>}
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

/* ===== Test Cases ===== */
function TestsTab({ data }: { data: Record<string, unknown> }) {
  const tests = (data.test_cases || []) as Record<string, unknown>[];
  return (
    <div className="bg-white rounded-lg border p-5">
      <h3 className="font-semibold mb-4">Test Cases ({tests.length})</h3>
      <div className="space-y-3">
        {tests.map((tc, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex justify-between mb-2">
              <h4 className="font-medium text-sm">{tc.title as string}</h4>
              <div className="flex gap-1">
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">{tc.test_type as string}</span>
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${tc.priority === 'P0' ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}>{tc.priority as string}</span>
              </div>
            </div>
            <p className="text-xs text-gray-600 mb-3">{tc.description as string}</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><p className="font-medium">Preconditions</p><p className="text-gray-600">{tc.preconditions as string}</p></div>
              <div><p className="font-medium">Expected</p><p className="text-gray-600">{tc.expected_result as string}</p></div>
            </div>
            <div className="mt-2">
              <p className="text-xs font-medium">Steps</p>
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

/* ===== Traceability ===== */
function TraceTab({ data }: { data: Record<string, unknown> }) {
  const v = data.validation as Record<string, unknown> | undefined;
  if (!v) return <p className="text-sm text-gray-500">No validation data yet.</p>;
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-5">
        <h3 className="font-semibold mb-4">Traceability Validation</h3>
        <div className="grid grid-cols-4 gap-3">
          <Stat label="Findings w/ Support" value={v.findings_with_support as number} />
          <Stat label="Without Support" value={v.findings_without_support as number} warn />
          <Stat label="Fully Traced" value={v.requirements_fully_traced as number} />
          <Stat label="Orphan Tests" value={v.orphan_tests as number} warn />
        </div>
      </div>
      {(v.issues as string[])?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="font-medium text-red-800">Issues</h4>
          {(v.issues as string[]).map((iss, i) => <p key={i} className="text-sm text-red-700">{iss}</p>)}
        </div>
      )}
      {(v.marked_assumptions as string[])?.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="font-medium text-purple-800">Marked as Assumptions</h4>
          {(v.marked_assumptions as string[]).map((a, i) => <p key={i} className="text-sm text-purple-700">{a}</p>)}
        </div>
      )}
      <div className="bg-white rounded-lg border p-5 text-center">
        <div className="flex items-center justify-center gap-4 text-sm py-4">
          <div className="p-3 bg-blue-50 rounded border font-bold text-blue-700">Reviews</div>
          <span className="text-2xl text-gray-300">→</span>
          <div className="p-3 bg-green-50 rounded border font-bold text-green-700">Findings</div>
          <span className="text-2xl text-gray-300">→</span>
          <div className="p-3 bg-purple-50 rounded border font-bold text-purple-700">Requirements</div>
          <span className="text-2xl text-gray-300">→</span>
          <div className="p-3 bg-orange-50 rounded border font-bold text-orange-700">Test Cases</div>
        </div>
        <p className="text-xs text-gray-400">Unsupported findings removed; untraceable requirements marked as assumptions.</p>
      </div>
    </div>
  );
}
