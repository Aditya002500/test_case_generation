from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from schemas import CodeAnalysis, FeedbackSignal, Spec, TestCaseList, TestPlan


def build_spec_agent(llm):
    parser = PydanticOutputParser(pydantic_object=Spec)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract structured requirements from problem statements. "
                "Return JSON only that matches the schema. No markdown.",
            ),
            (
                "human",
                "Problem statement:\n{problem}\n\n"
                "User-provided description:\n{description}\n\n"
                "User-provided constraints:\n{constraints}\n\n"
                "Language: {language}\n\n"
                "{format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_code_analysis_agent(llm):
    parser = PydanticOutputParser(pydantic_object=CodeAnalysis)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Analyze code behavior and risks. Return JSON only. No markdown.",
            ),
            (
                "human",
                "Language: {language}\n\nCode:\n{code}\n\n{format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_test_plan_agent(llm):
    parser = PydanticOutputParser(pydantic_object=TestPlan)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Create a structured testing plan with targets per category. "
                "Return JSON only. No markdown.",
            ),
            (
                "human",
                "Spec:\n{spec}\n\nCode analysis:\n{analysis}\n\n"
                "Known issues from previous iteration:\n{issues}\n\n"
                "Required categories: Basic cases, boundary cases, random cases, "
                "stress cases, invalid/robustness cases, bug-targeted cases.\n"
                "Desired per-category count: {per_category}\n\n"
                "{format_instructions}",
            ),
        ]
    )
    return prompt, parser


def build_feedback_agent(llm):
    parser = PydanticOutputParser(pydantic_object=FeedbackSignal)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Assess test plan quality. Return JSON only. No markdown.",
            ),
            (
                "human",
                "Spec:\n{spec}\n\nPlan:\n{plan}\n\n"
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
                "Generate concrete test cases. Use plan.targets for counts. "
                "Return JSON only. No markdown. "
                "Do not use code, expressions, or functions. "
                "All values must be literal JSON (strings, numbers, arrays, objects). "
                "Do not use repeat or operators. "
                "Keep any single string length <= 200 characters.",
            ),
            (
                "human",
                "Spec:\n{spec}\n\nPlan:\n{plan}\n\n"
                "Student index: {student_id}\n\n"
                "{format_instructions}",
            ),
        ]
    )
    return prompt, parser
