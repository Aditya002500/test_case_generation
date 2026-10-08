"""Paper-grade metrics for the SpecTest-LLM evaluation.

These functions aggregate results from the pipeline into a flat dict suitable
for the UI, for logging, and for a results CSV in experiments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from discrimination import DiscriminationScore
from diversity import inter_student_diversity, intra_category_diversity
from schemas import StudentTestSuite, TestCase


@dataclass
class PipelineMetrics:
    n_students: int
    n_cases: int
    intra_diversity: Dict[str, float]
    inter_diversity: float
    discrimination_mean: float
    discrimination_min: float
    coverage_pct: float
    oracle_match_rate: float
    low_discrimination_ids: List[str]
    oracle_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    mutation_score: float = 0.0
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_intra_diversity(suites: List[StudentTestSuite]) -> Dict[str, float]:
    flat: List[TestCase] = []
    for s in suites:
        flat.extend(s.cases)
    return intra_category_diversity(flat)


def compute_inter_diversity(suites: List[StudentTestSuite]) -> float:
    if len(suites) < 2:
        return 0.0
    return inter_student_diversity([s.cases for s in suites])


def compute_discrimination_summary(
    scores: List[DiscriminationScore],
    low_threshold: float = 0.3,
) -> tuple[float, float, List[str]]:
    if not scores:
        return 0.0, 0.0, []
    values = [s.score for s in scores]
    low = [s.case_id for s in scores if s.score < low_threshold]
    return sum(values) / len(values), min(values), low


def build_metrics(
    suites: List[StudentTestSuite],
    *,
    coverage_pct: float,
    oracle_match_rate: float,
    oracle_mismatches: List[Dict[str, Any]],
    discrimination_scores: List[DiscriminationScore],
    mutation_score: float = 0.0,
    duration_ms: float = 0.0,
    low_threshold: float = 0.3,
) -> PipelineMetrics:
    n_cases = sum(len(s.cases) for s in suites)
    intra = compute_intra_diversity(suites)
    inter = compute_inter_diversity(suites)
    disc_mean, disc_min, low_ids = compute_discrimination_summary(
        discrimination_scores,
        low_threshold=low_threshold,
    )
    return PipelineMetrics(
        n_students=len(suites),
        n_cases=n_cases,
        intra_diversity=intra,
        inter_diversity=round(inter, 3),
        discrimination_mean=round(disc_mean, 3),
        discrimination_min=round(disc_min, 3),
        coverage_pct=round(coverage_pct, 3),
        oracle_match_rate=round(oracle_match_rate, 3),
        low_discrimination_ids=low_ids,
        oracle_mismatches=oracle_mismatches,
        mutation_score=round(mutation_score, 4),
        duration_ms=round(duration_ms, 1),
    )


def metrics_summary_line(metrics: PipelineMetrics) -> str:
    """A short human-readable line for logs and UI banners."""
    return (
        f"cases={metrics.n_cases} students={metrics.n_students} "
        f"intra_div={ {k: round(v, 2) for k, v in metrics.intra_diversity.items()} } "
        f"inter_div={metrics.inter_diversity:.2f} "
        f"disc={metrics.discrimination_mean:.2f} "
        f"oracle_match={metrics.oracle_match_rate:.2f} "
        f"coverage={metrics.coverage_pct:.2f} "
        f"mutation_score={metrics.mutation_score:.2f}"
    )
