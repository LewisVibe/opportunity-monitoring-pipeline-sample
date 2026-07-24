from __future__ import annotations

from .models import PipelineResult


def render_markdown_digest(result: PipelineResult) -> str:
    lines = [
        "# Opportunity digest",
        "",
        f"- Opportunities: {len(result.records)}",
        f"- Needs review: {len(result.review_queue)}",
        "",
        "## Source health",
        "",
    ]
    for source in result.source_health:
        detail = (
            f"{source.item_count} items"
            if source.status == "healthy"
            else f"{source.consecutive_failures} failure(s): {source.last_error}"
        )
        lines.append(f"- **{source.source_id}**: {source.status} — {detail}")

    lines.extend(["", "## Opportunities", ""])
    for record in result.records:
        deadline = record.deadline.isoformat() if record.deadline else "not supplied"
        review = " — REVIEW REQUIRED" if record.review_required else ""
        lines.extend(
            [
                f"### {record.title}{review}",
                "",
                f"- Priority: {record.priority}",
                f"- Category: {record.category}",
                f"- Deadline: {deadline}",
                f"- Sources: {len(record.source_urls)}",
                f"- Why: {record.relevance_reason}",
                "",
                record.summary,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"

