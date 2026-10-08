"""Mutation analysis for test suite quality assessment.

Generates code mutants by applying well-known mutation operators to the
reference implementation, then measures how many mutants the generated
test suite can "kill" (detect).  A mutant is killed when the test case
produces a different output on the mutant compared to the original code.

This module provides the key novel contribution for the SpecTest-LLM
paper: *mutation-guided feedback*.  The mutation score (killed / total)
is a first-class quality signal used by both the metrics layer and the
feedback-driven regeneration loop.

Mutation operators implemented (based on the MuPy / PIT taxonomy):
  - Arithmetic Operator Replacement (AOR)
  - Relational Operator Replacement (ROR)
  - Logical Connector Replacement (LCR)
  - Boundary Value Perturbation (BVP)
  - Return Value Mutation (RVM)
  - Statement Deletion (SDL)
  - Conditional Negation (CNM)
  - Constant Replacement (CR)
"""

from __future__ import annotations

import ast
import copy
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from oracle import OracleResult, run_python_oracle
from schemas import TestCase

logger = logging.getLogger(__name__)

# Maximum number of mutants to generate (to keep latency reasonable).
MAX_MUTANTS = 30
# Timeout for executing each mutant per test case.
MUTANT_TIMEOUT_S = 1.5


# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------


# Each operator is a function: (source_code: str) -> List[(mutant_code, operator_name, description)]


def _arithmetic_operator_replacement(code: str) -> List[Tuple[str, str, str]]:
    """AOR: Replace +/- and *// with their counterparts."""
    mutants: List[Tuple[str, str, str]] = []
    swaps = [
        (r"(?<!=)\+(?!=)", "-", "AOR: + → -"),
        (r"(?<!<)(?<!>)-(?!>)(?!=)", "+", "AOR: - → +"),
        (r"\*(?!\*)", "/", "AOR: * → /"),
        (r"(?<!\*)//", "%", "AOR: // → %"),
    ]
    for pattern, replacement, desc in swaps:
        # Only replace first occurrence to keep mutants minimal
        result, count = re.subn(pattern, replacement, code, count=1)
        if count > 0 and result != code:
            mutants.append((result, "AOR", desc))
    return mutants


def _relational_operator_replacement(code: str) -> List[Tuple[str, str, str]]:
    """ROR: Replace relational operators."""
    mutants: List[Tuple[str, str, str]] = []
    swaps = [
        ("<=", "<", "ROR: <= → <"),
        (">=", ">", "ROR: >= → >"),
        ("==", "!=", "ROR: == → !="),
        ("!=", "==", "ROR: != → =="),
        (" < ", " <= ", "ROR: < → <="),
        (" > ", " >= ", "ROR: > → >="),
    ]
    for old, new, desc in swaps:
        if old in code:
            result = code.replace(old, new, 1)
            if result != code:
                mutants.append((result, "ROR", desc))
    return mutants


def _logical_connector_replacement(code: str) -> List[Tuple[str, str, str]]:
    """LCR: Replace logical connectors (and/or, not)."""
    mutants: List[Tuple[str, str, str]] = []
    if " and " in code:
        mutants.append((code.replace(" and ", " or ", 1), "LCR", "LCR: and → or"))
    if " or " in code:
        mutants.append((code.replace(" or ", " and ", 1), "LCR", "LCR: or → and"))
    return mutants


def _boundary_value_perturbation(code: str) -> List[Tuple[str, str, str]]:
    """BVP: Perturb constants by ±1 (off-by-one mutations)."""
    mutants: List[Tuple[str, str, str]] = []

    # Find integer literals and perturb by ±1
    # Skip 0 and 1 to avoid trivial/broken mutants
    int_pattern = re.compile(r"\b(\d+)\b")
    seen: set = set()
    for match in int_pattern.finditer(code):
        val = int(match.group(1))
        if val in seen or val > 10000:
            continue
        seen.add(val)
        # +1
        new_code = code[: match.start()] + str(val + 1) + code[match.end() :]
        if new_code != code:
            mutants.append(
                (new_code, "BVP", f"BVP: {val} → {val + 1}")
            )
        # -1 (only if positive result)
        if val > 0:
            new_code = code[: match.start()] + str(val - 1) + code[match.end() :]
            if new_code != code:
                mutants.append(
                    (new_code, "BVP", f"BVP: {val} → {val - 1}")
                )
        if len(mutants) >= 6:
            break
    return mutants


