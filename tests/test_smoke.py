"""Smoke + unit tests covering helpers and the new architecture modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discrimination import (  # noqa: E402
    DiscriminationScore,
    average_score,
    low_discrimination_cases,
    score_case,
    score_suite,
)
from diversity import (  # noqa: E402
    categories_needing_resample,
    fingerprint,
    inter_student_diversity,
    intra_category_diversity,
    jaccard,
    pairwise_diversity,
)
from graph import (  # noqa: E402
    CATEGORIES,
    MAX_REFINES,
    _build_student_seed,
    _cap_string,
    _category_targets,
    _coerce_input_to_spec,
    _enforce_targets,
    _eval_string_expression,
    _extract_json_blob,
    _normalize_category,
    _normalize_pythonish,
    _parse_case_list,
    _payload_for_oracle,
    _rewrite_repeat_calls,
    should_refine,
)
from metrics import (  # noqa: E402
    build_metrics,
    compute_intra_diversity,
    metrics_summary_line,
)
from oracle import run_python_oracle  # noqa: E402
from schemas import (  # noqa: E402
    CodeAnalysis,
    FeedbackSignal,
    Spec,
    StudentTestSuite,
    TestCase,
    TestCaseList,
    TestPlan,
)
from spec_graph import (  # noqa: E402
    Dimension,
    SpecGraph,
    build_spec_graph_from_llm_text,
    fallback_spec_graph,
)


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------


def test_canonical_categories():
    assert len(CATEGORIES) == 6
    assert _category_targets(2) == {c: 2 for c in CATEGORIES}


def test_normalize_category():
    cases = {
        "basic": "Basic cases",
        "edge": "Boundary cases",
        "edge cases": "Boundary cases",
        "boundary": "Boundary cases",
        "random sampling": "Random cases",
        "stress": "Stress cases",
        "invalid": "Invalid/robustness cases",
        "robustness": "Invalid/robustness cases",
        "bug": "Bug-targeted cases",
        "weird": "weird",
    }
    for raw, expected in cases.items():
        assert _normalize_category(raw) == expected, raw


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


def test_enforce_targets_picks_per_category():
    cases = [
        TestCase(category="Basic cases", input=[i], expected=i, explanation="x")
        for i in range(5)
    ]
    enforced, missing = _enforce_targets(cases, {"Basic cases": 2})
    assert len(enforced) == 2
    assert enforced[0].category == "Basic cases"
    assert missing == {}


def test_enforce_targets_reports_missing():
    enforced, missing = _enforce_targets([], _category_targets(2))
    assert enforced == []
    assert set(missing.keys()) == set(CATEGORIES)


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def test_strip_markdown_and_extract_json():
    fenced = '```json\n{"cases": []}\n```'
    blob = _extract_json_blob(fenced)
    assert json.loads(blob) == {"cases": []}


def test_parse_case_list_happy_path():
    raw = json.dumps(
        {
            "cases": [
                {
                    "category": "Basic cases",
                    "input": [1, 2],
                    "expected": 3,
                    "explanation": "1+2",
                }
            ]
        }
    )
    parsed = _parse_case_list(raw)
    assert len(parsed.cases) == 1
    assert parsed.cases[0].category == "Basic cases"


def test_parse_case_list_handles_python_literals():
    raw = "{\n  'cases': [\n    {'category': 'Basic', 'input': [1, 2,], 'expected': True, 'explanation': 'x',},\n  ],\n}"
    blob = _normalize_pythonish(raw.replace("'", '"'))
    assert json.loads(blob) == {
        "cases": [
            {
                "category": "Basic",
                "input": [1, 2],
                "expected": True,
                "explanation": "x",
            }
        ]
    }


def test_parse_case_list_returns_empty_on_garbage():
    parsed = _parse_case_list("not json at all")
    assert parsed.cases == []


def test_string_expression_eval():
    assert _eval_string_expression('"a" * 3') == "aaa"
    assert _eval_string_expression('"a" + "b" * 2') == "abb"
    assert _eval_string_expression("1 + 2") is None
    assert _eval_string_expression('"x".repeat(3)') is None


def test_repeat_rewriter():
    assert _rewrite_repeat_calls('"x".repeat(3)') == '"x" * 3'


def test_cap_string():
    assert _cap_string("x" * 250, limit=10) == "x" * 10


# ---------------------------------------------------------------------------
# Refinement
# ---------------------------------------------------------------------------


def test_student_seed_differs_per_student():
    a = _build_student_seed("Two Sum", 1)
    b = _build_student_seed("Two Sum", 2)
    c = _build_student_seed("Three Sum", 1)
    assert a != b
    assert a != c


def test_should_refine_respects_max():
    fb_refine = FeedbackSignal(needs_refine=True, issues=[], recommendations=[])
    fb_done = FeedbackSignal(needs_refine=False, issues=[], recommendations=[])
    assert (
        should_refine({"iteration": 0, "issues": ["x"], "feedback": fb_refine})
        == "refine"
    )
    assert (
        should_refine({"iteration": 0, "issues": [], "feedback": fb_refine}) == "refine"
    )
    assert should_refine({"iteration": 0, "issues": [], "feedback": fb_done}) == "final"
    assert (
        should_refine(
            {"iteration": MAX_REFINES, "issues": ["x"], "feedback": fb_refine}
        )
        == "final"
    )
    assert (
        should_refine({"iteration": 1, "issues": ["x"], "feedback": fb_refine})
        == "final"
    )


# ---------------------------------------------------------------------------
# Schemas round-trip
# ---------------------------------------------------------------------------


def test_schemas_round_trip():
    spec = Spec(
        problem_summary="p",
        input_format="i",
        output_format="o",
        constraints=["c1"],
        edge_cases=["e"],
        hidden_cases=[],
        notes=[],
    )
    blob = spec.model_dump()
    again = Spec.model_validate(blob)
    assert again == spec


# ===========================================================================
# New architecture modules
# ===========================================================================


# ---- oracle.py ----


def test_oracle_correct_function():
    code = "def add(a, b):\n    return a + b\n"
    res = run_python_oracle(code, "add", [2, 3], call_style="args_list", timeout_s=2.0)
    assert res.success is True
    assert res.value == 5
    assert res.error is None


def test_oracle_handles_string_output():
    code = "def rev(s):\n    return s[::-1]\n"
    res = run_python_oracle(code, "rev", "hello", call_style="args_list", timeout_s=2.0)
    assert res.success is True
    assert res.value == "olleh"


def test_oracle_handles_list_output():
    code = "def fb(n):\n    return [str(i) for i in range(1, n+1)]\n"
    res = run_python_oracle(code, "fb", 3, call_style="args_list", timeout_s=2.0)
    assert res.success is True
    assert res.value == ["1", "2", "3"]


def test_oracle_times_out_on_slow_code():
    import time

    code = "def slow(x):\n    import time; time.sleep(10); return x\n"
    t0 = time.perf_counter()
    res = run_python_oracle(code, "slow", 1, call_style="args_list", timeout_s=0.3)
    elapsed = time.perf_counter() - t0
    assert res.success is False
    assert "timeout" in (res.error or "")
    assert elapsed < 1.0  # did not wait the full 10s


def test_oracle_propagates_python_errors():
    code = "def boom(x):\n    return 1/0\n"
    res = run_python_oracle(code, "boom", 0, call_style="args_list", timeout_s=2.0)
    assert res.success is False
    assert "ZeroDivision" in (res.error or "")


# ---- spec_graph.py ----


def test_spec_graph_parses_well_formed_json():
    raw = json.dumps(
        {
            "function_signature": "def f(n: int) -> int",
            "call_style": "args_list",
            "dimensions": [
                {
                    "name": "n",
                    "type": "integer",
                    "role": "input",
                    "min": 1,
                    "max": 100,
                    "semantic_boundaries": [1, 100],
                }
            ],
            "return_type": "integer",
        }
    )
    g = build_spec_graph_from_llm_text(raw)
    assert g.dimensions[0].name == "n"
    assert g.dimensions[0].min == 1
    assert g.call_style == "args_list"


def test_spec_graph_parses_from_non_string():
    raw = {"function_signature": "def f()", "dimensions": [], "return_type": "any"}
    g = build_spec_graph_from_llm_text(raw)
    assert g.function_signature == "def f()"


def test_spec_graph_falls_back_on_garbage():
    g = build_spec_graph_from_llm_text("definitely not json")
    assert g.dimensions == []


def test_spec_graph_fallback_uses_numeric_constraints():
    g = fallback_spec_graph("Two Sum", "2 <= n <= 10000")
    assert g.dimensions
    assert g.dimensions[0].min == 2
    assert g.dimensions[0].max == 10000


def test_spec_graph_coverage_pct():
    g = SpecGraph(
        dimensions=[
            Dimension(name="n", type="integer", role="input", min=1, max=100),
        ]
    )
    cases = [{"input": 1}, {"input": 50}, {"input": 100}]
    pct = g.coverage_pct(cases)
    assert pct == 1.0  # all three cases cover the dim


def test_coerce_input_to_spec_handles_strings():
    sg = SpecGraph(dimensions=[Dimension(name="n", type="integer", role="input")])
    assert _coerce_input_to_spec("7", sg) == 7
    assert _coerce_input_to_spec("  -5  ", sg) == -5
    assert _coerce_input_to_spec(7, sg) == 7


def test_coerce_input_to_spec_handles_dict():
    sg = SpecGraph(
        dimensions=[
            Dimension(name="n", type="integer", role="input"),
            Dimension(name="s", type="string", role="input"),
        ]
    )
    out = _coerce_input_to_spec({"n": "10", "s": "hello"}, sg)
    assert out == {"n": 10, "s": "hello"}


# ---- diversity.py ----


def test_jaccard_disjoint_is_zero():
    from collections import Counter

    a = Counter({"a": 1, "b": 1})
    b = Counter({"c": 1, "d": 1})
    assert jaccard(a, b) == 0.0


def test_jaccard_identical_is_one():
    from collections import Counter

    a = Counter({"a": 1, "b": 1})
    assert jaccard(a, a) == 1.0


def test_pairwise_diversity_empty_and_single():
    assert pairwise_diversity([]) == 0.0
    assert (
        pairwise_diversity(
            [TestCase(category="X", input=1, expected=1, explanation="")]
        )
        == 0.0
    )


def test_pairwise_diversity_distinct_strings():
    cases = [
        TestCase(category="X", input="alpha", expected=None, explanation=""),
        TestCase(category="X", input="beta", expected=None, explanation=""),
        TestCase(category="X", input="gamma", expected=None, explanation=""),
    ]
    d = pairwise_diversity(cases)
    assert 0.0 < d <= 1.0


def test_pairwise_diversity_identical_strings_low():
    cases = [
        TestCase(category="X", input="same", expected=None, explanation=""),
        TestCase(category="X", input="same", expected=None, explanation=""),
    ]
    assert pairwise_diversity(cases) < 0.05


def test_intra_category_diversity():
    cases = [
        TestCase(category="A", input="abc", expected=None, explanation=""),
        TestCase(category="A", input="xyz", expected=None, explanation=""),
        TestCase(category="B", input="lmn", expected=None, explanation=""),
        TestCase(category="B", input="lmn", expected=None, explanation=""),
    ]
    out = intra_category_diversity(cases)
    assert "A" in out and "B" in out
    assert out["A"] > out["B"]


def test_inter_student_diversity_same_suites():
    s1 = [
        TestCase(category="X", input="a", expected=None, explanation=""),
        TestCase(category="X", input="b", expected=None, explanation=""),
    ]
    s2 = [
        TestCase(category="X", input="a", expected=None, explanation=""),
        TestCase(category="X", input="b", expected=None, explanation=""),
    ]
    assert inter_student_diversity([s1, s2]) == 0.0


def test_categories_needing_resample():
    div = {"A": 0.5, "B": 0.1, "C": 0.0}
    low = categories_needing_resample(div, threshold=0.3)
    assert "B" in low
    assert "C" in low
    assert "A" not in low


def test_fingerprint_stable():
    c1 = TestCase(category="X", input=1, expected=2, explanation="")
    c2 = TestCase(category="X", input=1, expected=2, explanation="")
    assert fingerprint(c1) == fingerprint(c2)
    c3 = TestCase(category="X", input=1, expected=3, explanation="")
    assert fingerprint(c1) != fingerprint(c3)


# ---- discrimination.py ----


def test_adversarial_templates_have_wrong_impls():
    from discrimination import adversarial_implementations

    impls = adversarial_implementations("foo")
    assert len(impls) >= 5
    for impl in impls:
        assert "def foo(" in impl["code"]


def test_score_case_against_known_wrong_impl():
    code = "def is_pal(s):\n    return s == s[::-1]\n"
    case = TestCase(
        id="t1", category="Boundary cases", input="abba", expected=True, explanation=""
    )
    s = score_case(
        case, reference_code=code, entry="is_pal", call_style="args_list", timeout_s=1.0
    )
    assert s.case_id == "t1"
    assert 0.0 <= s.score <= 1.0
    assert s.n_impls > 0


def test_low_discrimination_cases():
    scores = [
        DiscriminationScore("a", "X", 0.1, 5, 0, ""),
        DiscriminationScore("b", "X", 0.6, 5, 3, ""),
    ]
    assert low_discrimination_cases(scores, threshold=0.3) == ["a"]


def test_average_score():
    scores = [
        DiscriminationScore("a", "X", 0.4, 5, 2, ""),
        DiscriminationScore("b", "X", 0.6, 5, 3, ""),
    ]
    assert average_score(scores) == 0.5


# ---- metrics.py ----


def test_build_metrics_smoke():
    suites = [
        StudentTestSuite(
            student_id=1,
            cases=[
                TestCase(category="Basic cases", input=1, expected=1, explanation=""),
                TestCase(
                    category="Boundary cases", input=0, expected=0, explanation=""
                ),
            ],
        )
    ]
    m = build_metrics(
        suites,
        coverage_pct=1.0,
        oracle_match_rate=0.5,
        oracle_mismatches=[
            {
                "student_id": 1,
                "case_id": "x",
                "category": "c",
                "llm_expected": 1,
                "oracle_expected": 2,
            }
        ],
        discrimination_scores=[],
    )
    assert m.n_students == 1
    assert m.n_cases == 2
    assert m.coverage_pct == 1.0
    assert m.oracle_match_rate == 0.5
    assert "intra_diversity" in m.to_dict()


def test_metrics_summary_line_format():
    suites = [
        StudentTestSuite(
            student_id=1,
            cases=[
                TestCase(category="A", input=1, expected=1, explanation=""),
            ],
        )
    ]
    m = build_metrics(
        suites,
        coverage_pct=1.0,
        oracle_match_rate=1.0,
        oracle_mismatches=[],
        discrimination_scores=[],
    )
    line = metrics_summary_line(m)
    assert "cases=1" in line
    assert "students=1" in line
    assert "oracle_match=1.00" in line


# ---- payload_for_oracle ----


def test_payload_args_list_single():
    sg = SpecGraph(call_style="args_list")
    c = TestCase(id="x", category="X", input=7, expected=None, explanation="")
    assert _payload_for_oracle(c, sg) == [7]


def test_payload_args_list_multi():
    sg = SpecGraph(call_style="args_list")
    c = TestCase(id="x", category="X", input=[1, 2], expected=None, explanation="")
    assert _payload_for_oracle(c, sg) == [1, 2]


def test_payload_kwargs_with_dict():
    sg = SpecGraph(call_style="kwargs")
    c = TestCase(id="x", category="X", input={"n": 7}, expected=None, explanation="")
    assert _payload_for_oracle(c, sg) == {"n": 7}


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
