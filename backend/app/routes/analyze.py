"""Main analysis route with SSE progress streaming."""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..models.schemas import AnalysisRequest, AnalysisResult, AnalysisStatus
from ..services.collector import collect_reviews, extract_app_id
from ..services.cleaner import clean_reviews
from ..services.classifier import discover_topics
from ..services.analyzer import analyze_findings
from ..services.prd_generator import generate_prd
from ..services.testcase_gen import generate_test_cases
from ..services.validator import validate_traceability

logger = logging.getLogger(__name__)

router = APIRouter()


def sse_event(stage: str, status: str, data: dict) -> dict:
    data.update({
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return data


@router.post("/analyze")
async def analyze_stream(request: AnalysisRequest):
    """Run analysis with SSE progress streaming."""

    async def event_stream():
        try:
            # Stage 1: Collect
            yield sse_event("collect", "running", {
                "message": "Extracting app ID and collecting reviews...", "progress": 0
            })

            app_id = extract_app_id(request.app_url)
            if not app_id:
                yield sse_event("collect", "failed",
                    {"message": "Could not extract app ID from URL", "progress": 0})
                return

            app_name = f"App {app_id}"
            raw_reviews, warnings = await collect_reviews(
                request.app_url, max_reviews=request.max_reviews
            )

            yield sse_event("collect", "completed", {
                "message": f"Collected {len(raw_reviews)} reviews",
                "progress": 15, "count": len(raw_reviews), "warnings": warnings,
            })

            if not raw_reviews:
                yield sse_event("complete", "completed", {
                    "message": "No reviews collected.", "progress": 100
                })
                return

            # Stage 2: Clean
            yield sse_event("clean", "running", {
                "message": "Cleaning and deduplicating...", "progress": 20
            })

            cleaned, stats = clean_reviews(raw_reviews)

            yield sse_event("clean", "completed", {
                "message": f"Kept {stats.get('total_kept')}, removed {stats.get('duplicates_removed')} duplicates",
                "progress": 30, "stats": stats,
            })

            active = [r for r in cleaned if not r.get("is_duplicate")]
            if not active:
                yield sse_event("complete", "completed", {
                    "message": "No reviews remain after cleaning.", "progress": 100
                })
                return

            # Stage 3: Classify
            yield sse_event("classify", "running", {
                "message": "AI topic discovery...", "progress": 35
            })

            try:
                topics = await discover_topics(active, request.goal)
                yield sse_event("classify", "completed", {
                    "message": f"Discovered {len(topics)} topics",
                    "progress": 50,
                    "topics": [{"topic_name": t.get("topic_name"),
                                "review_count": len(t.get("review_ids", [])),
                                "primary_sentiment": t.get("primary_sentiment")}
                              for t in topics],
                })
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                yield sse_event("classify", "failed", {
                    "message": f"Classification error: {e}", "progress": 50
                })
                topics = []

            # Stage 4: Analyze
            yield sse_event("analyze", "running", {
                "message": "Generating findings...", "progress": 55
            })

            try:
                findings = await analyze_findings(topics, active, request.goal)
                yield sse_event("analyze", "completed", {
                    "message": f"{len(findings)} findings generated",
                    "progress": 65,
                    "findings": [{"title": f.get("title"), "severity": f.get("severity"),
                                  "confidence": f.get("confidence"),
                                  "supporting_count": len(f.get("supporting_review_ids", []))}
                                for f in findings],
                })
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                yield sse_event("analyze", "failed", {
                    "message": f"Analysis error: {e}", "progress": 65
                })
                findings = []

            # Stage 5: PRD
            yield sse_event("prd", "running", {
                "message": "Generating PRD...", "progress": 70
            })

            try:
                prd_data = await generate_prd(findings, topics, active, app_name, app_id, request.goal)
                v_count = len(prd_data.get("versions", []))
                r_count = sum(len(v.get("requirements", [])) for v in prd_data.get("versions", []))
                yield sse_event("prd", "completed", {
                    "message": f"PRD: {v_count} versions, {r_count} requirements",
                    "progress": 80,
                })
            except Exception as e:
                logger.error(f"PRD failed: {e}")
                yield sse_event("prd", "failed", {"message": f"PRD error: {e}", "progress": 80})
                prd_data = {"executive_summary": "", "versions": [], "data_notes": "", "limitations": []}

            # Stage 6: Tests
            yield sse_event("tests", "running", {
                "message": "Generating test cases...", "progress": 85
            })

            try:
                tests = await generate_test_cases(prd_data, findings, active)
                yield sse_event("tests", "completed", {
                    "message": f"{len(tests)} test cases generated",
                    "progress": 92, "count": len(tests),
                })
            except Exception as e:
                logger.error(f"Test gen failed: {e}")
                yield sse_event("tests", "failed", {"message": f"Test error: {e}", "progress": 92})
                tests = []

            # Stage 7: Validate
            yield sse_event("validate", "running", {
                "message": "Validating traceability...", "progress": 95
            })

            validation = validate_traceability(findings, prd_data, tests, active)

            yield sse_event("validate", "completed", {
                "message": f"Validation complete: {len(validation.get('issues', []))} issues",
                "progress": 98, "validation": validation,
            })

            # Done
            yield sse_event("complete", "completed", {
                "message": "Analysis complete!", "progress": 100,
            })

        except Exception as e:
            logger.error(f"Pipeline error: {traceback.format_exc()}")
            yield sse_event("error", "failed", {
                "message": f"Pipeline error: {e}", "progress": 0,
            })

    return EventSourceResponse(event_stream())
