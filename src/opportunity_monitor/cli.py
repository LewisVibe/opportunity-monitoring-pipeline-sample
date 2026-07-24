from __future__ import annotations

from datetime import date
from pathlib import Path

from .classifier import RuleClassifier
from .collectors import FixtureNewsletterCollector, FixtureWebCollector
from .digest import render_markdown_digest
from .pipeline import OpportunityPipeline


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    collectors = [
        FixtureWebCollector(
            source_id="public-grants-portal",
            fixture_path=root / "fixtures" / "web_items.json",
        ),
        FixtureNewsletterCollector(
            source_id="weekly-opportunities-newsletter",
            fixture_path=root / "fixtures" / "newsletter_items.json",
        ),
    ]
    pipeline = OpportunityPipeline(
        collectors=collectors,
        classifier=RuleClassifier(reference_date=date(2026, 7, 24)),
    )
    print(render_markdown_digest(pipeline.run()), end="")


if __name__ == "__main__":
    main()

