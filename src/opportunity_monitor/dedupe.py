from __future__ import annotations

from dataclasses import dataclass, field

from .models import RawOpportunity
from .normalization import canonicalize_url, token_similarity


@dataclass
class CanonicalCandidate:
    primary: RawOpportunity
    source_ids: set[str] = field(default_factory=set)
    source_urls: set[str] = field(default_factory=set)

    @classmethod
    def from_item(cls, item: RawOpportunity) -> "CanonicalCandidate":
        return cls(
            primary=item,
            source_ids={item.source_id},
            source_urls={str(item.url)},
        )

    def merge(self, item: RawOpportunity) -> None:
        self.source_ids.add(item.source_id)
        self.source_urls.add(str(item.url))
        if len(item.content) > len(self.primary.content):
            self.primary = item


def _same_opportunity(
    candidate: CanonicalCandidate,
    item: RawOpportunity,
    similarity_threshold: float,
) -> bool:
    if canonicalize_url(str(candidate.primary.url)) == canonicalize_url(str(item.url)):
        return True

    if candidate.primary.deadline != item.deadline:
        return False

    return (
        token_similarity(candidate.primary.title, item.title)
        >= similarity_threshold
    )


def deduplicate(
    items: list[RawOpportunity],
    similarity_threshold: float = 0.7,
) -> list[CanonicalCandidate]:
    candidates: list[CanonicalCandidate] = []
    for item in sorted(items, key=lambda value: value.discovered_at):
        match = next(
            (
                candidate
                for candidate in candidates
                if _same_opportunity(candidate, item, similarity_threshold)
            ),
            None,
        )
        if match is None:
            candidates.append(CanonicalCandidate.from_item(item))
        else:
            match.merge(item)
    return candidates

