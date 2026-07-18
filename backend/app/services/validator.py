"""Traceability validation — deterministic rules.

Why deterministic:
- Validation checks existence and consistency of references
- Rules are well-defined: finding must have reviews, req must have findings
- No model inference needed for checking links exist
- Results must be deterministic and reproducible
"""

import logging

logger = logging.getLogger(__name__)


def validate_traceability(
    findings: list[dict],
    prd: dict | None,
    test_cases: list[dict],
    reviews: list[dict],
) -> dict:
    """Validate traceability chain: review -> finding -> requirement -> test case."""
    review_ids = {r["id"] for r in reviews}
    finding_ids = set()
    issues = []
    removed_unsupported = []
    revised_findings = []
    marked_assumptions = []

    # --- Validate findings ---
    validated_findings = []
    for i, f in enumerate(findings):
        fid = f.get("finding_index", i)
        finding_ids.add(str(fid))

        supporting = f.get("supporting_review_ids", [])
        valid_supporting = [rid for rid in supporting if rid in review_ids]

        if not valid_supporting:
            issues.append(
                f"Finding '{f.get('title', f'#{fid}')}' has no valid supporting reviews — removed"
            )
            removed_unsupported.append(f.get("title", str(fid)))
            continue

        f["supporting_review_ids"] = valid_supporting
        f["supporting_review_count"] = len(valid_supporting)

        if len(valid_supporting) < 3:
            f["confidence"] = min(f.get("confidence", 0.5), 0.4)
            f["data_limitations"] = (
                f.get("data_limitations", "") +
                f" Only {len(valid_supporting)} review(s) support this."
            )

        validated_findings.append(f)
        findings[:] = validated_findings

    # --- Validate PRD requirements ---
    total_requirements = 0
    fully_traced = 0
    partially_traced = 0

    if prd and prd.get("versions"):
        for v in prd["versions"]:
            for j, req in enumerate(v.get("requirements", [])):
                total_requirements += 1
                src_findings = req.get("source_finding_ids", [])
                src_reviews = req.get("source_review_ids", [])

                valid_f = [fid for fid in src_findings if str(fid) in finding_ids]
                valid_r = [rid for rid in src_reviews if rid in review_ids]

                if not valid_f and not req.get("is_assumption"):
                    req["is_assumption"] = True
                    req["assumption_rationale"] = "此需求缺乏直接评论证据，属于 AI 推断。"
                    revised_findings.append({
                        "req": req.get("title", f"req-{j}"),
                        "change": "Marked as assumption (no finding traceability)",
                    })
                    marked_assumptions.append(req.get("title", f"req-{j}"))

                req["source_finding_ids"] = valid_f
                req["source_review_ids"] = valid_r

                if valid_f and valid_r:
                    fully_traced += 1
                elif valid_f or valid_r:
                    partially_traced += 1

    # --- Validate test cases ---
    req_ids_set = set()
    if prd and prd.get("versions"):
        for v in prd["versions"]:
            for j, _ in enumerate(v.get("requirements", [])):
                req_ids_set.add(str(j))

    tests_linked = 0
    orphan_tests = 0

    for tc in test_cases:
        linked_reviews = tc.get("linked_review_ids", [])
        valid_reviews = [rid for rid in linked_reviews if rid in review_ids]
        tc["linked_review_ids"] = valid_reviews
        if valid_reviews:
            tests_linked += 1
        if tc.get("linked_req_id", "") not in req_ids_set and req_ids_set:
            orphan_tests += 1

    return {
        "total_findings": len(findings),
        "total_requirements": total_requirements,
        "total_tests": len(test_cases),
        "findings_with_support": len(validated_findings),
        "findings_without_support": len(removed_unsupported),
        "requirements_fully_traced": fully_traced,
        "requirements_partially_traced": partially_traced,
        "tests_linked_to_reviews": tests_linked,
        "orphan_tests": orphan_tests,
        "removed_unsupported_findings": removed_unsupported,
        "revised_findings": revised_findings,
        "marked_assumptions": marked_assumptions,
        "issues": issues,
    }
