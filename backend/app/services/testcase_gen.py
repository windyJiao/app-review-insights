"""AI-powered test case generation from PRD requirements.

Why LLM:
- Must design concrete test steps from abstract requirements
- Edge cases require understanding of potential failure modes
- Test preconditions and expected results need domain context
- Traceability back to user reviews ensures test relevance
"""

import json
import logging
from ..utils.llm import structured_completion

logger = logging.getLogger(__name__)

TEST_CASES_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "preconditions": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    },
                    "expected_result": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["P0", "P1", "P2", "P3"]
                    },
                    "linked_req_id": {"type": "string"},
                    "linked_review_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "test_type": {
                        "type": "string",
                        "enum": ["functional", "edge_case", "regression",
                                 "performance", "usability"]
                    }
                },
                "required": ["title", "description", "preconditions", "steps",
                           "expected_result", "priority", "linked_req_id",
                           "linked_review_ids", "test_type"]
            }
        }
    },
    "required": ["test_cases"]
}


async def generate_test_cases(
    prd: dict,
    findings: list[dict],
    reviews: list[dict],
) -> list[dict]:
    """Generate test cases for each requirement in the PRD."""
    versions = prd.get("versions", [])
    if not versions:
        return []

    all_requirements = []
    for v in versions:
        for i, req in enumerate(v.get("requirements", [])):
            req_copy = dict(req)
            req_copy["version_name"] = v.get("version_name", "")
            req_copy["req_index"] = i
            all_requirements.append(req_copy)

    if not all_requirements:
        return []

    prompt = f"""Generate test cases for each requirement. Each test must trace to user reviews.

Requirements:
{json.dumps(all_requirements, indent=2)}

Findings context:
{json.dumps([{
    "index": f.get("finding_index", i),
    "title": f.get("title", ""),
    "description": f.get("description", ""),
    "supporting_review_ids": f.get("supporting_review_ids", []),
    "supporting_excerpts": f.get("supporting_excerpts", []),
} for i, f in enumerate(findings)], indent=2)}

Generate tests that:
1. Verify each requirement is correctly implemented
2. Include functional, edge case, and regression tests
3. Have clear preconditions, steps, and expected results
4. Link to the requirement (linked_req_id = req_index)
5. Link to original review IDs that motivated the requirement
6. Are practical and executable by a QA tester

Rules:
- 1-4 tests per requirement
- Every test must have linked_review_ids
- Test steps must be specific and actionable
- Consider the original user complaint when designing edge cases"""

    try:
        result = await structured_completion(
            system_prompt="QA engineer writing test cases. Each test executable and traceable to user feedback. Clear steps a manual tester can follow.",
            user_message=prompt,
            json_schema=TEST_CASES_SCHEMA,
            temperature=0.2,
        )
        tests = result.get("test_cases", [])
        logger.info(f"Generated {len(tests)} test cases")
        return tests
    except Exception as e:
        logger.error(f"Test case generation failed: {e}")
        return []
