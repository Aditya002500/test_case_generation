from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Callable, Dict, List, Tuple, TypedDict

from langgraph.graph import END, StateGraph

from agents import (
    build_code_analysis_agent,
    build_feedback_agent,
    build_spec_agent,
    build_spec_graph_agent,
    build_test_generator_agent,
    build_test_plan_agent,
)
from discrimination import DiscriminationScore, low_discrimination_cases, score_suite
from diversity import (
    categories_needing_resample,
    fingerprint,
    intra_category_diversity,
)
from llms import build_llm
from metrics import PipelineMetrics, build_metrics, metrics_summary_line
from oracle import run_python_oracle
from schemas import (
    CodeAnalysis,
    FeedbackSignal,
    FinalReport,
    Spec,
    StudentTestSuite,
    TestCase,
    TestCaseList,
    TestPlan,
)
from spec_graph import (
    SpecGraph,
    build_spec_graph_from_llm_text,
    fallback_spec_graph,
)

logger = logging.getLogger(__name__)

MAX_REFINES = 1
LLM_RETRIES = 2
LLM_RETRY_BACKOFF = 2.0
DIVERSITY_THRESHOLD = 0.35
DISCRIMINATION_THRESHOLD = 0.3
ORACLE_TIMEOUT_S = 1.5
DISCRIMINATION_TIMEOUT_S = 0.6


class GraphState(TypedDict, total=False):
    problem: str
    description: str
    constraints: str
    code: str
    language: str
    per_category: int
    student_count: int
    iteration: int
    spec: Spec
    analysis: CodeAnalysis
    spec_graph: SpecGraph
    plan: TestPlan
    suites: List[StudentTestSuite]
    feedback: FeedbackSignal
    metrics: PipelineMetrics
    issues: List[str]
    oracle_entry: str
    oracle_call_style: str


CATEGORIES = [
    "Basic cases",
    "Boundary cases",
    "Random cases",
    "Stress cases",
    "Invalid/robustness cases",
    "Bug-targeted cases",
]


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------


def _category_targets(per_category: int) -> Dict[str, int]:
    return {category: per_category for category in CATEGORIES}


def _normalize_category(label: str) -> str:
    if not isinstance(label, str):
        return "Other"
    lower = label.strip().lower()
    if "basic" in lower or "simple" in lower or "normal" in lower:
        return "Basic cases"
    if "boundary" in lower or "edge" in lower:
        return "Boundary cases"
    if "random" in lower or "sample" in lower:
        return "Random cases"
    if "stress" in lower or "large" in lower or "performance" in lower:
        return "Stress cases"
    if "invalid" in lower or "robust" in lower or "error" in lower:
        return "Invalid/robustness cases"
    if "bug" in lower or "target" in lower or "advers" in lower:
        return "Bug-targeted cases"
    return label


# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------


def _retry_invoke(chain: Callable, payload: Dict[str, Any], *, label: str) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, LLM_RETRIES + 2):
        try:
            return chain.invoke(payload)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("LLM call %s failed (attempt %s): %s", label, attempt, exc)
            if attempt <= LLM_RETRIES:
                time.sleep(LLM_RETRY_BACKOFF * attempt)
    assert last_error is not None
    raise last_error


def _strip_markdown(text: str) -> str:
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return stripped


def _extract_json_blob(text: str) -> str:
    start_obj = text.find("{")
    end_obj = text.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        return text[start_obj : end_obj + 1]
    start_list = text.find("[")
    end_list = text.rfind("]")
    if start_list != -1 and end_list != -1 and end_list > start_list:
        return text[start_list : end_list + 1]
    return text


def _scan_string(text: str, start: int) -> int:
    index = start + 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return index + 1
        index += 1
    return len(text)


def _find_expr_end(text: str, start: int) -> int:
    index = start
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in {",", "}", "]"}:
                return index
        index += 1
    return len(text)


