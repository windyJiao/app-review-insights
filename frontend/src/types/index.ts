export interface AnalysisRequest {
  app_url: string;
  goal?: string;
  max_reviews: number;
}

export interface StageEvent {
  stage: string;
  status: string;
  message: string;
  progress: number;
  timestamp: string;
  count?: number;
  warnings?: string[];
  stats?: Record<string, unknown>;
  topics?: TopicSummary[];
  findings?: FindingSummary[];
  validation?: ValidationResult;
  [key: string]: unknown;
}

export interface TopicSummary {
  topic_name: string;
  review_count: number;
  primary_sentiment: string;
}

export interface FindingSummary {
  title: string;
  severity: string;
  confidence: number;
  supporting_count: number;
}

export interface RawReview {
  id: string; rating: number; title: string; content: string;
  author: string; version?: string; date: string;
}

export interface CleanedReview {
  id: string; rating: number; title: string; content: string;
  content_length: number; author: string; version?: string;
  date: string; language: string; is_duplicate: boolean;
  duplicate_of?: string; quality_flag: string;
}

export interface TopicCluster {
  topic_id: string; topic_name: string; description: string;
  review_ids: string[]; review_count: number;
  sentiment_distribution: Record<string, number>;
  representative_excerpts: string[]; keywords: string[];
}

export interface Finding {
  finding_id: string; category: string; title: string;
  description: string; severity: string; confidence: number;
  source: string; supporting_review_ids: string[];
  supporting_review_count: number; supporting_excerpts: string[];
  conflicting_review_ids: string[]; conflicting_excerpts: string[];
  uncertainty_notes?: string; data_limitations?: string;
}

export interface Requirement {
  req_id: string; title: string; description: string;
  priority: string; category: string;
  source_finding_ids: string[]; source_review_ids: string[];
  is_assumption: boolean; assumption_rationale?: string;
}

export interface PRDVersion {
  version_id: string; version_name: string; description: string;
  goal: string; requirements: Requirement[]; timeline_estimate?: string;
}

export interface PRD {
  title: string; app_name: string; app_id: string;
  analysis_goal?: string; generated_at: string;
  executive_summary: string; versions: PRDVersion[];
  data_notes?: string; limitations: string[];
}

export interface TestCase {
  test_id: string; title: string; description: string;
  preconditions: string; steps: string[]; expected_result: string;
  priority: string; linked_req_id: string;
  linked_review_ids: string[]; test_type: string;
}

export interface ValidationResult {
  total_findings: number; total_requirements: number; total_tests: number;
  findings_with_support: number; findings_without_support: number;
  requirements_fully_traced: number; requirements_partially_traced: number;
  tests_linked_to_reviews: number; orphan_tests: number;
  removed_unsupported_findings: string[];
  revised_findings: Record<string, unknown>[];
  marked_assumptions: string[]; issues: string[];
}

export type AnalysisStage =
  'idle' | 'collect' | 'clean' | 'classify' | 'analyze'
  | 'prd' | 'tests' | 'validate' | 'complete' | 'error';

export interface StageState {
  stage: AnalysisStage;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
  progress: number;
}
