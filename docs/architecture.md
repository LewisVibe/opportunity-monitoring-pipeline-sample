# Architecture notes

## Source registry

Every production source should have an explicit record covering:

- owner and business purpose
- access method and authentication
- permitted collection method
- schedule and request budget
- expected fields and typical result volume
- change-detection signal
- fallback or manual-review route

This prevents a source URL from becoming an undocumented scraper that nobody knows how to repair.

## Connector boundary

Collectors return `RawOpportunity` records and do not classify or store them. APIs, RSS, normal HTTP extraction, mailbox APIs and permitted browser automation can therefore be implemented independently.

A collector failure is recorded in `HealthLedger`. It does not abort the full run.

## Normalisation and duplicate control

The sample removes common tracking parameters and fragments before comparing URLs. It then performs conservative title-token matching for near duplicates.

A production system should add source-specific identifiers and persistence-backed fingerprints. Similarity alone should never merge records when deadlines or organisations conflict.

## Classification boundary

`Classifier` returns a strict `Classification` object. The included implementation is deterministic; a production LLM adapter would be required to return the same object before its output could enter the rest of the pipeline.

Low-confidence results are marked `review_required` and listed separately.

## Persistence and scheduling

The in-memory ledger keeps the example focused. A production deployment would use:

- PostgreSQL or another durable store
- a transactional run and action ledger
- encrypted secret storage
- scheduled container or serverless execution
- metrics and alerting for stale or failing sources
