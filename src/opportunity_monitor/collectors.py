from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import RawOpportunity


class CollectorError(RuntimeError):
    """Raised when one source cannot be collected safely."""


class SourceCollector(Protocol):
    source_id: str

    def collect(self) -> list[RawOpportunity]:
        """Return validated raw opportunities from one source."""


def _load_fixture(path: Path, expected_kind: str) -> list[RawOpportunity]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [RawOpportunity.model_validate(item) for item in payload]
    except (OSError, ValueError) as exc:
        raise CollectorError(f"fixture could not be collected: {path.name}") from exc

    if any(item.source_kind != expected_kind for item in items):
        raise CollectorError(
            f"fixture {path.name} contains an unexpected source kind"
        )
    return items


@dataclass(frozen=True)
class FixtureWebCollector:
    source_id: str
    fixture_path: Path

    def collect(self) -> list[RawOpportunity]:
        items = _load_fixture(self.fixture_path, expected_kind="web")
        if any(item.source_id != self.source_id for item in items):
            raise CollectorError("web fixture source_id does not match collector")
        return items


@dataclass(frozen=True)
class FixtureNewsletterCollector:
    source_id: str
    fixture_path: Path

    def collect(self) -> list[RawOpportunity]:
        items = _load_fixture(self.fixture_path, expected_kind="newsletter")
        if any(item.source_id != self.source_id for item in items):
            raise CollectorError("newsletter fixture source_id does not match collector")
        return items

