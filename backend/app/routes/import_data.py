"""Data import endpoint — supports JSON and CSV review datasets."""

import json
import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ..services.cleaner import clean_reviews
from ..services.classifier import discover_topics
from ..services.analyzer import analyze_findings
from ..services.prd_generator import generate_prd
from ..services.testcase_gen import generate_test_cases
from ..services.validator import validate_traceability

logger = logging.getLogger(__name__)
router = APIRouter()


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
):
    """Import reviews from JSON/CSV and run full analysis."""
    content = await file.read()
    text = content.decode("utf-8")

    try:
        raw = parse_csv(text) if format == "csv" else parse_json(text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")

    if not raw:
        raise HTTPException(status_code=400, detail="No valid reviews found")

    cleaned, stats = clean_reviews(raw)
    active = [r for r in cleaned if not r.get("is_duplicate")]
    topics = await discover_topics(active, goal)
    findings = await analyze_findings(topics, active, goal)
    prd_data = await generate_prd(findings, topics, active, app_name, "imported", goal)
    tests = await generate_test_cases(prd_data or {}, findings, active)
    validation = validate_traceability(findings, prd_data, tests, active)

    return {
        "raw_reviews": raw,
        "cleaned_reviews": cleaned,
        "cleaning_stats": stats,
        "topic_clusters": topics,
        "findings": findings,
        "prd": prd_data,
        "test_cases": tests,
        "validation": validation,
        "status": "completed",
    }
