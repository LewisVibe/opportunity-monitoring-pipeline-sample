"""Opportunity monitoring reference pipeline."""

from .classifier import Classifier, RuleClassifier
from .collectors import FixtureNewsletterCollector, FixtureWebCollector
from .ledger import HealthLedger
from .models import OpportunityRecord, PipelineResult, RawOpportunity
from .pipeline import OpportunityPipeline

__all__ = [
    "Classifier",
    "FixtureNewsletterCollector",
    "FixtureWebCollector",
    "HealthLedger",
    "OpportunityPipeline",
    "OpportunityRecord",
    "PipelineResult",
    "RawOpportunity",
    "RuleClassifier",
]