def _tokenize_expr(expr: str) -> List[Tuple[str, Any]] | None:
    tokens: List[Tuple[str, Any]] = []
    index = 0
    while index < len(expr):
        char = expr[index]
        if char.isspace():
            index += 1
            continue
        if char == '"':
            end = _scan_string(expr, index)
            literal = expr[index:end]
            try:
                value = json.loads(literal)
            except json.JSONDecodeError:
                return None
            tokens.append(("str", value))
            index = end
            continue
        if char.isdigit():
            end = index
            while end < len(expr) and expr[end].isdigit():
                end += 1
            tokens.append(("int", int(expr[index:end])))
            index = end
            continue
        if char in {"+", "*"}:
            tokens.append(("op", char))
            index += 1
            continue
        return None
    return tokens


def _eval_string_expression(expr: str) -> str | None:
    tokens = _tokenize_expr(expr)
    if not tokens:
        return None
    has_string = any(token[0] == "str" for token in tokens)
    if not has_string:
        return None

    def parse_term(pos: int) -> Tuple[str | None, int]:
        if pos >= len(tokens):
            return None, pos
        if tokens[pos][0] == "str":
            value: Any = tokens[pos][1]
        elif tokens[pos][0] == "int":
            value = str(tokens[pos][1])
        else:
            return None, pos
        pos += 1
        while pos + 1 < len(tokens) and tokens[pos] == ("op", "*"):
            if tokens[pos + 1][0] != "int":
                return None, pos
            repeat = tokens[pos + 1][1]
            if not isinstance(value, str):
                return None, pos
            value = value * repeat
            pos += 2
        return value, pos

    result, pos = parse_term(0)
    if result is None:
        return None
    while pos < len(tokens):
        if tokens[pos] != ("op", "+"):
            return None
        term, pos = parse_term(pos + 1)
        if term is None:
            return None
        result += term
    return result


