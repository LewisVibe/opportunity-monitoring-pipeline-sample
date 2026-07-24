from __future__ import annotations

from datetime import date
from typing import Protocol

from .models import Classification, RawOpportunity


class Classifier(Protocol):
    def classify(self, item: RawOpportunity) -> Classification:
        """Return a validated classification for one opportunity."""


CATEGORY_KEYWORDS = {
    "event": {"award", "conference", "speaker", "speaking", "summit"},
    "tender": {"procurement", "rfp", "tender"},
    "grant": {"funding", "grant"},
    "partnership": {"collaboration", "partner", "partnership"},
}
THEME_KEYWORDS = {
    "circular",
    "climate",
    "decarbonisation",
    "decarbonization",
    "esg",
    "regenerative",
    "sustainability",
    "waste",
}


class RuleClassifier:
    def __init__(self, reference_date: date, review_threshold: float = 0.72):
        self.reference_date = reference_date
        self.review_threshold = review_threshold

    def classify(self, item: RawOpportunity) -> Classification:
        title = item.title.lower()
        haystack = f"{title} {item.content}".lower()
        category = "other"

        # Strong title signals win before broader body-text matches. This keeps
        # an event about procurement from being mislabeled as a tender.
        for candidate, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in title for keyword in keywords):
                category = candidate
                break
        if category == "other":
            for candidate, keywords in CATEGORY_KEYWORDS.items():
                if any(keyword in haystack for keyword in keywords):
                    category = candidate
                    break

        theme_matches = sorted(
            keyword for keyword in THEME_KEYWORDS if keyword in haystack
        )
        has_category = category != "other"

        if has_category and theme_matches:
            confidence = 0.92
            reason = (
                f"Matches {category} language and the theme"
                f" {', '.join(theme_matches[:3])}."
            )
        elif has_category or theme_matches:
            confidence = 0.64
            reason = "Some relevant signals were found, but the match needs review."
        else:
            confidence = 0.38
            reason = "No strong opportunity category or target-theme match was found."

        priority = "low"
        if confidence >= self.review_threshold:
            priority = "medium"
            if item.deadline is not None:
                days_remaining = (item.deadline - self.reference_date).days
                if 0 <= days_remaining <= 14:
                    priority = "high"

        summary = " ".join(item.content.split())
        if len(summary) > 180:
            summary = summary[:177].rstrip() + "..."

        return Classification(
            category=category,
            priority=priority,
            summary=summary,
            relevance_reason=reason,
            confidence=confidence,
        )
