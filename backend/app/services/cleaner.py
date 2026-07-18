"""Review data cleaning and deduplication.

Why deterministic rules:
- Exact dedup: MD5 hashing is fast, reliable, and reproducible
- Near-duplicate detection: n-gram Jaccard similarity catches copy-paste variants
- Quality flagging: heuristic rules (length, char patterns) are interpretable
- Language detection: Unicode range analysis is deterministic and fast

Not using LLM here because:
- Dedup is a well-defined problem with exact solutions
- Quality flags need consistent, explainable thresholds
- Much faster and cheaper than calling an API for every review
"""

import re
import hashlib
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize for comparison: lowercase, collapse whitespace, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()


def detect_language(text: str) -> str:
    """Simple language detection via Unicode range analysis."""
    cjk = len(re.findall(r'[一-鿿]', text))
    hiragana = len(re.findall(r'[぀-ゟ]', text))
    katakana = len(re.findall(r'[゠-ヿ]', text))
    hangul = len(re.findall(r'[가-힯]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))

    total_chars = len(text.replace(' ', ''))
    if total_chars == 0:
        return "unknown"
    if cjk / total_chars > 0.3:
        return "zh"
    if hiragana + katakana > 5:
        return "ja"
    if hangul / total_chars > 0.3:
        return "ko"
    if latin / max(total_chars, 1) > 0.5:
        return "en-latin"
    return "unknown"


def flag_quality(content: str) -> str:
    """Flag review quality using heuristics."""
    text = content.strip()
    length = len(text)

    if length < 10:
        return "short"
    if length < 20 and not any(c.isalpha() for c in text):
        return "non_informative"

    url_count = len(re.findall(r'https?://', text))
    repeated = len(re.findall(r'(.)\1{4,}', text))
    emoji_ratio = len(re.findall(r'[\U0001F300-\U0001F9FF]', text)) / max(length, 1)

    if url_count > 2 or repeated > 3:
        return "spam_like"
    if emoji_ratio > 0.5:
        return "non_informative"
    return "ok"


def compute_similarity(a: str, b: str) -> float:
    """Jaccard similarity of word n-grams.

    Uses word bigrams for short texts (<5 words), trigrams for longer.
    Word-level comparison is more robust than character n-grams for
    detecting near-duplicate review content across varying lengths.
    """
    words_a = a.split()
    words_b = b.split()
    if not words_a or not words_b:
        return 0.0

    n = 2 if min(len(words_a), len(words_b)) < 5 else 3

    def ngrams(words, n):
        return set(' '.join(words[i:i+n]) for i in range(len(words) - n + 1))

    a_set = ngrams(words_a, n)
    b_set = ngrams(words_b, n)
    if not a_set or not b_set:
        return 0.0

    return len(a_set & b_set) / len(a_set | b_set)


def clean_reviews(
    raw_reviews: list[dict],
    dedup_threshold: float = 0.85,
) -> tuple[list[dict], dict]:
    """Clean and deduplicate reviews.

    Phase 1: Exact dedup via MD5, quality flagging, language detection.
    Phase 2: Near-duplicate detection via n-gram Jaccard similarity.

    Returns (cleaned_reviews, stats).
    """
    stats = {
        "total_raw": len(raw_reviews),
        "duplicates_removed": 0,
        "short_flagged": 0,
        "spam_flagged": 0,
        "non_informative_flagged": 0,
        "language_distribution": defaultdict(int),
        "rating_distribution": defaultdict(int),
    }

    # Phase 1: Normalize and exact dedup
    processed = []
    seen_hashes = set()

    for review in raw_reviews:
        content = review.get("content", "").strip()
        if not content:
            continue

        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in seen_hashes:
            stats["duplicates_removed"] += 1
            continue
        seen_hashes.add(content_hash)

        quality = flag_quality(content)
        lang = detect_language(content)

        cleaned = {
            "id": review.get("id", f"gen-{len(processed)}"),
            "rating": review.get("rating", 0),
            "title": review.get("title", "").strip(),
            "content": content,
            "content_length": len(content),
            "author": review.get("author", "Anonymous"),
            "version": review.get("version"),
            "date": review.get("date", ""),
            "language": lang,
            "is_duplicate": False,
            "duplicate_of": None,
            "quality_flag": quality,
        }
        processed.append(cleaned)

        stats["language_distribution"][lang] += 1
        stats["rating_distribution"][str(review.get("rating", 0))] += 1
        if quality == "short":
            stats["short_flagged"] += 1
        elif quality == "spam_like":
            stats["spam_flagged"] += 1
        elif quality == "non_informative":
            stats["non_informative_flagged"] += 1

    # Phase 2: Near-duplicate detection
    normalized_texts = [normalize_text(r["content"]) for r in processed]

    for i in range(len(processed)):
        if processed[i]["is_duplicate"]:
            continue
        for j in range(i + 1, len(processed)):
            if processed[j]["is_duplicate"]:
                continue
            if abs(processed[i]["rating"] - processed[j]["rating"]) > 1:
                continue
            sim = compute_similarity(normalized_texts[i], normalized_texts[j])
            if sim >= dedup_threshold:
                # Keep the longer review
                if processed[i]["content_length"] >= processed[j]["content_length"]:
                    processed[j]["is_duplicate"] = True
                    processed[j]["duplicate_of"] = processed[i]["id"]
                else:
                    processed[i]["is_duplicate"] = True
                    processed[i]["duplicate_of"] = processed[j]["id"]
                stats["duplicates_removed"] += 1

    stats["language_distribution"] = dict(stats["language_distribution"])
    stats["rating_distribution"] = dict(stats["rating_distribution"])
    stats["total_cleaned"] = len(processed)
    stats["total_kept"] = sum(1 for r in processed if not r["is_duplicate"])

    return processed, stats
