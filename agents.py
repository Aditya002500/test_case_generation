from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from schemas import CodeAnalysis, FeedbackSignal, Spec, TestCaseList, TestPlan


SYSTEM_JSON_ONLY = (
    "You are a precise component of a multi-agent test generation system. "
    "Respond with a single JSON object that matches the requested schema. "
    "Do not wrap the JSON in markdown code fences. Do not add commentary."
)


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------

CATEGORY_RUBRIC = """Category definitions (use these VERBATIM):
- "Basic cases": typical in-distribution inputs that should pass for any correct solution.
- "Boundary cases": inputs at the *minimum* or *maximum* of the constraint range (n=lo, n=hi, len(s)=1, len(s)=max, etc.).
- "Random cases": in-distribution inputs chosen without a specific boundary or invariant in mind.
- "Stress cases": inputs that exercise size or complexity, typically near the upper bound or larger.
- "Invalid/robustness cases": inputs that VIOLATE the stated constraints or test error handling (empty where min>=1, negative where non-negative required, wrong type, malformed, etc.).
- "Bug-targeted cases": inputs that specifically probe a common bug class (off-by-one, sign error, wrong operator, palindrome trap, null vs empty, etc.)."""


def build_spec_agent(llm):
    parser = PydanticOutputParser(pydantic_object=Spec)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_JSON_ONLY),
            (
                "human",
                "Extract a structured specification from the problem statement below.\n\n"
                "Problem statement:\n{problem}\n\n"
                "User-provided description:\n{description}\n\n"
                "User-provided constraints:\n{constraints}\n\n"
                "Language: {language}\n\n"
                "If fields are missing, infer sensible defaults rather than refusing. "
                "Only return JSON. {format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_code_analysis_agent(llm):
    parser = PydanticOutputParser(pydantic_object=CodeAnalysis)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_JSON_ONLY),
            (
                "human",
                "Analyse the supplied source code for risks and assumptions. "
                "Do not execute the code; reason from the source alone.\n\n"
                "Language: {language}\n\n"
                "Code:\n{code}\n\n"
                "If you cannot find loops, conditions, risks, or assumptions, "
                "return empty lists rather than guessing. {format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_spec_graph_agent(llm):
    """Extracts a typed input/output spec graph.

    The JSON schema is passed as a runtime-substituted variable, not embedded
    in the template, so the braces never collide with the f-string parser.
    """
    from spec_graph import SPEC_GRAPH_PROMPT_TEMPLATE

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_JSON_ONLY),
            ("human", "{spec_graph_input}"),
        ]
    )
    return prompt.partial(spec_graph_input=SPEC_GRAPH_PROMPT_TEMPLATE)


def build_test_plan_agent(llm):
    parser = PydanticOutputParser(pydantic_object=TestPlan)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_JSON_ONLY),
            (
                "human",
                "Design a balanced test plan that covers six categories. "
                "Use these exact category names:\n" + CATEGORY_RUBRIC + "\n\n"
                "Spec:\n{spec}\n\n"
                "Spec graph (typed dimensions and boundaries):\n{spec_graph}\n\n"
                "Code analysis:\n{analysis}\n\n"
                "Issues detected in a previous iteration (if any):\n{issues}\n\n"
                "Desired per-category count: {per_category}\n\n"
                "Return only the JSON plan. {format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_feedback_agent(llm):
    parser = PydanticOutputParser(pydantic_object=FeedbackSignal)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_JSON_ONLY),
            (
                "human",
                "Evaluate whether the plan addresses the specification. "
                "Set needs_refine=true only if the plan is fundamentally "
                "insufficient; minor wording issues are fine.\n\n"
                "Spec:\n{spec}\n\n"
                "Plan:\n{plan}\n\n"
                "Detected issues so far:\n{issues}\n\n"
                "{format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_test_generator_agent(llm):
    parser = PydanticOutputParser(pydantic_object=TestCaseList)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                SYSTEM_JSON_ONLY
                + " Every case must be self-contained JSON literal values; "
                "no expressions, no JavaScript, no function calls, no `.repeat`, "
                "no concatenation operators, no `null` placeholders for input. "
                "Keep every string <= 200 characters. Do not echo the spec. "
                "Numeric values must be JSON numbers (NOT quoted strings). "
                "For integer dimensions, write them as raw integers: 0, -5, 42, 100. "
                "Never wrap them in quotes.",
            ),
            (
                "human",
                "Generate test cases for student {student_id} of {student_count}.\n\n"
                "Spec:\n{spec}\n\n"
                "Plan with per-category targets:\n{plan}\n\n"
                "Spec graph (concrete boundary values per dimension):\n{spec_graph}\n\n"
                "CATEGORY RUBRIC (use these EXACT category names):\n"
                + CATEGORY_RUBRIC
                + "\n\n"
                "IMPORTANT: You are generating cases for STUDENT {student_id}. "
                "The cases must look like a different student generated them: "
                "different numeric values, different string content, different edge cases. "
                "If previous students already used these inputs, you MUST pick different ones:\n"
                "{anti_examples}\n\n"
                "Produce exactly the number of cases specified by plan.targets for each of the "
                "six categories. Each input must conform to the spec's input_format. Each "
                "expected value must be the correct output for the given input (it will be "
                "cross-checked against an oracle). Write a one-sentence explanation per case.\n\n"
                "{format_instructions}",
            ),
        ]
    )
    return prompt, parser
