from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from opportunity_monitor.classifier import RuleClassifier
from opportunity_monitor.collectors import (
    FixtureNewsletterCollector,
    FixtureWebCollector,
)
from opportunity_monitor.dedupe import deduplicate
from opportunity_monitor.digest import render_markdown_digest
from opportunity_monitor.ledger import HealthLedger
from opportunity_monitor.models import RawOpportunity
from opportunity_monitor.normalization import canonicalize_url, token_similarity
from opportunity_monitor.pipeline import OpportunityPipeline


REFERENCE_DATE = date(2026, 7, 24)


def raw(
    *,
    source_id: str = "source-a",
    source_kind: str = "web",
    url: str = "https://example.test/item",
    title: str = "Circular economy grant",
    content: str = "Funding for a circular economy and waste project.",
    deadline: date | None = date(2026, 8, 1),
) -> RawOpportunity:
    return RawOpportunity(
        source_id=source_id,
        source_kind=source_kind,
        url=url,
        title=title,
        content=content,
        discovered_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        deadline=deadline,
    )


def write_fixture(path: Path, items: list[RawOpportunity]) -> None:
    path.write_text(
        json.dumps([item.model_dump(mode="json") for item in items]),
        encoding="utf-8",
    )


def pipeline_for(tmp_path: Path, web_items: list[RawOpportunity]):
    fixture = tmp_path / "web.json"
    write_fixture(fixture, web_items)
    return OpportunityPipeline(
        collectors=[FixtureWebCollector(web_items[0].source_id, fixture)],
        classifier=RuleClassifier(REFERENCE_DATE),
    )


def test_tracking_parameters_are_removed_from_urls() -> None:
    assert canonicalize_url(
        "https://Example.test/grant/?utm_source=x&ref=email&round=2#apply"
    ) == "https://example.test/grant?round=2"


def test_same_url_from_two_sources_is_deduplicated() -> None:
    items = [
        raw(url="https://example.test/grant?utm_source=portal"),
        raw(
            source_id="newsletter",
            source_kind="newsletter",
            url="https://example.test/grant?ref=email",
            title="Applications open: circular economy grant",
        ),
    ]
    candidates = deduplicate(items)
    assert len(candidates) == 1
    assert candidates[0].source_ids == {"source-a", "newsletter"}
    assert len(candidates[0].source_urls) == 2


def test_near_duplicate_titles_with_same_deadline_are_merged() -> None:
    items = [
        raw(url="https://example.test/a", title="Circular Innovation Grant 2026"),
        raw(
            source_id="source-b",
            url="https://example.test/b",
            title="Applications open Circular Innovation Grant",
        ),
    ]
    assert token_similarity(items[0].title, items[1].title) >= 0.7
    assert len(deduplicate(items)) == 1


def test_matching_titles_with_different_deadlines_stay_separate() -> None:
    items = [
        raw(url="https://example.test/a"),
        raw(
            source_id="source-b",
            url="https://example.test/b",
            deadline=date(2026, 9, 1),
        ),
    ]
    assert len(deduplicate(items)) == 2


def test_relevant_near_deadline_item_is_high_priority() -> None:
    classification = RuleClassifier(REFERENCE_DATE).classify(raw())
    assert classification.category == "grant"
    assert classification.priority == "high"
    assert classification.confidence == pytest.approx(0.92)


def test_event_title_wins_over_procurement_body_language() -> None:
    item = raw(
        title="Climate Procurement Summit",
        content="A conference seeking speakers on sustainable procurement and ESG.",
        deadline=date(2026, 9, 30),
    )
    classification = RuleClassifier(REFERENCE_DATE).classify(item)
    assert classification.category == "event"


def test_weak_match_is_routed_for_review(tmp_path: Path) -> None:
    item = raw(
        title="General member update",
        content="A routine note about internal scheduling and office administration.",
        deadline=None,
    )
    result = pipeline_for(tmp_path, [item]).run()
    assert len(result.review_queue) == 1
    assert result.records[0].review_required is True
    assert result.records[0].priority == "low"


def test_source_urls_survive_deduplication(tmp_path: Path) -> None:
    web_path = tmp_path / "web.json"
    news_path = tmp_path / "news.json"
    write_fixture(web_path, [raw(url="https://example.test/grant?utm_source=web")])
    write_fixture(
        news_path,
        [
            raw(
                source_id="newsletter",
                source_kind="newsletter",
                url="https://example.test/grant?ref=email",
            )
        ],
    )
    result = OpportunityPipeline(
        collectors=[
            FixtureWebCollector("source-a", web_path),
            FixtureNewsletterCollector("newsletter", news_path),
        ],
        classifier=RuleClassifier(REFERENCE_DATE),
    ).run()
    assert len(result.records) == 1
    assert result.records[0].source_ids == ["newsletter", "source-a"]
    assert len(result.records[0].source_urls) == 2


def test_failed_source_does_not_abort_healthy_source(tmp_path: Path) -> None:
    healthy_path = tmp_path / "healthy.json"
    write_fixture(healthy_path, [raw()])
    result = OpportunityPipeline(
        collectors=[
            FixtureWebCollector("source-a", healthy_path),
            FixtureNewsletterCollector("broken-newsletter", tmp_path / "missing.json"),
        ],
        classifier=RuleClassifier(REFERENCE_DATE),
    ).run()
    assert len(result.records) == 1
    states = {item.source_id: item for item in result.source_health}
    assert states["source-a"].status == "healthy"
    assert states["broken-newsletter"].status == "failed"


def test_health_ledger_counts_consecutive_failures() -> None:
    ledger = HealthLedger()
    ledger.record_failure("source-a", "first")
    second = ledger.record_failure("source-a", "second")
    assert second.consecutive_failures == 2
    assert second.last_error == "second"


def test_health_success_resets_failure_count() -> None:
    ledger = HealthLedger()
    ledger.record_failure("source-a", "temporary")
    success = ledger.record_success("source-a", 3)
    assert success.consecutive_failures == 0
    assert success.last_error is None


def test_digest_lists_high_priority_before_review_item(tmp_path: Path) -> None:
    items = [
        raw(title="Circular economy grant"),
        raw(
            url="https://example.test/update",
            title="General member update",
            content="A routine note about internal scheduling and office administration.",
            deadline=None,
        ),
    ]
    digest = render_markdown_digest(pipeline_for(tmp_path, items).run())
    assert digest.index("Circular economy grant") < digest.index(
        "General member update"
    )
    assert "REVIEW REQUIRED" in digest


def test_schema_rejects_unknown_fields() -> None:
    payload = raw().model_dump()
    payload["unexpected"] = "not allowed"
    with pytest.raises(ValidationError):
        RawOpportunity.model_validate(payload)


def test_schema_rejects_naive_discovery_time() -> None:
    payload = raw().model_dump()
    payload["discovered_at"] = datetime(2026, 7, 24)
    with pytest.raises(ValidationError):
        RawOpportunity.model_validate(payload)


def test_fixture_rejects_wrong_source_kind(tmp_path: Path) -> None:
    fixture = tmp_path / "wrong-kind.json"
    write_fixture(fixture, [raw(source_kind="web")])
    collector = FixtureNewsletterCollector("source-a", fixture)
    with pytest.raises(Exception, match="unexpected source kind"):
        collector.collect()

