from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Spec(BaseModel):
    problem_summary: str
    input_format: str
    output_format: str
    constraints: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    hidden_cases: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class CodeAnalysis(BaseModel):
    loops: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class TestPlan(BaseModel):
    categories: List[str]
    targets: Dict[str, int]
    strategy_notes: List[str] = Field(default_factory=list)


class TestCase(BaseModel):
    category: str
    input: Any
    expected: Optional[Any] = None
    explanation: str


class TestCaseList(BaseModel):
    cases: List[TestCase]


class StudentTestSuite(BaseModel):
    student_id: int
    cases: List[TestCase]


class FeedbackSignal(BaseModel):
    needs_refine: bool
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    spec: Spec
    analysis: CodeAnalysis
    plan: TestPlan
    suites: List[StudentTestSuite]
    feedback: FeedbackSignal
