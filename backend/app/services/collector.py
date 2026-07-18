"""App Store RSS feed review collector.

Data source: Apple's official iTunes RSS feed (not page scraping).
Endpoint: https://itunes.apple.com/{country}/rss/customerreviews/id{app_id}/xml

Limitations:
- Max ~10 pages, ~50 reviews per page (~500 total)
- Only most recent reviews are available
- XML format (JSON endpoint doesn't support pagination)
- Rate limits: no documented limit, but use with reasonable delays
"""

import re
import httpx
import xml.etree.ElementTree as ET
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_app_id(url: str) -> Optional[str]:
    """Extract numeric app ID from an App Store URL."""
    match = re.search(r'/id(\d{5,})(?:\?|$)', url)
    return match.group(1) if match else None


def parse_review_entry(entry: ET.Element) -> Optional[dict]:
    """Parse a single review entry from the RSS feed XML."""
    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'im': 'http://itunes.apple.com/rss',
    }

    try:
        entry_id = entry.find('atom:id', ns)
        review_id = entry_id.text.strip() if entry_id is not None and entry_id.text else "unknown"

        rating_el = entry.find('im:rating', ns)
        rating = int(rating_el.text.strip()) if rating_el is not None and rating_el.text else 0

        title_el = entry.find('atom:title', ns)
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        content_els = entry.findall('atom:content', ns)
        content = ""
        for c in content_els:
            if c.get('type') == 'text' and c.text:
                content = c.text.strip()
                break

        author_el = entry.find('atom:author/atom:name', ns)
        author = author_el.text.strip() if author_el is not None and author_el.text else "Anonymous"

        version_el = entry.find('im:version', ns)
        version = version_el.text.strip() if version_el is not None and version_el.text else None

        date_str = ""
        updated_el = entry.find('atom:updated', ns)
        if updated_el is not None and updated_el.text:
            date_str = updated_el.text.strip()

        return {
            "id": review_id,
            "rating": rating,
            "title": title,
            "content": content,
            "author": author,
            "version": version,
            "date": date_str,
        }
    except Exception as e:
        logger.warning(f"Failed to parse review entry: {e}")
        return None


async def collect_reviews(
    app_url: str,
    country: str = "us",
    max_reviews: int = 500,
) -> tuple[list[dict], list[str]]:
    """Collect reviews from the App Store RSS feed.

    Returns (reviews, warnings).
    """
    app_id = extract_app_id(app_url)
    if not app_id:
        return [], [f"Could not extract app ID from URL: {app_url}"]

    reviews = []
    warnings = []
    xml_base = (
        f"https://itunes.apple.com/{country}/rss/customerreviews"
        f"/id{app_id}/sortBy=mostRecent/xml"
    )

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for page in range(1, 11):
            if len(reviews) >= max_reviews:
                break

            url = f"{xml_base}?page={page}"
            try:
                response = await client.get(url)
                if response.status_code == 400:
                    break  # No more pages
                if response.status_code != 200:
                    warnings.append(f"Page {page}: HTTP {response.status_code}")
                    break

                root = ET.fromstring(response.text)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('atom:entry', ns)

                if not entries:
                    break

                for entry in entries:
                    if len(reviews) >= max_reviews:
                        break
                    parsed = parse_review_entry(entry)
                    if parsed and parsed["content"]:
                        reviews.append(parsed)

                logger.info(f"Page {page}: {len(entries)} entries, total: {len(reviews)}")

            except ET.ParseError as e:
                warnings.append(f"Page {page}: XML parse error: {e}")
                break
            except httpx.TimeoutException:
                warnings.append(f"Page {page}: Request timeout")
                break

    if len(reviews) >= max_reviews:
        warnings.append(f"Reached max review limit ({max_reviews}).")

    return reviews, warnings
