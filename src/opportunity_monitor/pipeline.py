from __future__ import annotations

import hashlib

from .classifier import Classifier
from .collectors import CollectorError, SourceCollector
from .dedupe import deduplicate
from .ledger import HealthLedger
from .models import OpportunityRecord, PipelineResult
from .normalization import canonicalize_url


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class OpportunityPipeline:
    def __init__(
        self,
        collectors: list[SourceCollector],
        classifier: Classifier,
        ledger: HealthLedger | None = None,
        review_threshold: float = 0.72,
    ) -> None:
        self.collectors = collectors
        self.classifier = classifier
        self.ledger = ledger or HealthLedger()
        self.review_threshold = review_threshold

    def run(self) -> PipelineResult:
        raw_items = []
        for collector in self.collectors:
            try:
                items = collector.collect()
            except CollectorError as exc:
                self.ledger.record_failure(collector.source_id, str(exc))
                continue

            self.ledger.record_success(collector.source_id, len(items))
            raw_items.extend(items)

        records: list[OpportunityRecord] = []
        review_queue: list[str] = []

        for candidate in deduplicate(raw_items):
            item = candidate.primary
            classification = self.classifier.classify(item)
            canonical_key = canonicalize_url(str(item.url))
            canonical_id = hashlib.sha256(
                canonical_key.encode("utf-8")
            ).hexdigest()[:20]
            review_required = classification.confidence < self.review_threshold
            if review_required:
                review_queue.append(canonical_id)

            records.append(
                OpportunityRecord(
                    canonical_id=canonical_id,
                    title=item.title,
                    category=classification.category,
                    priority=classification.priority,
                    summary=classification.summary,
                    relevance_reason=classification.relevance_reason,
                    confidence=classification.confidence,
                    review_required=review_required,
                    deadline=item.deadline,
                    discovered_at=item.discovered_at,
                    source_ids=sorted(candidate.source_ids),
                    source_urls=sorted(candidate.source_urls),
                )
            )

        records.sort(
            key=lambda record: (
                PRIORITY_ORDER[record.priority],
                record.deadline is None,
                record.deadline,
                record.title.lower(),
            )
        )
        return PipelineResult(
            records=records,
            source_health=self.ledger.snapshot(),
            review_queue=review_queue,
        )
