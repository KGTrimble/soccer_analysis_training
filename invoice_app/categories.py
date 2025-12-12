from __future__ import annotations

from dataclasses import dataclass


MARKETING_COST_CATEGORIES: list[str] = [
    "Advertising",
    "Paid Search",
    "Paid Social",
    "Content / SEO",
    "Events",
    "Sponsorships",
    "PR / Comms",
    "Agency / Contractors",
    "Tools / Software",
    "Print / Swag",
    "Other",
]


@dataclass(frozen=True)
class CategorySuggestion:
    category: str
    score: int
    matched_keywords: tuple[str, ...]


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Advertising": (
        "advertising",
        "display ads",
        "cpm",
        "cpc",
        "media buy",
        "programmatic",
    ),
    "Paid Search": (
        "google ads",
        "adwords",
        "bing ads",
        "microsoft advertising",
        "paid search",
        "search ads",
    ),
    "Paid Social": (
        "facebook ads",
        "meta ads",
        "instagram ads",
        "linkedin ads",
        "tiktok ads",
        "twitter ads",
        "x ads",
        "paid social",
    ),
    "Content / SEO": (
        "seo",
        "content",
        "copywriting",
        "blog",
        "backlinks",
        "keyword research",
    ),
    "Events": (
        "event",
        "conference",
        "booth",
        "exhibition",
        "sponsorship package",
        "registration",
        "venue",
        "catering",
    ),
    "Sponsorships": (
        "sponsor",
        "sponsorship",
        "partner package",
    ),
    "PR / Comms": (
        "press release",
        "pr",
        "public relations",
        "media relations",
    ),
    "Agency / Contractors": (
        "agency",
        "retainer",
        "consulting",
        "contractor",
        "freelance",
        "services rendered",
    ),
    "Tools / Software": (
        "subscription",
        "license",
        "saas",
        "software",
        "platform fee",
        "monthly plan",
        "annual plan",
    ),
    "Print / Swag": (
        "print",
        "printing",
        "swag",
        "merch",
        "stickers",
        "brochures",
        "flyers",
        "business cards",
    ),
}


def suggest_marketing_category(text: str) -> CategorySuggestion:
    """
    Suggest a marketing cost category from invoice text using simple keyword scoring.

    This is intentionally deterministic/offline; users can override in the UI.
    """
    normalized = (text or "").lower()

    best_category = "Other"
    best_score = 0
    best_matches: tuple[str, ...] = ()

    for category, keywords in _CATEGORY_KEYWORDS.items():
        matches = tuple(k for k in keywords if k in normalized)
        score = len(matches)
        if score > best_score:
            best_category = category
            best_score = score
            best_matches = matches

    return CategorySuggestion(
        category=best_category,
        score=best_score,
        matched_keywords=best_matches,
    )

