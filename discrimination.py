"""Discrimination analysis: how well does a test case distinguish the correct
implementation from a set of adversarially-generated wrong ones?

A test is *low-discrimination* if it produces the same output for the correct
code and every wrong implementation we tried. Such tests pass for code that is
clearly broken, so they don't help surface bugs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from oracle import OracleResult, run_python_oracle
from schemas import TestCase

logger = logging.getLogger(__name__)


@dataclass
class DiscriminationScore:
    case_id: str
    category: str
    score: float
    n_impls: int
    n_killed: int
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "score": round(self.score, 3),
            "n_impls": self.n_impls,
            "n_killed": self.n_killed,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Adversarial implementation templates (Python)
# ---------------------------------------------------------------------------


def _wrap(entry: str, body: str, *, args_list: bool = True) -> str:
    """Wrap a body that assigns `result` into a Python module defining `entry`."""
    sig = (
        f"def {entry}(*args, **kwargs):\n    result = "
        if args_list
        else f"def {entry}(*args, **kwargs):\n    args = list(args) or list(kwargs.values())\n    result = "
    )
    return sig + body + "\n"


TEMPLATES: Dict[str, str] = {
    "constant_none": "None",
    "constant_zero_int": "0",
    "constant_empty_list": "[]",
    "identity_first": "(args[0] if args else None)",
    "reverse_input": "args[0][::-1] if args and isinstance(args[0], (list, str)) else (args[0] if args else None)",
    "off_by_one": "args[0] + 1 if isinstance(args[0], int) else (args[0][:-1] if args and isinstance(args[0], str) else None)",
    "negate_bool": "not bool(args[0]) if args else None",
    "sort_list": "sorted(args[0]) if args and isinstance(args[0], list) else None",
    "wrong_op": "(args[0] - args[1]) if len(args) >= 2 and isinstance(args[0], (int, float)) else None",
    "all_multiples_of_3": "['Fizz'] * (args[0] if args else 0)",
    "return_input": "(args[0] if args else None)",
}


def adversarial_implementations(entry: str) -> List[Dict[str, str]]:
    """Return a list of {name, code} candidates that are intentionally wrong."""
    out: List[Dict[str, str]] = []
    for name, body in TEMPLATES.items():
        out.append(
            {
                "name": name,
                "code": _wrap(entry, body, args_list=True),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _values_equal(a: Any, b: Any) -> bool:
    if a == b:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max(1.0, 1e-6 * abs(b))
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return all(_values_equal(x, y) for x, y in zip(a, b))
    return False


def score_case(
    case: TestCase,
    *,
    reference_code: str,
    entry: str,
    call_style: str = "args_list",
    timeout_s: float = 1.0,
) -> DiscriminationScore:
    """Run the case against reference + a suite of adversarial impls.

    score = (# wrong impls that disagree with reference on this case) / (total impls).

    score = 0 means the test cannot tell a correct implementation from any of
    our wrong ones → low discrimination → flagged.
    score = 1 means the test breaks every wrong impl while agreeing with the
    reference → high discrimination.
    """
    if not reference_code.strip():
        return DiscriminationScore(
            case.id, case.category, 0.0, 0, 0, "no reference code"
        )

    ref = run_python_oracle(
        reference_code,
        entry,
        case.input,
        call_style=call_style,
        timeout_s=timeout_s,
    )
    if not ref.success:
        return DiscriminationScore(
            case.id,
            case.category,
            0.0,
            0,
            0,
            notes=f"reference failed: {ref.error}",
        )

    impls = adversarial_implementations(entry)
    killed = 0
    used = 0
    for impl in impls:
        wrong = run_python_oracle(
            impl["code"],
            entry,
            case.input,
            call_style=call_style,
            timeout_s=timeout_s,
        )
        if not wrong.success:
            continue
        used += 1
        if not _values_equal(wrong.value, ref.value):
            killed += 1
    if used == 0:
        return DiscriminationScore(case.id, case.category, 0.0, 0, 0, "no usable impls")
    return DiscriminationScore(
        case_id=case.id,
        category=case.category,
        score=killed / used,
        n_impls=used,
        n_killed=killed,
    )


def score_suite(
    cases: List[TestCase],
    *,
    reference_code: str,
    entry: str,
    call_style: str = "args_list",
    timeout_s: float = 1.0,
    max_cases: Optional[int] = None,
) -> List[DiscriminationScore]:
    if max_cases is not None:
        cases = cases[:max_cases]
    return [
        score_case(
            c,
            reference_code=reference_code,
            entry=entry,
            call_style=call_style,
            timeout_s=timeout_s,
        )
        for c in cases
    ]


def average_score(scores: List[DiscriminationScore]) -> float:
    if not scores:
        return 0.0
    return sum(s.score for s in scores) / len(scores)


def low_discrimination_cases(
    scores: List[DiscriminationScore],
    threshold: float = 0.3,
) -> List[str]:
    return [s.case_id for s in scores if s.score < threshold]
