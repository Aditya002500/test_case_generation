from __future__ import annotations

import json
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from agents import (
    build_code_analysis_agent,
    build_feedback_agent,
    build_spec_agent,
    build_test_generator_agent,
    build_test_plan_agent,
)
from llms import build_llm
from schemas import (
    CodeAnalysis,
    FeedbackSignal,
    FinalReport,
    Spec,
    StudentTestSuite,
    TestCaseList,
    TestCase,
    TestPlan,
)


class GraphState(TypedDict):
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
    plan: TestPlan
    suites: List[StudentTestSuite]
    feedback: FeedbackSignal
    issues: List[str]


def _category_targets(per_category: int) -> Dict[str, int]:
    categories = [
        "Basic cases",
        "Boundary cases",
        "Random cases",
        "Stress cases",
        "Invalid/robustness cases",
        "Bug-targeted cases",
    ]
    return {category: per_category for category in categories}


def _normalize_category(label: str) -> str:
    lower = label.strip().lower()
    if "basic" in lower:
        return "Basic cases"
    if "boundary" in lower or "edge" in lower:
        return "Boundary cases"
    if "random" in lower:
        return "Random cases"
    if "stress" in lower:
        return "Stress cases"
    if "invalid" in lower or "robust" in lower:
        return "Invalid/robustness cases"
    if "bug" in lower:
        return "Bug-targeted cases"
    return label


def _enforce_targets(
    cases: List[TestCase], targets: Dict[str, int]
) -> tuple[List[TestCase], Dict[str, int]]:
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


def _strip_markdown(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
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


def _tokenize_expr(expr: str) -> List[tuple[str, Any]] | None:
    tokens: List[tuple[str, Any]] = []
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

    def parse_term(pos: int) -> tuple[str | None, int]:
        if pos >= len(tokens):
            return None, pos
        if tokens[pos][0] == "str":
            value = tokens[pos][1]
        elif tokens[pos][0] == "int":
            value = str(tokens[pos][1])
        else:
            return None, pos
        pos += 1
        while pos + 1 < len(tokens) and tokens[pos] == ("op", "*"):
            if tokens[pos + 1][0] != "int":
                return None, pos
            repeat = tokens[pos + 1][1]
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


def _parse_case_list(raw_text: str) -> TestCaseList:
    cleaned = _strip_markdown(raw_text)
    rewritten = _rewrite_repeat_calls(cleaned)
    repaired = _replace_string_expressions(rewritten)
    blob = _extract_json_blob(repaired)
    try:
        data = json.loads(blob)
        if isinstance(data, list):
            data = {"cases": data}
        return TestCaseList.model_validate(data)
    except json.JSONDecodeError:
        return TestCaseList(cases=[])


def node_spec(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3-flash-preview", temperature=0.2)
    prompt, parser = build_spec_agent(llm)
    chain = prompt | llm | parser
    spec = chain.invoke(
        {
            "problem": state["problem"],
            "description": state["description"],
            "constraints": state["constraints"],
            "language": state["language"],
            "format_instructions": parser.get_format_instructions(),
        }
    )
    return {"spec": spec}


def node_analysis(state: GraphState) -> Dict[str, Any]:
    if not state["code"].strip():
        return {"analysis": CodeAnalysis()}
    llm = build_llm("gemini-2.5-flash", temperature=0.2)
    prompt, parser = build_code_analysis_agent(llm)
    chain = prompt | llm | parser
    analysis = chain.invoke(
        {
            "code": state["code"],
            "language": state["language"],
            "format_instructions": parser.get_format_instructions(),
        }
    )
    return {"analysis": analysis}


def node_start(state: GraphState) -> Dict[str, Any]:
    return {"iteration": 0}


def node_plan(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3.1-flash-lite-preview", temperature=0.3)
    prompt, parser = build_test_plan_agent(llm)
    chain = prompt | llm | parser
    per_category = max(2, min(3, state["per_category"]))
    plan = chain.invoke(
        {
            "spec": state["spec"].model_dump(),
            "analysis": state["analysis"].model_dump(),
            "issues": state.get("issues", []),
            "per_category": per_category,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    plan.targets = _category_targets(per_category)
    plan.categories = list(plan.targets.keys())
    return {"plan": plan}


def node_generate(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-2.5-flash-lite", temperature=0.5)
    prompt, parser = build_test_generator_agent(llm)
    chain = prompt | llm
    suites: List[StudentTestSuite] = []
    issues: List[str] = []
    for student_id in range(1, state["student_count"] + 1):
        response = chain.invoke(
            {
                "spec": state["spec"].model_dump(),
                "plan": state["plan"].model_dump(),
                "student_id": student_id,
                "format_instructions": parser.get_format_instructions(),
            }
        )
        raw_text = response.content if hasattr(response, "content") else str(response)
        case_list = _parse_case_list(raw_text)
        if not case_list.cases:
            issues.append(f"Student {student_id} output parsing failed")
            continue
        enforced, missing = _enforce_targets(case_list.cases, state["plan"].targets)
        suites.append(StudentTestSuite(student_id=student_id, cases=enforced))
        if missing:
            issues.append(
                f"Student {student_id} missing categories: {sorted(missing.keys())}"
            )
    return {"suites": suites, "issues": issues}


def node_feedback(state: GraphState) -> Dict[str, Any]:
    llm = build_llm("gemini-3-flash-preview", temperature=0.2)
    prompt, parser = build_feedback_agent(llm)
    chain = prompt | llm | parser
    issues = state.get("issues", [])
    feedback = chain.invoke(
        {
            "spec": state["spec"].model_dump(),
            "plan": state["plan"].model_dump(),
            "issues": issues,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    needs_refine = feedback.needs_refine or bool(issues)
    iteration = state.get("iteration", 0) + (1 if needs_refine else 0)
    return {"feedback": feedback, "iteration": iteration}


def should_refine(state: GraphState) -> str:
    max_refines = 1
    if state.get("iteration", 0) > max_refines:
        return "final"
    if state.get("issues"):
        return "refine"
    return "refine" if state["feedback"].needs_refine else "final"


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("start", node_start)
    graph.add_node("spec", node_spec)
    graph.add_node("analysis", node_analysis)
    graph.add_node("plan", node_plan)
    graph.add_node("generate", node_generate)
    graph.add_node("feedback", node_feedback)

    graph.set_entry_point("start")
    graph.add_edge("start", "spec")
    graph.add_edge("start", "analysis")
    graph.add_edge("spec", "plan")
    graph.add_edge("analysis", "plan")
    graph.add_edge("plan", "generate")
    graph.add_edge("generate", "feedback")
    graph.add_conditional_edges(
        "feedback",
        should_refine,
        {
            "refine": "plan",
            "final": END,
        },
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
        suites=state["suites"],
        feedback=state["feedback"],
    )
