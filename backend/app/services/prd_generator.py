"""AI-powered PRD generation with version planning.

Why LLM:
- Synthesizes findings into actionable product requirements
- Version planning requires strategic scope and dependency decisions
- Must distinguish evidence-backed requirements from assumptions
- Requirements must link to source findings for traceability
"""

import json
import logging
from ..utils.llm import structured_completion

logger = logging.getLogger(__name__)

PRD_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "versions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "version_name": {"type": "string"},
                    "description": {"type": "string"},
                    "goal": {"type": "string"},
                    "timeline_estimate": {"type": "string"},
                    "requirements": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "priority": {
                                    "type": "string",
                                    "enum": ["P0", "P1", "P2", "P3"]
                                },
                                "category": {"type": "string"},
                                "source_finding_ids": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "source_review_ids": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "is_assumption": {"type": "boolean"},
                                "assumption_rationale": {"type": "string"}
                            },
                            "required": ["title", "description", "priority",
                                       "category", "source_finding_ids",
                                       "source_review_ids", "is_assumption"]
                        }
                    }
                },
                "required": ["version_name", "description", "goal", "requirements"]
            }
        },
        "data_notes": {"type": "string"},
        "limitations": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["executive_summary", "versions", "data_notes", "limitations"]
}


async def generate_prd(
    findings: list[dict],
    topics: list[dict],
    reviews: list[dict],
    app_name: str,
    app_id: str,
    goal: str | None = None,
    lang: str = "en",
) -> dict:
    """Generate PRD with version planning from findings."""
    if not findings:
        return {
            "executive_summary": "Insufficient findings to generate a PRD.",
            "versions": [],
            "data_notes": "No findings were generated.",
            "limitations": ["No findings available."],
        }

    for i, f in enumerate(findings):
        f["finding_index"] = i

    topic_names = [t["topic_name"] for t in topics]
    goal_context = f"\nPrimary analysis goal: {goal}" if goal else ""
    review_count = len(reviews)

    # Adapt scope to data size
    if review_count < 20:
        version_hint = "Generate exactly 1 version with 2-4 requirements. Be concise."
    elif review_count < 50:
        version_hint = "Generate 1-2 versions with 3-6 requirements total."
    else:
        version_hint = "Generate up to 3 versions."

    prompt = f"""Generate a PRD for "{app_name}" based on user review findings.{goal_context}

App ID: {app_id}
Total reviews: {review_count}
Topics: {', '.join(topic_names)}
{version_hint}

Findings:
{json.dumps(findings, indent=2)}

Rules:
- Every requirement links to source finding IDs
- <5 supporting reviews for a finding -> mark requirement as assumption
- Don't invent features nobody asked for
- If data is too thin for meaningful requirements, say so
- Mark is_assumption=true when not directly evidenced"""

    try:
        lang_inst = "Please respond in Simplified Chinese (简体中文)." if lang == "zh" else ""
        result = await structured_completion(
            system_prompt=f"Senior product manager creating PRD from user research. Every requirement traceable to evidence. Mark assumptions explicitly. {lang_inst}",
            user_message=prompt,
            json_schema=PRD_SCHEMA,
            temperature=0.3,
        )
        logger.info(f"Generated PRD with {len(result.get('versions', []))} versions")
        return result
    except Exception as e:
        logger.error(f"PRD generation failed: {e}")
        return {
            "executive_summary": f"PRD generation failed: {str(e)}",
            "versions": [],
            "data_notes": "Generation error.",
            "limitations": [str(e)],
        }
