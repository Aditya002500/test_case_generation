"""Spec-Graph: typed input dimensions, boundaries, and invariants.

The spec is a natural-language description. To reason about coverage
principled, we extract a small typed graph:

    InputPositionalArgs: [Dimension(name='n', type='integer', bounds=(1, 100)), ...]
    ReturnType: list[str]
    Invariants: ["len(result) == n", "result[i] in {'Fizz','Buzz','FizzBuzz',str(i+1)}"]
    SemanticBoundaries: per-dimension concrete boundary values

The LLM fills in the dimension list and invariants (validated as JSON); we
compute concrete boundary values deterministically.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Dimension(BaseModel):
    name: str
    type: str  # "integer", "string", "list_int", "list_str", "boolean"
    role: str = "input"  # "input", "output_length", "return_type_hint"
    min: Optional[float] = None
    max: Optional[float] = None
    semantic_boundaries: List[Any] = Field(default_factory=list)
    description: str = ""


class Invariant(BaseModel):
    text: str
    kind: str = "postcondition"  # "postcondition", "precondition", "relation"


class SpecGraph(BaseModel):
    function_signature: str = ""
    call_style: str = "args_list"  # "args_list" | "kwargs" | "stdin_single_arg"
    dimensions: List[Dimension] = Field(default_factory=list)
    invariants: List[Invariant] = Field(default_factory=list)
    return_type: str = "any"
    raw: Dict[str, Any] = Field(default_factory=dict)

    def coverage_targets(self, per_category: int) -> Dict[str, List[Any]]:
        """Per-category concrete boundary samples to seed the generator."""
        out: Dict[str, List[Any]] = {}
        for d in self.dimensions:
            if d.role != "input":
                continue
            out[d.name] = self._sample(d, per_category)
        return out

    def _sample(self, dim: Dimension, n: int) -> List[Any]:
        samples: List[Any] = []
        if dim.semantic_boundaries:
            samples.extend(dim.semantic_boundaries[:n])
        if (
            dim.type in ("integer", "list_int")
            and dim.min is not None
            and dim.max is not None
        ):
            lo, hi = int(dim.min), int(dim.max)
            candidates: List[int] = []
            for offset, value in enumerate([lo, lo + 1, (lo + hi) // 2, hi - 1, hi]):
                if lo <= value <= hi and value not in candidates:
                    candidates.append(value)
            samples.extend(candidates[: max(0, n - len(samples))])
        # Dedup, preserve order, cap at n
        seen: set = set()
        uniq: List[Any] = []
        for s in samples:
            key = json.dumps(s, default=str, sort_keys=True)
            if key not in seen:
                seen.add(key)
                uniq.append(s)
            if len(uniq) >= n:
                break
        return uniq

    def coverage_pct(self, cases: List[Dict[str, Any]]) -> float:
        """Fraction of dimensions represented by at least one boundary sample in `cases`."""
        if not self.dimensions:
            return 0.0
        input_dims = [d for d in self.dimensions if d.role == "input"]
        if not input_dims:
            return 0.0
        covered = 0
        for d in input_dims:
            targets = self._sample(d, 4)
            for case in cases:
                v = self._extract_dim(case.get("input"), d.name, input_dims, d)
                if v is None:
                    continue
                for t in targets:
                    if self._values_match(v, t):
                        covered += 1
                        break
                else:
                    continue
                break
        return covered / len(input_dims)

    @staticmethod
    def _extract_dim(payload: Any, name: str, input_dims: list, dim) -> Any:
        if isinstance(payload, dict):
            return payload.get(name)
        # Single-scalar payload: there's one input dim, take the value as-is.
        if len(input_dims) == 1:
            return payload
        # Positional list payload: match by index in input_dims order.
        if isinstance(payload, list):
            for i, d in enumerate(input_dims):
                if d.name == name and i < len(payload):
                    return payload[i]
        return None

    @staticmethod
    def _values_match(a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(a - b) <= max(1.0, 0.05 * abs(b))
        return a == b


SPEC_GRAPH_SCHEMA = {
    "function_signature": "python-style signature, e.g. 'def two_sum(nums: list[int], target: int) -> list[int]'",
    "call_style": "args_list | kwargs | stdin_single_arg",
    "dimensions": [
        {
            "name": "n",
            "type": "integer | string | list_int | list_str | boolean",
            "role": "input | output_length | return_type_hint",
            "min": "number or null",
            "max": "number or null",
            "semantic_boundaries": ["concrete values"],
            "description": "short purpose",
        }
    ],
    "invariants": [
        {
            "text": "human-readable invariant",
            "kind": "postcondition | precondition | relation",
        }
    ],
    "return_type": "integer | string | list_int | list_str | boolean | any",
}


SPEC_GRAPH_PROMPT_TEMPLATE = """You are extracting a structured input/output spec for a programming problem.
Return ONLY a JSON object that matches the schema below. No commentary, no markdown.

Schema (a JSON object with these keys):
{schema}

Now process the following problem and respond with the JSON object only.

Problem:
{problem}

Description:
{description}

Constraints:
{constraints}

Language: {language}
""".strip()


def spec_graph_prompt(
    problem: str, description: str, constraints: str, language: str
) -> str:
    return SPEC_GRAPH_PROMPT_TEMPLATE.format(
        schema=json.dumps(SPEC_GRAPH_SCHEMA, indent=2),
        problem=problem or "",
        description=description or "",
        constraints=constraints or "",
        language=language or "python",
    )


_NUMERIC_RE = re.compile(r"(-?\d+(?:\.\d+)?(?:e-?\d+)?)")


def _extract_numeric_bounds(text: str) -> Tuple[Optional[float], Optional[float]]:
    nums = [float(m) for m in _NUMERIC_RE.findall(text or "")]
    if not nums:
        return None, None
    return min(nums), max(nums)


def build_spec_graph_from_llm_text(
    raw: Any, fallback: Optional[SpecGraph] = None
) -> SpecGraph:
    """Parse the LLM's JSON output into a SpecGraph with safe fallback."""
    if not raw:
        return fallback or SpecGraph()
    if not isinstance(raw, str):
        try:
            text = json.dumps(raw)
        except (TypeError, ValueError):
            return fallback or SpecGraph()
    else:
        text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return fallback or SpecGraph()
    if not isinstance(data, dict):
        return fallback or SpecGraph()
    try:
        return SpecGraph(
            function_signature=str(data.get("function_signature", "")),
            call_style=str(data.get("call_style", "args_list")),
            dimensions=[
                Dimension(**{k: v for k, v in d.items() if k in Dimension.model_fields})
                for d in data.get("dimensions", [])
                if isinstance(d, dict)
            ],
            invariants=[
                Invariant(**{k: v for k, v in i.items() if k in Invariant.model_fields})
                for i in data.get("invariants", [])
                if isinstance(i, dict)
            ],
            return_type=str(data.get("return_type", "any")),
            raw=data,
        )
    except Exception:  # noqa: BLE001
        return fallback or SpecGraph()


def fallback_spec_graph(problem: str, constraints: str) -> SpecGraph:
    """Heuristic fallback when the LLM extraction fails. Looks for n, m ranges."""
    lo, hi = _extract_numeric_bounds(constraints or problem or "")
    if lo is None and hi is None:
        return SpecGraph()
    return SpecGraph(
        dimensions=[
            Dimension(
                name="n",
                type="integer",
                role="input",
                min=lo,
                max=hi,
                semantic_boundaries=[lo, hi]
                if lo is not None and hi is not None
                else [],
                description="auto-extracted size range",
            )
        ],
    )
