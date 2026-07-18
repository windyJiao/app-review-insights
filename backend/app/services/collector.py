"""App Store review collector.

Extracts review data embedded in the App Store product page HTML.
Apple embeds review JSON objects in the page source for initial render.
"""

import re
import json
import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def extract_app_id(url: str) -> Optional[str]:
    match = re.search(r'/id(\d{5,})(?:\?|$)', url)
    return match.group(1) if match else None


def extract_country(url: str) -> str:
    match = re.search(r'apple\.com/([a-z]{2})/', url)
    return match.group(1) if match else "us"


def _parse_reviews_from_html(html: str) -> list[dict]:
    """Extract review objects from the App Store page HTML.

    Reviews are embedded as JSON objects with '$kind':'Review' in the page's
    shelf data, which is rendered server-side for SEO and initial display.
    """
    reviews = []
    seen_ids = set()

    # Pattern: find all {"$kind":"Review", ...} JSON objects
    # These are embedded in the page's shelf/items arrays
    pattern = r'\{\"\$kind\":\"Review\",\"id\":\"(\d+)\",\"title\":\"(.*?)\",\"date\":\"(.*?)\",\"dateText\":\"[^\"]*\",\"contents\":\"(.*?)\",\"rating\":(\d+),\"reviewerName\":\"(.*?)\"'

    for m in re.finditer(pattern, html, re.DOTALL):
        review_id = m.group(1)
        if review_id in seen_ids:
            continue
        seen_ids.add(review_id)

        # Unescape JSON strings
        title = m.group(2).replace('\\"', '"').replace('\\\\', '\\')
        content = m.group(4).replace('\\"', '"').replace('\\\\', '\\')
        reviewer = m.group(6).replace('\\"', '"').replace('\\\\', '\\')

        reviews.append({
            "id": review_id,
            "rating": int(m.group(5)),
            "title": title,
            "content": content,
            "author": reviewer,
            "version": None,
            "date": m.group(3),
        })

    return reviews


async def collect_reviews(
    app_url: str,
    country: str = "us",
    max_reviews: int = 500,
) -> tuple[list[dict], list[str]]:
    """Collect reviews from the App Store product page.

    Returns (reviews, warnings).
    """
    app_id = extract_app_id(app_url)
    if not app_id:
        return [], [f"Could not extract app ID from URL: {app_url}"]

    warnings = []

    # Build the product page URL
    page_url = f"https://apps.apple.com/{country}/app/id{app_id}"
    logger.info(f"Fetching reviews from: {page_url}")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(
                page_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            if response.status_code != 200:
                warnings.append(f"HTTP {response.status_code} from {page_url}")
                return [], warnings

            reviews = _parse_reviews_from_html(response.text)
            reviews = reviews[:max_reviews]
            logger.info(f"Extracted {len(reviews)} reviews from page HTML")

            for r in reviews:
                logger.info(f"  [{r['rating']}★] {r['title']} — {r['content'][:80]}...")

            if not reviews:
                warnings.append("No review data found in page HTML.")

        except Exception as e:
            warnings.append(f"Fetch error: {e}")
            return [], warnings

    return reviews, warnings