def _return_value_mutation(code: str) -> List[Tuple[str, str, str]]:
    """RVM: Mutate return values."""
    mutants: List[Tuple[str, str, str]] = []
    if "return True" in code:
        mutants.append(
            (code.replace("return True", "return False", 1), "RVM", "RVM: return True → False")
        )
    if "return False" in code:
        mutants.append(
            (code.replace("return False", "return True", 1), "RVM", "RVM: return False → True")
        )
    if "return 0" in code:
        mutants.append(
            (code.replace("return 0", "return 1", 1), "RVM", "RVM: return 0 → 1")
        )
    if "return -1" in code:
        mutants.append(
            (code.replace("return -1", "return 0", 1), "RVM", "RVM: return -1 → 0")
        )
    if "return []" in code:
        mutants.append(
            (code.replace("return []", "return [0]", 1), "RVM", "RVM: return [] → [0]")
        )
    if 'return ""' in code:
        mutants.append(
            (code.replace('return ""', 'return "x"', 1), "RVM", 'RVM: return "" → "x"')
        )
    if "return None" in code:
        mutants.append(
            (code.replace("return None", "return 0", 1), "RVM", "RVM: return None → 0")
        )
    return mutants


def _conditional_negation(code: str) -> List[Tuple[str, str, str]]:
    """CNM: Negate conditions in if/while/elif statements."""
    mutants: List[Tuple[str, str, str]] = []
    lines = code.split("\n")
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("if ", "elif ", "while ")) and ":" in stripped:
            indent = line[: len(line) - len(stripped)]
            keyword_end = stripped.index(" ") + 1
            keyword = stripped[:keyword_end]
            condition = stripped[keyword_end:].rstrip(":").strip()
            new_condition = f"not ({condition})"
            new_line = f"{indent}{keyword}{new_condition}:"
            new_lines = lines[:i] + [new_line] + lines[i + 1 :]
            mutants.append(
                ("\n".join(new_lines), "CNM", f"CNM: negate condition line {i + 1}")
            )
            if len(mutants) >= 3:
                break
    return mutants


def _statement_deletion(code: str) -> List[Tuple[str, str, str]]:
    """SDL: Replace a statement with `pass`."""
    mutants: List[Tuple[str, str, str]] = []
    lines = code.split("\n")
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        # Only delete meaningful statements (assignments, function calls)
        if (
            stripped
            and not stripped.startswith(("def ", "class ", "import ", "from ", "#", '"""', "'''"))
            and not stripped.startswith(("if ", "elif ", "else:", "while ", "for ", "try:", "except", "finally:"))
            and "=" in stripped or "(" in stripped
        ):
            indent = line[: len(line) - len(stripped)]
            new_lines = lines[:i] + [f"{indent}pass  # SDL mutant"] + lines[i + 1 :]
            mutants.append(
                ("\n".join(new_lines), "SDL", f"SDL: delete statement line {i + 1}")
            )
            if len(mutants) >= 3:
                break
    return mutants


# Registry of all mutation operators
MUTATION_OPERATORS: List[Callable[[str], List[Tuple[str, str, str]]]] = [
    _arithmetic_operator_replacement,
    _relational_operator_replacement,
    _logical_connector_replacement,
    _boundary_value_perturbation,
    _return_value_mutation,
    _conditional_negation,
    _statement_deletion,
]


# ---------------------------------------------------------------------------
# Mutant generation
# ---------------------------------------------------------------------------


@dataclass
class Mutant:
    """A single code mutant."""
    id: str
    code: str
    operator: str
    description: str
    killed: bool = False
    killed_by: Optional[str] = None  # case_id that killed it


def generate_mutants(
    code: str,
    *,
    max_mutants: int = MAX_MUTANTS,
) -> List[Mutant]:
    """Generate mutants by applying all registered operators."""
    mutants: List[Mutant] = []
    seen_codes: set = set()

    for operator_fn in MUTATION_OPERATORS:
        try:
            results = operator_fn(code)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Operator %s failed: %s", operator_fn.__name__, exc)
            continue
        for mutant_code, op_name, desc in results:
            # Deduplicate
            if mutant_code in seen_codes:
                continue
            seen_codes.add(mutant_code)
            # Validate that it's still parseable Python
            try:
                ast.parse(mutant_code)
            except SyntaxError:
                continue
            mutants.append(
                Mutant(
                    id=f"M{len(mutants) + 1:03d}-{op_name}",
                    code=mutant_code,
                    operator=op_name,
                    description=desc,
                )
            )
            if len(mutants) >= max_mutants:
                return mutants

    return mutants


# ---------------------------------------------------------------------------
# Mutation score computation
# ---------------------------------------------------------------------------


@dataclass
class MutationResult:
    """Aggregated mutation analysis result for a test suite."""
    total_mutants: int
    killed: int
    survived: int
    equivalent: int  # mutants that produce same output as original (possibly equivalent)
    mutation_score: float  # killed / (total - equivalent)
    mutant_details: List[Dict[str, Any]] = field(default_factory=list)
    surviving_mutants: List[Mutant] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mutants": self.total_mutants,
            "killed": self.killed,
            "survived": self.survived,
            "equivalent": self.equivalent,
            "mutation_score": round(self.mutation_score, 4),
            "surviving_operators": [m.operator for m in self.surviving_mutants],
            "surviving_descriptions": [m.description for m in self.surviving_mutants],
            "mutant_details": self.mutant_details[:20],  # Cap for report size
        }


