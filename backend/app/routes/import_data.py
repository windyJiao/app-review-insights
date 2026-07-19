"""Data import endpoint — supports JSON and CSV review datasets with SSE streaming."""

import json
import csv
import io
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from starlette.responses import StreamingResponse

from ..services.cleaner import clean_reviews
from ..services.classifier import discover_topics
from ..services.analyzer import analyze_findings
from ..services.prd_generator import generate_prd
from ..services.testcase_gen import generate_test_cases
from ..services.validator import validate_traceability

logger = logging.getLogger(__name__)
router = APIRouter()


def format_sse(stage: str, status: str, payload: dict) -> str:
    """Format a dict as an SSE event string."""
    payload["stage"] = stage
    payload["status"] = status
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return f"event: {stage}\ndata: {json.dumps(payload, default=str)}\n\n"


def parse_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    reviews = []
    for row in reader:
        r = {
            "id": row.get("id", row.get("review_id", f"imp-{len(reviews)}")),
            "rating": int(row.get("rating", row.get("score", 0))),
            "title": row.get("title", ""),
            "content": row.get("content", row.get("text", row.get("review", ""))),
            "author": row.get("author", row.get("username", "Anonymous")),
            "version": row.get("version"),
            "date": row.get("date", row.get("timestamp", "")),
        }
        if r["content"]:
            reviews.append(r)
    return reviews


def parse_json(content: str) -> list[dict]:
    data = json.loads(content)
    if isinstance(data, dict):
        if "reviews" in data:
            data = data["reviews"]
        elif "feed" in data:
            entries = data.get("feed", {}).get("entry", [])
            data = []
            for entry in entries:
                if not entry.get("im:name"):
                    data.append({
                        "id": entry.get("id", {}).get("label", f"imp-{len(data)}"),
                        "rating": int(entry.get("im:rating", {}).get("label", 0)),
                        "title": entry.get("title", {}).get("label", ""),
                        "content": entry.get("content", {}).get("label", ""),
                        "author": entry.get("author", {}).get("name", {}).get("label", "Anonymous"),
                        "version": entry.get("im:version", {}).get("label") if entry.get("im:version") else None,
                        "date": entry.get("updated", {}).get("label", ""),
                    })
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of review objects")
    reviews = []
    for item in data:
        r = {
            "id": str(item.get("id", item.get("review_id", f"imp-{len(reviews)}"))),
            "rating": int(item.get("rating", item.get("score", 0))),
            "title": str(item.get("title", "")),
            "content": str(item.get("content", item.get("text", item.get("review", "")))),
            "author": str(item.get("author", item.get("username", "Anonymous"))),
            "version": item.get("version"),
            "date": str(item.get("date", item.get("timestamp", ""))),
        }
        if r["content"]:
            reviews.append(r)
    return reviews


@router.post("/import/analyze")
async def analyze_import(
    file: UploadFile = File(...),
    format: str = Form("json"),
    goal: Optional[str] = Form(None),
    app_name: Optional[str] = Form("Imported App"),
    lang: str = Form("en"),
):
    """Import reviews from JSON/CSV and run full analysis with SSE progress streaming."""

    # Parse file upfront — if it's invalid, fail fast with HTTP 400
    content = await file.read()
    text = content.decode("utf-8")

    try:
        raw = parse_csv(text) if format == "csv" else parse_json(text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")

    if not raw:
        raise HTTPException(status_code=400, detail="No valid reviews found")

    async def event_stream():
        try:
            # Stage 1: Collect (file already parsed — report what we got)
            yield format_sse("collect", "completed", {
                "message": f"Parsed {len(raw)} reviews from uploaded file",
                "progress": 15, "count": len(raw),
            })

            # Stage 2: Clean
            yield format_sse("clean", "running", {
                "message": "Cleaning and deduplicating...", "progress": 20
            })

            cleaned, stats = clean_reviews(raw)

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
                topics = await discover_topics(active, goal, lang)
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
                findings = await analyze_findings(topics, active, goal, lang)
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
                prd_data = await generate_prd(findings, topics, active, app_name, "imported", goal, lang)
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
                tests = await generate_test_cases(prd_data or {}, findings, active, lang)
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
                "cleaned_reviews": active,
                "cleaning_stats": stats,
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
