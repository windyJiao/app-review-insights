"""Pydantic data models for the review analysis pipeline."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    COLLECTING = "collecting"
    CLEANING = "cleaning"
    CLASSIFYING = "classifying"
    ANALYZING = "analyzing"
    GENERATING_PRD = "generating_prd"
    GENERATING_TESTS = "generating_tests"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRequest(BaseModel):
    app_url: str = Field(
        default="https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684",
        description="App Store URL (US storefront recommended)"
    )
    goal: Optional[str] = Field(
        default=None,
        description="Analysis goal or constraint"
    )
    max_reviews: int = Field(default=500, ge=50, le=1000)
    lang: str = Field(default="en", description="Output language: 'en' or 'zh'")


class RawReview(BaseModel):
    id: str
    rating: int
    title: str
    content: str
    author: str
    version: Optional[str] = None
    date: str


class CleanedReview(BaseModel):
    id: str
    rating: int
    title: str
    content: str
    content_length: int
    author: str
    version: Optional[str] = None
    date: str
    language: str = "unknown"
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    quality_flag: str = "ok"


class TopicCluster(BaseModel):
    topic_id: str = ""
    topic_name: str
    description: str
    review_ids: list[str] = []
    review_count: int = 0
    sentiment_distribution: dict[str, int] = Field(default_factory=dict)
    representative_excerpts: list[str] = []
    keywords: list[str] = []


class Finding(BaseModel):
    finding_id: str = ""
    category: str
    title: str
    description: str
    severity: str  # critical, high, medium, low
    confidence: float  # 0.0 - 1.0
    source: str = "model"  # "model" or "statistical"
    supporting_review_ids: list[str] = []
    supporting_review_count: int = 0
    supporting_excerpts: list[str] = []
    conflicting_review_ids: list[str] = []
    conflicting_excerpts: list[str] = []
    uncertainty_notes: Optional[str] = None
    data_limitations: Optional[str] = None


class Requirement(BaseModel):
    req_id: str = ""
    title: str
    description: str
    priority: str  # P0, P1, P2, P3
    category: str
    source_finding_ids: list[str] = []
    source_review_ids: list[str] = []
    is_assumption: bool = False
    assumption_rationale: Optional[str] = None


class PRDVersion(BaseModel):
    version_id: str = ""
    version_name: str
    description: str
    goal: str
    requirements: list[Requirement] = []
    timeline_estimate: Optional[str] = None


class PRD(BaseModel):
    title: str = ""
    app_name: str
    app_id: str
    analysis_goal: Optional[str] = None
    generated_at: str = ""
    executive_summary: str = ""
    versions: list[PRDVersion] = []
    data_notes: Optional[str] = None
    limitations: list[str] = []


class TestCase(BaseModel):
    test_id: str = ""
    title: str
    description: str
    preconditions: str
    steps: list[str] = []
    expected_result: str
    priority: str
    linked_req_id: str
    linked_review_ids: list[str] = []
    test_type: str = "functional"


class ValidationResult(BaseModel):
    total_findings: int = 0
    total_requirements: int = 0
    total_tests: int = 0
    findings_with_support: int = 0
    findings_without_support: int = 0
    requirements_fully_traced: int = 0
    requirements_partially_traced: int = 0
    tests_linked_to_reviews: int = 0
    orphan_tests: int = 0
    removed_unsupported_findings: list[str] = []
    revised_findings: list[dict] = []
    marked_assumptions: list[str] = []
    issues: list[str] = []


class AnalysisResult(BaseModel):
    request: Optional[AnalysisRequest] = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    raw_reviews: list[RawReview] = []
    cleaned_reviews: list[CleanedReview] = []
    cleaning_stats: dict = Field(default_factory=dict)
    topic_clusters: list[TopicCluster] = []
    findings: list[Finding] = []
    prd: Optional[PRD] = None
    test_cases: list[TestCase] = []
    validation: Optional[ValidationResult] = None
    errors: list[str] = []
    warnings: list[str] = []