def compute_mutation_score(
    cases: List[TestCase],
    *,
    reference_code: str,
    entry: str,
    call_style: str = "args_list",
    timeout_s: float = MUTANT_TIMEOUT_S,
    max_mutants: int = MAX_MUTANTS,
) -> MutationResult:
    """Run all test cases against all mutants and compute the mutation score.

    For each mutant:
    1. Run the reference code on each test input → ref_output
    2. Run the mutant code on each test input → mut_output
    3. If ref_output ≠ mut_output for any test → mutant is KILLED
    4. If ref_output == mut_output for ALL tests → mutant SURVIVED

    mutation_score = killed / (total - equivalent)
    """
    if not reference_code.strip() or not entry or not cases:
        return MutationResult(0, 0, 0, 0, 0.0)

    mutants = generate_mutants(reference_code, max_mutants=max_mutants)
    if not mutants:
        return MutationResult(0, 0, 0, 0, 0.0)

    # Pre-compute reference outputs for all cases
    ref_outputs: Dict[str, Any] = {}
    ref_errors: set = set()
    for case in cases:
        payload = case.input if isinstance(case.input, list) else [case.input]
        ref = run_python_oracle(
            reference_code, entry, payload,
            call_style=call_style, timeout_s=timeout_s,
        )
        if ref.success:
            ref_outputs[case.id] = ref.value
        else:
            ref_errors.add(case.id)

    usable_cases = [c for c in cases if c.id in ref_outputs]
    if not usable_cases:
        return MutationResult(len(mutants), 0, len(mutants), 0, 0.0)

    killed = 0
    survived = 0
    equivalent = 0
    details: List[Dict[str, Any]] = []
    surviving: List[Mutant] = []

    for mutant in mutants:
        mutant_killed = False
        killed_by_case = None
        all_same = True

        for case in usable_cases:
            payload = case.input if isinstance(case.input, list) else [case.input]
            mut_result = run_python_oracle(
                mutant.code, entry, payload,
                call_style=call_style, timeout_s=timeout_s,
            )
            if not mut_result.success:
                # Mutant crashed → counts as killed (the test detected the fault)
                mutant_killed = True
                killed_by_case = case.id
                all_same = False
                break

            if mut_result.value != ref_outputs[case.id]:
                mutant_killed = True
                killed_by_case = case.id
                all_same = False
                break

        if mutant_killed:
            killed += 1
            mutant.killed = True
            mutant.killed_by = killed_by_case
        else:
            if all_same:
                # Could be an equivalent mutant
                equivalent += 1
            survived += 1
            surviving.append(mutant)

        details.append({
            "mutant_id": mutant.id,
            "operator": mutant.operator,
            "description": mutant.description,
            "killed": mutant_killed,
            "killed_by": killed_by_case,
        })

    denominator = len(mutants) - equivalent
    score = killed / denominator if denominator > 0 else 1.0

    return MutationResult(
        total_mutants=len(mutants),
        killed=killed,
        survived=survived,
        equivalent=equivalent,
        mutation_score=score,
        mutant_details=details,
        surviving_mutants=surviving,
    )


def surviving_mutant_hints(result: MutationResult) -> List[str]:
    """Generate human-readable hints about surviving mutants.

    These hints are fed back to the LLM test generator to produce
    tests that target the specific mutation types that survived.
    This is the core of mutation-guided regeneration.
    """
    hints: List[str] = []
    op_counts: Dict[str, int] = {}
    for m in result.surviving_mutants:
        op_counts[m.operator] = op_counts.get(m.operator, 0) + 1

    operator_hints = {
        "AOR": "Generate cases where arithmetic operations (+, -, *, /) produce visibly different results. "
               "Test with inputs where swapping + and - or * and / gives wrong answers.",
        "ROR": "Generate cases at exact boundary thresholds where < vs <= or > vs >= makes a difference. "
               "Focus on inputs at the exact boundary value.",
        "LCR": "Generate cases where both conditions in an 'and'/'or' expression matter. "
               "One condition should be True while the other is False.",
        "BVP": "Generate cases using exact boundary values (n=0, n=1, n=max, n=max-1). "
               "Off-by-one errors are not being caught.",
        "RVM": "Generate cases where the return value itself is the differentiator. "
               "Include cases that should return empty, zero, False, or None.",
        "CNM": "Generate cases where the condition in if/while statements is decisive. "
               "Include cases that should take both the true and false branches.",
        "SDL": "Generate cases that exercise every statement in the function. "
               "Ensure no dead code can be deleted without affecting output.",
    }

    for op, count in sorted(op_counts.items(), key=lambda x: -x[1]):
        hint = operator_hints.get(op, f"Target mutations of type {op}.")
        hints.append(f"[{op} — {count} surviving mutant(s)] {hint}")

    return hints
