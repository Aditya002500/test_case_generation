"""Experiment runner for the SpecTest-LLM paper evaluation.

Runs the full pipeline and baselines across a curated benchmark suite
and collects all 8 metrics for statistical comparison.

Usage:
    python experiments.py                  # Run full benchmark
    python experiments.py --baseline-only  # Run only baselines
    python experiments.py --problems 5     # Limit to first N problems

Results are saved as CSV in experiments_results/ for direct inclusion
in the paper's results table.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Benchmark Problem Suite
# ---------------------------------------------------------------------------

BENCHMARK_PROBLEMS: List[Dict[str, Any]] = [
    # --- Arithmetic ---
    {
        "id": "P01",
        "domain": "arithmetic",
        "problem": "Two Sum: Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice. Return the answer in ascending order.",
        "description": "Classic hash-map interview question.",
        "constraints": "2 <= nums.length <= 10^4, -10^9 <= nums[i] <= 10^9, -10^9 <= target <= 10^9",
        "code": "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return sorted([seen[target - n], i])\n        seen[n] = i\n    return []",
        "language": "python",
    },
    {
        "id": "P02",
        "domain": "arithmetic",
        "problem": "FizzBuzz: Given an integer n, return a list of strings from 1 to n. For multiples of 3 return 'Fizz', for multiples of 5 return 'Buzz', for multiples of both return 'FizzBuzz', otherwise return the number as a string.",
        "description": "Classic FizzBuzz problem.",
        "constraints": "1 <= n <= 10^4",
        "code": "def fizzbuzz(n):\n    result = []\n    for i in range(1, n + 1):\n        if i % 15 == 0:\n            result.append('FizzBuzz')\n        elif i % 3 == 0:\n            result.append('Fizz')\n        elif i % 5 == 0:\n            result.append('Buzz')\n        else:\n            result.append(str(i))\n    return result",
        "language": "python",
    },
    {
        "id": "P03",
        "domain": "arithmetic",
        "problem": "GCD: Given two non-negative integers a and b, return their greatest common divisor. If both are 0, return 0.",
        "description": "Euclidean algorithm for GCD.",
        "constraints": "0 <= a, b <= 10^9",
        "code": "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a",
        "language": "python",
    },
    # --- String Manipulation ---
    {
        "id": "P04",
        "domain": "string",
        "problem": "Palindrome Check: Given a string s, determine if it is a palindrome, considering only alphanumeric characters and ignoring case. Return True if palindrome, False otherwise.",
        "description": "LeetCode-style string problem.",
        "constraints": "1 <= |s| <= 2*10^5",
        "code": "def is_palindrome(s):\n    t = ''.join(c.lower() for c in s if c.isalnum())\n    return t == t[::-1]",
        "language": "python",
    },
    {
        "id": "P05",
        "domain": "string",
        "problem": "Anagram Check: Given two strings s and t, return True if t is an anagram of s, and False otherwise. An anagram uses exactly the same characters, the same number of times.",
        "description": "Character frequency comparison.",
        "constraints": "1 <= |s|, |t| <= 5*10^4, s and t consist of lowercase English letters",
        "code": "def is_anagram(s, t):\n    if len(s) != len(t):\n        return False\n    from collections import Counter\n    return Counter(s) == Counter(t)",
        "language": "python",
    },
    {
        "id": "P06",
        "domain": "string",
        "problem": "Reverse Words: Given a string s, reverse the order of words. A word is a sequence of non-space characters. Return a string of the words in reverse order concatenated by a single space.",
        "description": "String splitting and reversal.",
        "constraints": "1 <= |s| <= 10^4, s contains English letters, digits, and spaces",
        "code": "def reverse_words(s):\n    return ' '.join(s.split()[::-1])",
        "language": "python",
    },
    # --- Dynamic Programming ---
    {
        "id": "P07",
        "domain": "dp",
        "problem": "Fibonacci: Given n, return the nth Fibonacci number. F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1.",
        "description": "Classic DP / memoization problem.",
        "constraints": "0 <= n <= 30",
        "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
        "language": "python",
    },
    {
        "id": "P08",
        "domain": "dp",
        "problem": "Climbing Stairs: You are climbing a staircase. It takes n steps to reach the top. Each time you can either climb 1 or 2 steps. Return how many distinct ways you can climb to the top.",
        "description": "DP with Fibonacci pattern.",
        "constraints": "1 <= n <= 45",
        "code": "def climb_stairs(n):\n    if n <= 2:\n        return n\n    a, b = 1, 2\n    for _ in range(3, n + 1):\n        a, b = b, a + b\n    return b",
        "language": "python",
    },
    {
        "id": "P09",
        "domain": "dp",
        "problem": "Maximum Subarray: Given an integer array nums, find the contiguous subarray which has the largest sum and return its sum.",
        "description": "Kadane's algorithm.",
        "constraints": "1 <= nums.length <= 10^5, -10^4 <= nums[i] <= 10^4",
        "code": "def max_subarray(nums):\n    max_sum = curr_sum = nums[0]\n    for n in nums[1:]:\n        curr_sum = max(n, curr_sum + n)\n        max_sum = max(max_sum, curr_sum)\n    return max_sum",
        "language": "python",
    },
    # --- Searching & Sorting ---
    {
        "id": "P10",
        "domain": "search",
        "problem": "Binary Search: Given a sorted array of distinct integers and a target, return the index of target or -1 if not found. The array is 0-indexed.",
        "description": "Standard divide-and-conquer search.",
        "constraints": "1 <= n <= 10^5, array is strictly increasing",
        "code": "def binary_search(nums, target):\n    lo, hi = 0, len(nums) - 1\n    while lo <= hi:\n        mid = lo + (hi - lo) // 2\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1",
        "language": "python",
    },
    {
        "id": "P11",
        "domain": "search",
        "problem": "Find Minimum in Rotated Sorted Array: Given a sorted rotated array of unique elements, return the minimum element.",
        "description": "Modified binary search.",
        "constraints": "1 <= n <= 5000, -5000 <= nums[i] <= 5000, all values are unique",
        "code": "def find_min(nums):\n    lo, hi = 0, len(nums) - 1\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if nums[mid] > nums[hi]:\n            lo = mid + 1\n        else:\n            hi = mid\n    return nums[lo]",
        "language": "python",
    },
    # --- Data Structures ---
    {
        "id": "P12",
        "domain": "data_structures",
        "problem": "Valid Parentheses: Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type in the correct order.",
        "description": "Stack-based bracket matching.",
        "constraints": "1 <= |s| <= 10^4",
        "code": "def is_valid(s):\n    stack = []\n    mapping = {')': '(', '}': '{', ']': '['}\n    for c in s:\n        if c in mapping:\n            if not stack or stack[-1] != mapping[c]:\n                return False\n            stack.pop()\n        else:\n            stack.append(c)\n    return not stack",
        "language": "python",
    },
    {
        "id": "P13",
        "domain": "data_structures",
        "problem": "Remove Duplicates from Sorted Array: Given a sorted array nums, remove the duplicates in-place such that each element appears only once and return the new length.",
        "description": "Two-pointer technique.",
        "constraints": "1 <= nums.length <= 3*10^4, -100 <= nums[i] <= 100",
        "code": "def remove_duplicates(nums):\n    if not nums:\n        return 0\n    write = 1\n    for i in range(1, len(nums)):\n        if nums[i] != nums[i - 1]:\n            nums[write] = nums[i]\n            write += 1\n    return write",
        "language": "python",
    },
    # --- Math ---
    {
        "id": "P14",
        "domain": "math",
        "problem": "Power of Two: Given an integer n, return True if it is a power of two, otherwise return False. An integer n is a power of two if there exists an integer x such that n == 2^x.",
        "description": "Bit manipulation check.",
        "constraints": "-2^31 <= n <= 2^31 - 1",
        "code": "def is_power_of_two(n):\n    return n > 0 and (n & (n - 1)) == 0",
        "language": "python",
    },
    {
        "id": "P15",
        "domain": "math",
        "problem": "Roman to Integer: Given a roman numeral string, convert it to an integer. Input is guaranteed to be within the range from 1 to 3999.",
        "description": "Symbol to value mapping with subtraction rule.",
        "constraints": "1 <= |s| <= 15, s contains only the characters I, V, X, L, C, D, M",
        "code": "def roman_to_int(s):\n    val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n    result = 0\n    for i in range(len(s)):\n        if i + 1 < len(s) and val[s[i]] < val[s[i + 1]]:\n            result -= val[s[i]]\n        else:\n            result += val[s[i]]\n    return result",
        "language": "python",
    },
]


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------


@dataclass
class ExperimentResult:
    problem_id: str
    domain: str
    method: str  # "single_prompt", "multi_agent_no_oracle", "spectest_llm_full"
    n_cases: int = 0
    coverage_pct: float = 0.0
    oracle_match_rate: float = 0.0
    discrimination_mean: float = 0.0
    inter_diversity: float = 0.0
    mutation_score: float = 0.0
    parsing_success: bool = True
    duration_s: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Baseline: Single-prompt LLM
# ---------------------------------------------------------------------------


def run_single_prompt_baseline(problem: Dict[str, Any]) -> ExperimentResult:
    """Baseline 1: Single prompt, no multi-agent, no oracle."""
    from llms import build_llm

    start = time.time()
    try:
        llm = build_llm(temperature=0.5)
        prompt = (
            f"Generate 12 test cases for this programming problem. "
            f"For each test case, provide the input and expected output as JSON.\n\n"
            f"Problem: {problem['problem']}\n"
            f"Constraints: {problem['constraints']}\n\n"
            f"Return a JSON object with a 'cases' key containing a list of objects, "
            f"each with 'category', 'input', 'expected', and 'explanation' fields.\n"
            f"Categories: Basic cases, Boundary cases, Random cases, Stress cases, "
            f"Invalid/robustness cases, Bug-targeted cases.\n"
            f"Produce 2 cases per category."
        )
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)

        # Try to parse
        import re
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw.strip(), re.DOTALL)
        if fence:
            raw = fence.group(1)
        start_obj = raw.find("{")
        end_obj = raw.rfind("}")
        if start_obj != -1 and end_obj != -1:
            raw = raw[start_obj:end_obj + 1]

        data = json.loads(raw)
        cases = data.get("cases", []) if isinstance(data, dict) else data
        n_cases = len(cases) if isinstance(cases, list) else 0

        return ExperimentResult(
            problem_id=problem["id"],
            domain=problem["domain"],
            method="single_prompt",
            n_cases=n_cases,
            coverage_pct=0.0,  # No spec-graph coverage
            oracle_match_rate=0.0,  # No oracle
            discrimination_mean=0.0,  # No discrimination
            inter_diversity=0.0,  # Single student
            mutation_score=0.0,  # No mutation analysis
            parsing_success=True,
            duration_s=time.time() - start,
        )
    except Exception as exc:
        return ExperimentResult(
            problem_id=problem["id"],
            domain=problem["domain"],
            method="single_prompt",
            parsing_success=False,
            duration_s=time.time() - start,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def run_full_pipeline(problem: Dict[str, Any]) -> ExperimentResult:
    """Run the full SpecTest-LLM pipeline and collect metrics."""
    from graph import run_pipeline

    start = time.time()
    try:
        report = run_pipeline(
            problem=problem["problem"],
            description=problem.get("description", ""),
            constraints=problem.get("constraints", ""),
            code=problem.get("code", ""),
            language=problem.get("language", "python"),
            student_count=3,
            per_category=2,
        )
        meta = report.meta or {}
        metrics = meta.get("metrics", {})
        mutation = meta.get("mutation", {})

        return ExperimentResult(
            problem_id=problem["id"],
            domain=problem["domain"],
            method="spectest_llm_full",
            n_cases=metrics.get("n_cases", 0),
            coverage_pct=metrics.get("coverage_pct", 0.0),
            oracle_match_rate=metrics.get("oracle_match_rate", 0.0),
            discrimination_mean=metrics.get("discrimination_mean", 0.0),
            inter_diversity=metrics.get("inter_diversity", 0.0),
            mutation_score=mutation.get("mutation_score", 0.0),
            parsing_success=True,
            duration_s=time.time() - start,
        )
    except Exception as exc:
        logger.exception("Pipeline failed for %s", problem["id"])
        return ExperimentResult(
            problem_id=problem["id"],
            domain=problem["domain"],
            method="spectest_llm_full",
            parsing_success=False,
            duration_s=time.time() - start,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="SpecTest-LLM Experiment Runner")
    parser.add_argument("--problems", type=int, default=None, help="Limit to first N problems")
    parser.add_argument("--baseline-only", action="store_true", help="Only run baselines")
    parser.add_argument("--full-only", action="store_true", help="Only run full pipeline")
    parser.add_argument("--output-dir", default="experiments_results", help="Output directory")
    args = parser.parse_args()

    problems = BENCHMARK_PROBLEMS[: args.problems] if args.problems else BENCHMARK_PROBLEMS
    os.makedirs(args.output_dir, exist_ok=True)

    results: List[ExperimentResult] = []

    for i, problem in enumerate(problems, 1):
        logger.info("=" * 60)
        logger.info("Problem %d/%d: %s [%s]", i, len(problems), problem["id"], problem["domain"])

        if not args.full_only:
            logger.info("Running: single_prompt baseline")
            result = run_single_prompt_baseline(problem)
            results.append(result)
            logger.info(
                "  → %s: cases=%d, parse=%s, time=%.1fs",
                result.method, result.n_cases, result.parsing_success, result.duration_s,
            )

        if not args.baseline_only:
            logger.info("Running: spectest_llm_full")
            result = run_full_pipeline(problem)
            results.append(result)
            logger.info(
                "  → %s: cases=%d, coverage=%.2f, oracle=%.2f, disc=%.2f, "
                "mutation=%.2f, time=%.1fs",
                result.method, result.n_cases, result.coverage_pct,
                result.oracle_match_rate, result.discrimination_mean,
                result.mutation_score, result.duration_s,
            )

    # Save results as CSV
    csv_path = os.path.join(args.output_dir, "results.csv")
    if results:
        fieldnames = list(asdict(results[0]).keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r.to_dict())
        logger.info("Results saved to %s", csv_path)

    # Save as JSON too
    json_path = os.path.join(args.output_dir, "results.json")
    with open(json_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    logger.info("JSON results saved to %s", json_path)

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'Problem':>6} | {'Method':<25} | {'Cases':>5} | {'Coverage':>8} | "
          f"{'Oracle':>6} | {'Disc':>5} | {'Mutation':>8} | {'Time':>6}")
    print("-" * 100)
    for r in results:
        print(
            f"{r.problem_id:>6} | {r.method:<25} | {r.n_cases:>5} | "
            f"{r.coverage_pct * 100:>7.1f}% | {r.oracle_match_rate * 100:>5.1f}% | "
            f"{r.discrimination_mean * 100:>4.1f}% | "
            f"{r.mutation_score * 100:>7.1f}% | {r.duration_s:>5.1f}s"
        )
    print("=" * 100)


if __name__ == "__main__":
    main()