def _cap_string(value: str, limit: int = 200) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _rewrite_repeat_calls(text: str) -> str:
    output: List[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            start = index
            end = _scan_string(text, index)
            output.append(text[start:end])
            probe = end
            while probe < len(text) and text[probe].isspace():
                probe += 1
            if text.startswith(".repeat", probe):
                cursor = probe + len(".repeat")
                while cursor < len(text) and text[cursor].isspace():
                    cursor += 1
                if cursor < len(text) and text[cursor] == "(":
                    cursor += 1
                    while cursor < len(text) and text[cursor].isspace():
                        cursor += 1
                    number_start = cursor
                    while cursor < len(text) and text[cursor].isdigit():
                        cursor += 1
                    number = text[number_start:cursor]
                    while cursor < len(text) and text[cursor].isspace():
                        cursor += 1
                    if number and cursor < len(text) and text[cursor] == ")":
                        output.append(f" * {number}")
                        index = cursor + 1
                        continue
            index = end
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _replace_string_expressions(text: str) -> str:
    output: List[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            start = index
            end = _scan_string(text, index)
            probe = end
            while probe < len(text) and text[probe].isspace():
                probe += 1
            if probe < len(text) and text[probe] in {"+", "*"}:
                expr_end = _find_expr_end(text, start)
                expr_text = text[start:expr_end]
                evaluated = _eval_string_expression(expr_text)
                if evaluated is not None:
                    output.append(json.dumps(_cap_string(evaluated)))
                    index = expr_end
                    continue
            output.append(text[start:end])
            index = end
            continue
        if char.isdigit():
            start = index
            end = index
            while end < len(text) and text[end].isdigit():
                end += 1
            probe = end
            while probe < len(text) and text[probe].isspace():
                probe += 1
            if probe < len(text) and text[probe] == "*":
                expr_end = _find_expr_end(text, start)
                expr_text = text[start:expr_end]
                evaluated = _eval_string_expression(expr_text)
                if evaluated is not None:
                    output.append(json.dumps(_cap_string(evaluated)))
                    index = expr_end
                    continue
        output.append(char)
        index += 1
    return "".join(output)


def _normalize_pythonish(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        word = match.group(0)
        return {"True": "true", "False": "false", "None": "null"}[word]

    text = re.sub(r"\b(True|False|None)\b", _repl, text)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def _parse_case_list(raw_text: str) -> TestCaseList:
    cleaned = _strip_markdown(raw_text)
    rewritten = _rewrite_repeat_calls(cleaned)
    repaired = _replace_string_expressions(rewritten)
    blob = _extract_json_blob(repaired)
    blob = _normalize_pythonish(blob)
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return TestCaseList(cases=[])
    if isinstance(data, list):
        data = {"cases": data}
    if not isinstance(data, dict):
        return TestCaseList(cases=[])
    try:
        return TestCaseList.model_validate(data)
    except Exception:  # noqa: BLE001
        return TestCaseList(cases=[])


def _enforce_targets(
    cases: List[TestCase], targets: Dict[str, int]
) -> Tuple[List[TestCase], Dict[str, int]]:
    by_category: Dict[str, List[TestCase]] = {category: [] for category in targets}
    for case in cases:
        normalized = _normalize_category(case.category)
        case.category = normalized
        if normalized in by_category:
            by_category[normalized].append(case)
    enforced: List[TestCase] = []
    missing: Dict[str, int] = {}
    for category, count in targets.items():
        selected = by_category.get(category, [])[:count]
        enforced.extend(selected)
        remaining = count - len(selected)
        if remaining > 0:
            missing[category] = remaining
    return enforced, missing


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "case"


# ---------------------------------------------------------------------------
# Oracle entry point detection
# ---------------------------------------------------------------------------


_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)


def _detect_oracle_entry(code: str) -> str:
    if not code:
        return ""
    matches = _DEF_RE.findall(code)
    if not matches:
        return ""
    # Prefer a function whose name is not a dunder, not "main", not a class.
    for name in matches:
        if not name.startswith("_") and name not in {"main", "Solution", "Test"}:
            return name
    return matches[0]


# ---------------------------------------------------------------------------
# Pipeline nodes
# ---------------------------------------------------------------------------


def node_spec(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3-flash-preview", temperature=0.2)
    prompt, parser = build_spec_agent(llm)
    chain = prompt | llm | parser
    spec = _retry_invoke(
        chain,
        {
            "problem": state["problem"],
            "description": state.get("description", ""),
            "constraints": state.get("constraints", ""),
            "language": state.get("language", "python"),
            "format_instructions": parser.get_format_instructions(),
        },
        label="spec",
    )
    return {"spec": spec}


def node_analysis(state: GraphState) -> Dict[str, Any]:
    if not state.get("code", "").strip():
        return {"analysis": CodeAnalysis(), "oracle_entry": ""}
    llm = build_llm("gemini-2.5-flash", temperature=0.2)
    prompt, parser = build_code_analysis_agent(llm)
    chain = prompt | llm | parser
    analysis = _retry_invoke(
        chain,
        {
            "code": state["code"],
            "language": state.get("language", "python"),
            "format_instructions": parser.get_format_instructions(),
        },
        label="analysis",
    )
    return {"analysis": analysis, "oracle_entry": _detect_oracle_entry(state["code"])}


def node_spec_graph(state: GraphState) -> Dict[str, Any]:
    """Typed coverage model that drives both the plan and the generator's prompts."""
    llm = build_llm("gemini-3.1-flash-lite-preview", temperature=0.1)
    prompt = build_spec_graph_agent(llm) | llm
    raw = ""
    try:
        response = _retry_invoke(
            prompt,
            {
                "problem": state["problem"],
                "description": state.get("description", ""),
                "constraints": state.get("constraints", ""),
                "language": state.get("language", "python"),
            },
            label="spec_graph",
        )
        raw = response.content if hasattr(response, "content") else str(response)
    except Exception as exc:  # noqa: BLE001
        logger.warning("spec_graph LLM failed: %s", exc)

    graph = build_spec_graph_from_llm_text(raw)
    if not graph.dimensions:
        graph = fallback_spec_graph(state["problem"], state.get("constraints", ""))
    graph.call_style = graph.call_style or "args_list"
    if state.get("code") and state.get("language", "python") == "python":
        graph.call_style = "args_list"
    return {"spec_graph": graph}


def node_start(state: GraphState) -> Dict[str, Any]:
    return {"iteration": 0, "issues": state.get("issues", [])}


def node_plan(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3.1-flash-lite-preview", temperature=0.3)
    prompt, parser = build_test_plan_agent(llm)
    chain = prompt | llm | parser
    per_category = max(2, min(3, state.get("per_category", 2)))
    plan = _retry_invoke(
        chain,
        {
            "spec": state["spec"].model_dump(),
            "spec_graph": state.get("spec_graph", SpecGraph()).model_dump(),
            "analysis": state["analysis"].model_dump(),
            "issues": state.get("issues", []),
            "per_category": per_category,
            "format_instructions": parser.get_format_instructions(),
        },
        label="plan",
    )
    plan.targets = _category_targets(per_category)
    plan.categories = list(plan.targets.keys())
    return {"plan": plan}


def _build_student_seed(problem: str, student_id: int) -> int:
    base = abs(hash(problem)) % (10**8)
    return base + student_id * 9973


def _apply_student_seed(case_list: TestCaseList, seed: int) -> TestCaseList:
    rng = random.Random(seed)
    enriched: List[TestCase] = []
    for case in case_list.cases:
        inputs = case.input
        if (
            isinstance(inputs, list)
            and len(inputs) >= 2
            and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in inputs
            )
        ):
            try:
                lo, hi = float(min(inputs)), float(max(inputs))
                jitter = rng.uniform(-0.05, 0.05) * max(1.0, abs(hi - lo))
                if rng.random() < 0.5:
                    shifted = [round(lo + jitter, 4), round(hi + jitter, 4)]
                    if all(isinstance(v, int) for v in inputs):
                        shifted = [int(v) for v in shifted]
                    case = case.model_copy(update={"input": shifted})
            except (TypeError, ValueError):
                pass
        enriched.append(case)
    return TestCaseList(cases=enriched)


def _anti_examples_text(
    existing: List[TestCase], categories: List[str], limit_per_cat: int = 3
) -> str:
    """Render a small subset of existing cases per category to use as anti-examples."""
    by_cat: Dict[str, List[TestCase]] = {}
    for c in existing:
        by_cat.setdefault(c.category, []).append(c)
    lines: List[str] = []
    for cat in categories:
        items = by_cat.get(cat, [])[:limit_per_cat]
        if not items:
            continue
        lines.append(f"[{cat}]")
        for c in items:
            lines.append(f"  - input={json.dumps(c.input)[:160]}")
        lines.append("")
    return "\n".join(lines) if lines else "(none)"


def _coerce_input_to_spec(value: Any, spec_graph: SpecGraph) -> Any:
    """Best-effort type normalisation based on the spec graph.

    The LLM sometimes serialises integers as strings (e.g. "0", "-5"). The
    spec graph declares the expected type per dimension. This step walks
    nested inputs and applies the declared coercion.
    """
    if not spec_graph.dimensions:
        return value
    type_map: Dict[str, str] = {d.name: d.type for d in spec_graph.dimensions}
    input_types: List[str] = [
        d.type for d in spec_graph.dimensions if d.role == "input"
    ]

    def _coerce_one(v: Any, t: str) -> Any:
        if v is None or not t:
            return v
        if t in ("integer", "list_int"):
            if isinstance(v, str):
                stripped = v.strip()
                try:
                    return int(stripped)
                except ValueError:
                    try:
                        return float(stripped)
                    except ValueError:
                        return v
            return v
        if t == "boolean":
            if isinstance(v, str):
                low = v.strip().lower()
                if low in ("true", "1", "yes"):
                    return True
                if low in ("false", "0", "no"):
                    return False
            return v
        return v

    def _walk(v: Any) -> Any:
        if isinstance(v, dict):
            return {
                k: _coerce_one(val, type_map.get(k, "")) or _walk(val)
                for k, val in v.items()
            }
        if isinstance(v, list):
            return [_walk(item) for item in v]
        return v

    if isinstance(value, dict):
        return {
            k: _coerce_one(val, type_map.get(k, "")) or _walk(val)
            for k, val in value.items()
        }
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return [_walk(item) for item in value]
    # Single scalar / list of scalars: if there's exactly one input dim, use it.
    if len(input_types) == 1:
        return _coerce_one(value, input_types[0])
    if isinstance(value, list):
        return [
            _coerce_one(item, input_types[i] if i < len(input_types) else "")
            for i, item in enumerate(value)
        ]
    return value


def _payload_for_oracle(case: TestCase, spec_graph: SpecGraph) -> Any:
    """Translate a test case's `input` into the payload shape the oracle expects."""
    coerced = _coerce_input_to_spec(case.input, spec_graph)
    style = spec_graph.call_style
    if style == "args_list":
        if isinstance(coerced, list):
            return coerced
        return [coerced]
    if style == "kwargs":
        if isinstance(coerced, dict):
            return coerced
        return {"x": coerced}
    return coerced


def _run_oracle_for_case(
    case: TestCase,
    *,
    code: str,
    entry: str,
    spec_graph: SpecGraph,
) -> TestCase:
    if not code or not entry:
        return case
    coerced_input = _coerce_input_to_spec(case.input, spec_graph)
    case = case.model_copy(update={"input": coerced_input})
    payload = _payload_for_oracle(case, spec_graph)
    result = run_python_oracle(
        code,
        entry,
        payload,
        call_style=spec_graph.call_style,
        timeout_s=ORACLE_TIMEOUT_S,
    )
    if not result.success:
        return case.model_copy(
            update={
                "expected_oracle": None,
                "oracle_match": None,
                "oracle_error": result.error,
            }
        )
    match = result.value == case.expected
    return case.model_copy(
        update={
            "expected_oracle": result.value,
            "oracle_match": match,
            "oracle_error": None,
        }
    )


def _detect_student_count(state: GraphState) -> int:
    return max(1, int(state.get("student_count", 1)))


def node_generate(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-2.5-flash-lite", temperature=0.5)
    prompt, parser = build_test_generator_agent(llm)
    chain = prompt | llm
    suites: List[StudentTestSuite] = []
    issues: List[str] = []
    student_count = _detect_student_count(state)
    spec_graph = state.get("spec_graph") or SpecGraph()
    code = state.get("code", "")
    entry = state.get("oracle_entry", "")

    for student_id in range(1, student_count + 1):
        try:
            seed_cases: List[TestCase] = []
            for prior in suites:
                seed_cases.extend(prior.cases)
            anti = _anti_examples_text(seed_cases, list(CATEGORIES))
            response = _retry_invoke(
                chain,
                {
                    "spec": state["spec"].model_dump(),
                    "plan": state["plan"].model_dump(),
                    "spec_graph": spec_graph.model_dump(),
                    "student_id": student_id,
                    "student_count": student_count,
                    "anti_examples": anti,
                    "format_instructions": parser.get_format_instructions(),
                },
                label=f"generate-{student_id}",
            )
        except Exception as exc:  # noqa: BLE001
            issues.append(f"Student {student_id} LLM call failed: {exc}")
            continue
        raw_text = response.content if hasattr(response, "content") else str(response)
        case_list = _parse_case_list(raw_text)
        if not case_list.cases:
            issues.append(f"Student {student_id} output parsing failed")
            continue
        seed = _build_student_seed(state["problem"], student_id)
        case_list = _apply_student_seed(case_list, seed)
        enforced, missing = _enforce_targets(case_list.cases, state["plan"].targets)
        suite_cases: List[TestCase] = []
        for idx, case in enumerate(enforced, start=1):
            case_id = f"S{student_id}-C{idx:02d}-{_slug(case.category)}"
            if code and entry and spec_graph.call_style:
                case = _run_oracle_for_case(
                    case,
                    code=code,
                    entry=entry,
                    spec_graph=spec_graph,
                )
            suite_cases.append(
                case.model_copy(
                    update={
                        "id": case_id,
                        "student_id": student_id,
                        "category": _normalize_category(case.category),
                    }
                )
            )
        suites.append(StudentTestSuite(student_id=student_id, cases=suite_cases))
        if missing:
            issues.append(
                f"Student {student_id} missing categories: {sorted(missing.keys())}"
            )

    return {"suites": suites, "issues": issues}


def node_discrimination(state: GraphState) -> Dict[str, Any]:
    """Score discrimination for cases against adversarial impls. Used as a feedback signal."""
    code = state.get("code", "")
    entry = state.get("oracle_entry", "")
    spec_graph = state.get("spec_graph") or SpecGraph()
    if not code or not entry or state.get("language", "python") != "python":
        return {"issues": state.get("issues", [])}

    flat: List[TestCase] = []
    for s in state.get("suites", []):
        flat.extend(s.cases)
    if not flat:
        return {"issues": state.get("issues", [])}

    # Cap to keep this fast: 2 cases per category max.
    by_cat: Dict[str, List[TestCase]] = {}
    for c in flat:
        by_cat.setdefault(c.category, []).append(c)
    sampled: List[TestCase] = []
    for cat, items in by_cat.items():
        sampled.extend(items[:2])

    scores = score_suite(
        sampled,
        reference_code=code,
        entry=entry,
        call_style=spec_graph.call_style,
        timeout_s=DISCRIMINATION_TIMEOUT_S,
    )
    low = low_discrimination_cases(scores, threshold=DISCRIMINATION_THRESHOLD)
    issues = list(state.get("issues", []))
    for s in scores:
        for case in flat:
            if case.id == s.case_id:
                # attach score for the report
                case.discrimination_score = s.score
                break
    if low:
        issues.append(
            f"low-discrimination cases (score<{DISCRIMINATION_THRESHOLD}): {low[:5]}"
        )
    return {"issues": issues, "suites": state.get("suites", [])}


def _oracle_mismatches(suites: List[StudentTestSuite]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in suites:
        for c in s.cases:
            if c.oracle_match is False:
                out.append(
                    {
                        "student_id": s.student_id,
                        "case_id": c.id,
                        "category": c.category,
                        "llm_expected": c.expected,
                        "oracle_expected": c.expected_oracle,
                    }
                )
    return out


def _oracle_match_rate(suites: List[StudentTestSuite]) -> float:
    total = 0
    matches = 0
    for s in suites:
        for c in s.cases:
            if c.oracle_match is None:
                continue
            total += 1
            if c.oracle_match:
                matches += 1
    return (matches / total) if total else 0.0


def _coverage_pct(spec_graph: SpecGraph, suites: List[StudentTestSuite]) -> float:
    cases = [{"input": c.input} for s in suites for c in s.cases]
    return spec_graph.coverage_pct(cases)


def node_metrics(state: GraphState) -> Dict[str, Any]:
    suites = state.get("suites", [])
    spec_graph = state.get("spec_graph") or SpecGraph()
    coverage = _coverage_pct(spec_graph, suites)
    match_rate = _oracle_match_rate(suites)
    mismatches = _oracle_mismatches(suites)

    flat: List[TestCase] = []
    for s in suites:
        flat.extend(s.cases)
    by_cat: Dict[str, List[TestCase]] = {}
    for c in flat:
        by_cat.setdefault(c.category, []).append(c)
    sampled: List[TestCase] = []
    for items in by_cat.values():
        sampled.extend(items[:2])

    disc_scores: List[DiscriminationScore] = []
    if (
        state.get("code")
        and state.get("oracle_entry")
        and state.get("language", "python") == "python"
    ):
        disc_scores = score_suite(
            sampled,
            reference_code=state["code"],
            entry=state["oracle_entry"],
            call_style=spec_graph.call_style,
            timeout_s=DISCRIMINATION_TIMEOUT_S,
        )

    metrics = build_metrics(
        suites,
        coverage_pct=coverage,
        oracle_match_rate=match_rate,
        oracle_mismatches=mismatches,
        discrimination_scores=disc_scores,
    )
    logger.info("pipeline metrics: %s", metrics_summary_line(metrics))
    return {"metrics": metrics}


def node_feedback(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3-flash-preview", temperature=0.2)
    prompt, parser = build_feedback_agent(llm)
    chain = prompt | llm | parser
    issues = state.get("issues", [])
    feedback = _retry_invoke(
        chain,
        {
            "spec": state["spec"].model_dump(),
            "plan": state["plan"].model_dump(),
            "issues": issues,
            "format_instructions": parser.get_format_instructions(),
        },
        label="feedback",
    )
    needs_refine = bool(feedback.needs_refine) or bool(issues)
    iteration = state.get("iteration", 0) + (1 if needs_refine else 0)
    return {"feedback": feedback, "iteration": iteration}


def should_refine(state: GraphState) -> str:
    iteration = state.get("iteration", 0)
    issues = state.get("issues", [])
    feedback = state.get("feedback")
    if iteration >= MAX_REFINES:
        return "final"
    if issues:
        return "refine"
    if feedback is not None and feedback.needs_refine:
        return "refine"
    return "final"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("start", node_start)
    graph.add_node("spec", node_spec)
    graph.add_node("analysis", node_analysis)
    graph.add_node("spec_graph", node_spec_graph)
    graph.add_node("plan", node_plan)
    graph.add_node("generate", node_generate)
    graph.add_node("discrimination", node_discrimination)
    graph.add_node("metrics", node_metrics)
    graph.add_node("feedback", node_feedback)

    graph.set_entry_point("start")
    graph.add_edge("start", "spec")
    graph.add_edge("start", "analysis")
    graph.add_edge("start", "spec_graph")
    graph.add_edge("spec", "plan")
    graph.add_edge("analysis", "plan")
    graph.add_edge("spec_graph", "plan")
    graph.add_edge("plan", "generate")
    graph.add_edge("generate", "discrimination")
    graph.add_edge("discrimination", "metrics")
    graph.add_edge("metrics", "feedback")
    graph.add_conditional_edges(
        "feedback",
        should_refine,
        {"refine": "plan", "final": END},
    )
    return graph.compile()


def run_pipeline(
    *,
    problem: str,
    description: str,
    constraints: str,
    code: str,
    language: str,
    student_count: int,
    per_category: int,
    issues: List[str] | None = None,
) -> FinalReport:
    app = build_graph()
    state = app.invoke(
        {
            "problem": problem,
            "description": description,
            "constraints": constraints,
            "code": code,
            "language": language,
            "student_count": student_count,
            "per_category": per_category,
            "issues": issues or [],
        }
    )
    return FinalReport(
        spec=state["spec"],
        analysis=state["analysis"],
        plan=state["plan"],
        suites=state.get("suites", []),
        feedback=state["feedback"],
        meta={
            "spec_graph": state.get("spec_graph", SpecGraph()).model_dump(),
            "metrics": (state.get("metrics").to_dict() if state.get("metrics") else {}),
        },
    )
