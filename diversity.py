"""Diversity metrics for test suites.

We measure pairwise dissimilarity within a category (intra-category diversity)
and across students (inter-student diversity). The signal type is chosen
based on the input shape: numeric lists get histogram Jaccard, strings get
character n-gram Jaccard, nested structures get token-level Jaccard.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Any, Dict, List, Sequence, Tuple

from schemas import TestCase


# ---------------------------------------------------------------------------
# Canonical string form
# ---------------------------------------------------------------------------


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


# ---------------------------------------------------------------------------
# N-gram helpers
# ---------------------------------------------------------------------------


def _char_ngrams(text: str, n: int = 3) -> Counter:
    if len(text) < n:
        return Counter([text]) if text else Counter()
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


def _token_ngrams(value: Any, n: int = 2) -> Counter:
    tokens = _flatten(value)
    if len(tokens) < n:
        return Counter([tuple(tokens)]) if tokens else Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def _flatten(value: Any) -> List[str]:
    if value is None:
        return ["null"]
    if isinstance(value, (int, float, bool, str)):
        return [str(value)]
    if isinstance(value, (list, tuple)):
        out: List[str] = []
        for item in value:
            out.extend(_flatten(item))
        return out
    if isinstance(value, dict):
        out = []
        for k, v in sorted(value.items()):
            out.append(str(k))
            out.extend(_flatten(v))
        return out
    return [str(value)]


def _numeric_histogram(value: Sequence[float], bins: int = 8) -> Counter:
    if not value:
        return Counter()
    lo, hi = min(value), max(value)
    if math.isclose(lo, hi):
        return Counter({f"bin-{int(lo)}": len(value)})
    step = (hi - lo) / bins
    if step == 0:
        return Counter({f"bin-0": len(value)})
    out: Counter = Counter()
    for v in value:
        idx = min(int((v - lo) / step), bins - 1)
        out[f"bin-{idx}"] += 1
    return out


# ---------------------------------------------------------------------------
# Similarity primitives
# ---------------------------------------------------------------------------


def jaccard(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 1.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    if union == 0:
        return 1.0
    return inter / union


def _signature(value: Any) -> Counter:
    """Pick a signature counter appropriate to the value's shape."""
    if isinstance(value, str):
        return _char_ngrams(value)
    if (
        isinstance(value, (list, tuple))
        and value
        and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value)
    ):
        return _numeric_histogram(list(value))
    return _token_ngrams(value)


def _input_of(case: TestCase) -> Any:
    return case.input


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pairwise_diversity(cases: List[TestCase]) -> float:
    """Average pairwise Jaccard *distance* (1 - similarity) over inputs.

    Returns 0.0 for a single case (no pairs), 1.0 for maximally diverse.
    """
    if len(cases) < 2:
        return 0.0
    sigs = [_signature(_input_of(c)) for c in cases]
    total = 0.0
    pairs = 0
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            total += 1.0 - jaccard(sigs[i], sigs[j])
            pairs += 1
    return total / pairs if pairs else 0.0


def intra_category_diversity(suite_cases: List[TestCase]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    by_cat: Dict[str, List[TestCase]] = {}
    for c in suite_cases:
        by_cat.setdefault(c.category, []).append(c)
    for cat, items in by_cat.items():
        out[cat] = pairwise_diversity(items)
    return out


def inter_student_diversity(suites: List[List[TestCase]]) -> float:
    """Mean Jaccard distance between consecutive students' flat input sets."""
    if len(suites) < 2:
        return 0.0
    sigs: List[Counter] = []
    for s in suites:
        agg: Counter = Counter()
        for c in s:
            for k, v in _signature(_input_of(c)).items():
                agg[k] += v
        sigs.append(agg)
    total = 0.0
    pairs = 0
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            total += 1.0 - jaccard(sigs[i], sigs[j])
            pairs += 1
    return total / pairs if pairs else 0.0


def categories_needing_resample(
    diversity: Dict[str, float],
    threshold: float = 0.35,
) -> List[str]:
    """Return categories whose intra-diversity is below threshold."""
    return [cat for cat, d in diversity.items() if d < threshold and d >= 0]


def fingerprint(case: TestCase) -> str:
    h = hashlib.sha1()
    h.update(_canonical(_input_of(case)).encode("utf-8"))
    h.update(b"|")
    h.update(_canonical(case.expected).encode("utf-8"))
    return h.hexdigest()[:12]
