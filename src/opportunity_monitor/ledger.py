from __future__ import annotations

from .models import SourceHealth


class HealthLedger:
    def __init__(self) -> None:
        self._state: dict[str, SourceHealth] = {}

    def record_success(self, source_id: str, item_count: int) -> SourceHealth:
        health = SourceHealth(
            source_id=source_id,
            status="healthy",
            item_count=item_count,
            consecutive_failures=0,
            last_error=None,
        )
        self._state[source_id] = health
        return health

    def record_failure(self, source_id: str, error: str) -> SourceHealth:
        previous = self._state.get(source_id)
        failures = 1 if previous is None else previous.consecutive_failures + 1
        health = SourceHealth(
            source_id=source_id,
            status="failed",
            item_count=0,
            consecutive_failures=failures,
            last_error=error,
        )
        self._state[source_id] = health
        return health

    def snapshot(self) -> list[SourceHealth]:
        return [self._state[key] for key in sorted(self._state)]

