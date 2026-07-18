"""AI-powered findings analysis with evidence grounding.

Why LLM:
- Must synthesize patterns across disparate reviews into actionable findings
- Must evaluate evidence strength and assign confidence
- Must identify conflicting feedback — reviews that disagree within same topic
- Cannot be reduced to keyword counting or sentiment scores alone

Every model-generated finding includes:
- Source review IDs and excerpts
- Confidence based on review count and consistency
- Conflicting evidence when reviews disagree
- Uncertainty notes and data limitations
- Statistical evidence (avg rating, distribution) computed deterministically
"""

import json
import logging
from ..utils.llm import structured_completion

logger = logging.getLogger(__name__)

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["bug", "ux_issue", "feature_request", "praise",
                                 "pricing_concern", "performance", "content_quality",
                                 "subscription", "other"]
                    },
                    "description": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Based on review count, clarity, consistency"
                    },
                    "supporting_review_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "supporting_excerpts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "conflicting_review_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "conflicting_excerpts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "uncertainty_notes": {"type": "string"},
                    "data_limitations": {"type": "string"}
                },
                "required": ["title", "category", "description", "severity",
                           "confidence", "supporting_review_ids",
                           "supporting_excerpts", "uncertainty_notes"]
            }
        }
    },
    "required": ["findings"]
}


def compute_topic_stats(topic: dict, reviews: list[dict]) -> dict:
    """Deterministic statistics for a topic — complements model-generated findings."""
    topic_reviews = [r for r in reviews if r["id"] in topic.get("review_ids", [])]
    ratings = [r["rating"] for r in topic_reviews if r.get("rating")]

    if not ratings:
        return {"avg_rating": 0, "mention_count": len(topic_reviews),
                "is_model_generated": True}

    return {
        "avg_rating": round(sum(ratings) / len(ratings), 2),
        "rating_distribution": {str(i): ratings.count(i) for i in range(1, 6)},
        "mention_count": len(topic_reviews),
        "is_model_generated": True,
    }


async def analyze_findings(
    topics: list[dict],
    reviews: list[dict],
    goal: str | None = None,
) -> list[dict]:
    """Generate evidence-grounded findings from topic clusters."""
    if not topics or not reviews:
        return []

    topic_summaries = []
    for t in topics:
        stats = compute_topic_stats(t, reviews)
        topic_reviews = [r for r in reviews if r["id"] in t.get("review_ids", [])]
        review_details = [{
            "id": r["id"],
            "rating": r["rating"],
            "title": r.get("title", ""),
            "content": r["content"][:200],
            "date": r.get("date", ""),
        } for r in topic_reviews[:10]]

        topic_summaries.append({
            "topic_name": t["topic_name"],
            "description": t.get("description", ""),
            "primary_sentiment": t.get("primary_sentiment", "neutral"),
            "review_count": len(t.get("review_ids", [])),
            "avg_rating": stats["avg_rating"],
            "rating_distribution": stats["rating_distribution"],
            "keywords": t.get("keywords", []),
            "sample_reviews": review_details,
            "representative_excerpts": t.get("representative_excerpts", []),
        })

    goal_context = f"\nAnalysis goal: {goal}\nPrioritize findings relevant to this goal." if goal else ""

    prompt = f"""Generate evidence-grounded findings from these topic clusters.{goal_context}

For each topic, generate findings that:
1. Identify specific user problems or positive patterns
2. Include supporting review IDs and direct quotes
3. Note conflicting reviews that disagree
4. Assess confidence based on evidence strength
5. Note data limitations and uncertainty

Rules:
- Every finding MUST have real supporting review IDs (don't fabricate)
- <3 supporting reviews = low confidence
- Reviews within a topic that disagree = note as conflicting
- Be specific ("Video download fails on iOS 17.4" not "Video problems")

Topics:
{json.dumps(topic_summaries, indent=2)}"""

    try:
        result = await structured_completion(
            system_prompt="Senior product analyst. Generate findings grounded in evidence. Never fabricate data. Distinguish between what data shows and what you infer. When evidence is thin, say so.",
            user_message=prompt,
            json_schema=FINDINGS_SCHEMA,
            temperature=0.2,
        )
        findings = result.get("findings", [])
        logger.info(f"Generated {len(findings)} findings")
        return findings
    except Exception as e:
        logger.error(f"Findings analysis failed: {e}")
        return []
