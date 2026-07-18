"""AI-powered dynamic topic discovery.

This is the first model-driven semantic task. Why LLM instead of rules:
- Topics vary across app categories — fitness, games, finance all differ
- User analysis goals may target specific themes (subscription, usability)
- Captures nuanced patterns: "paywall frustration" vs "subscription value"
- Handles mixed-language reviews and emergent terminology

Process:
1. Batch reviews for context window limits
2. LLM discovers topics from each batch
3. Merge overlapping topics across batches via a second LLM pass
"""

import json
import logging
from ..utils.llm import structured_completion

logger = logging.getLogger(__name__)

TOPIC_DISCOVERY_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string"},
                    "description": {"type": "string"},
                    "review_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "primary_sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "mixed", "neutral"]
                    },
                    "representative_excerpts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 10
                    }
                },
                "required": ["topic_name", "description", "review_ids",
                           "primary_sentiment", "representative_excerpts", "keywords"]
            }
        }
    },
    "required": ["topics"]
}

TOPIC_MERGE_SCHEMA = {
    "type": "object",
    "properties": {
        "merged_topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string"},
                    "description": {"type": "string"},
                    "merged_from": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "review_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "primary_sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "mixed", "neutral"]
                    },
                    "representative_excerpts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 10
                    }
                },
                "required": ["topic_name", "description", "review_ids",
                           "primary_sentiment", "representative_excerpts", "keywords"]
            }
        }
    },
    "required": ["merged_topics"]
}


async def discover_topics(
    reviews: list[dict],
    goal: str | None = None,
    batch_size: int = 100,
) -> list[dict]:
    """Discover topics from reviews using LLM, batching if needed."""
    all_topics = []
    goal_context = f"\nAnalysis goal: {goal}\nFocus on this goal." if goal else ""

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]

        review_lines = []
        for r in batch:
            content = r["content"][:300].replace('\n', ' ')
            title = r.get("title", "")[:100]
            review_lines.append(
                f"[{r['id']}] Rating: {r['rating']}/5 | {title} | {content}"
            )

        prompt = f"""Analyze these app store reviews and discover distinct topics/themes.{goal_context}

Focus on: recurring complaints or praise, common pain points, feature requests,
technical issues, pricing/subscription sentiment, UX patterns.

Rules:
- Topics must be grounded in specific reviews (include their IDs)
- A review can belong to multiple topics
- Topic names should be specific ("Video Buffering on Cellular" not "Problems")
- If a topic has <2 reviews, merge it into a broader topic
- Capture both positive and negative patterns

Reviews:
{chr(10).join(review_lines)}"""

        try:
            result = await structured_completion(
                system_prompt="You are a product analyst identifying themes in user feedback. Be thorough and specific.",
                user_message=prompt,
                json_schema=TOPIC_DISCOVERY_SCHEMA,
                temperature=0.3,
            )
            batch_topics = result.get("topics", [])
            all_topics.extend(batch_topics)
            logger.info(f"Batch {i//batch_size + 1}: {len(batch_topics)} topics")
        except Exception as e:
            logger.error(f"Topic discovery failed for batch {i}: {e}")
            continue

    if not all_topics:
        return []

    # Merge overlapping topics across batches
    if len(all_topics) > 5:
        merged = await _merge_topics(all_topics, goal)
        return merged

    return all_topics


async def _merge_topics(topics: list[dict], goal: str | None) -> list[dict]:
    """Merge overlapping topics via LLM semantic understanding."""
    topics_json = json.dumps([{
        "topic_name": t["topic_name"],
        "description": t.get("description", ""),
        "review_ids": t.get("review_ids", []),
        "primary_sentiment": t.get("primary_sentiment", "neutral"),
        "keywords": t.get("keywords", []),
    } for t in topics], indent=2)

    goal_context = f"\nAnalysis goal: {goal}" if goal else ""

    try:
        result = await structured_completion(
            system_prompt="Merge overlapping topics from app store review analysis. Combine semantically identical topics.",
            user_message=f"""Merge overlapping topics. Combine those describing the same issue.
Target 5-15 well-defined, specific topics.{goal_context}

Topics:
{topics_json}""",
            json_schema=TOPIC_MERGE_SCHEMA,
            temperature=0.2,
        )
        merged = result.get("merged_topics", topics)
        logger.info(f"Merged {len(topics)} topics -> {len(merged)}")
        return merged
    except Exception as e:
        logger.error(f"Topic merge failed: {e}")
        return topics
