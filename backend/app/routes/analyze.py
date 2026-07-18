"""Main analysis route with SSE progress streaming."""

import json
import logging
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from ..models.schemas import AnalysisRequest
from ..services.collector import collect_reviews, extract_app_id, extract_country
from ..services.cleaner import clean_reviews
from ..services.classifier import discover_topics
from ..services.analyzer import analyze_findings
from ..services.prd_generator import generate_prd
from ..services.testcase_gen import generate_test_cases
from ..services.validator import validate_traceability

logger = logging.getLogger(__name__)

router = APIRouter()


def format_sse(stage: str, status: str, payload: dict) -> str:
    """Format a dict as an SSE event string (manual, no library dependency)."""
    payload["stage"] = stage
    payload["status"] = status
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return f"event: {stage}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.post("/analyze")
async def analyze_stream(request: AnalysisRequest):
    """Run analysis with SSE progress streaming."""

    async def event_stream():
        try:
            # Stage 1: Collect
            yield format_sse("collect", "running", {
                "message": "Extracting app ID and collecting reviews...", "progress": 0
            })

            app_id = extract_app_id(request.app_url)
            if not app_id:
                yield format_sse("collect", "failed",
                    {"message": "Could not extract app ID from URL", "progress": 0})
                return

            app_name = f"App {app_id}"
            country = extract_country(request.app_url)
            raw_reviews, warnings = await collect_reviews(
                request.app_url, country=country, max_reviews=request.max_reviews
            )

            yield format_sse("collect", "completed", {
                "message": f"Collected {len(raw_reviews)} reviews",
                "progress": 15, "count": len(raw_reviews), "warnings": warnings,
            })

            if not raw_reviews:
                yield format_sse("complete", "completed", {
                    "message": "No reviews collected.", "progress": 100
                })
                return

            # Stage 2: Clean
            yield format_sse("clean", "running", {
                "message": "Cleaning and deduplicating...", "progress": 20
            })

            cleaned, stats = clean_reviews(raw_reviews)

            yield format_sse("clean", "completed", {
                "message": f"Kept {stats.get('total_kept')}, removed {stats.get('duplicates_removed')} duplicates",
                "progress": 30, "stats": stats,
            })

            active = [r for r in cleaned if not r.get("is_duplicate")]
            if not active:
                yield format_sse("complete", "completed", {
                    "message": "No reviews remain after cleaning.", "progress": 100
                })
                return

            # Stage 3: Classify
            yield format_sse("classify", "running", {
                "message": "AI topic discovery...", "progress": 35
            })

            try:
                topics = await discover_topics(active, request.goal)
                yield format_sse("classify", "completed", {
                    "message": f"Discovered {len(topics)} topics",
                    "progress": 50,
                    "topics": [{"topic_name": t.get("topic_name"),
                                "review_count": len(t.get("review_ids", [])),
                                "primary_sentiment": t.get("primary_sentiment")}
                              for t in topics],
                })
            except Exception as e:
                logger.error(f"Classification failed: {e}")
                yield format_sse("classify", "failed", {
                    "message": f"Classification error: {e}", "progress": 50
                })
                topics = []

            # Stage 4: Analyze
            yield format_sse("analyze", "running", {
                "message": "Generating findings...", "progress": 55
            })

            try:
                findings = await analyze_findings(topics, active, request.goal)
                yield format_sse("analyze", "completed", {
                    "message": f"{len(findings)} findings generated",
                    "progress": 65,
                    "findings": [{"title": f.get("title"), "severity": f.get("severity"),
                                  "confidence": f.get("confidence"),
                                  "supporting_count": len(f.get("supporting_review_ids", []))}
                                for f in findings],
                })
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                yield format_sse("analyze", "failed", {
                    "message": f"Analysis error: {e}", "progress": 65
                })
                findings = []

            # Stage 5: PRD
            yield format_sse("prd", "running", {
                "message": "Generating PRD...", "progress": 70
            })

            try:
                prd_data = await generate_prd(findings, topics, active, app_name, app_id, request.goal)
                v_count = len(prd_data.get("versions", []))
                r_count = sum(len(v.get("requirements", [])) for v in prd_data.get("versions", []))
                yield format_sse("prd", "completed", {
                    "message": f"PRD: {v_count} versions, {r_count} requirements",
                    "progress": 80,
                })
            except Exception as e:
                logger.error(f"PRD failed: {e}")
                yield format_sse("prd", "failed", {"message": f"PRD error: {e}", "progress": 80})
                prd_data = {"executive_summary": "", "versions": [], "data_notes": "", "limitations": []}

            # Stage 6: Tests
            yield format_sse("tests", "running", {
                "message": "Generating test cases...", "progress": 85
            })

            try:
                tests = await generate_test_cases(prd_data, findings, active)
                yield format_sse("tests", "completed", {
                    "message": f"{len(tests)} test cases generated",
                    "progress": 92, "count": len(tests),
                })
            except Exception as e:
                logger.error(f"Test gen failed: {e}")
                yield format_sse("tests", "failed", {"message": f"Test error: {e}", "progress": 92})
                tests = []

            # Stage 7: Validate
            yield format_sse("validate", "running", {
                "message": "Validating traceability...", "progress": 95
            })

            validation = validate_traceability(findings, prd_data, tests, active)

            yield format_sse("validate", "completed", {
                "message": f"Validation complete: {len(validation.get('issues', []))} issues",
                "progress": 98, "validation": validation,
            })

            # Done — pass full results
            yield format_sse("complete", "completed", {
                "message": "Analysis complete!",
                "progress": 100,
                "findings": findings,
                "topic_clusters": topics,
                "prd": prd_data,
                "test_cases": tests,
                "validation": validation,
            })

        except Exception as e:
            logger.error(f"Pipeline error: {traceback.format_exc()}")
            yield format_sse("error", "failed", {
                "message": f"Pipeline error: {e}", "progress": 0,
            })

    return StreamingResponse(event_stream(), media_type="text/event-stream")
