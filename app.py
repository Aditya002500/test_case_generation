from __future__ import annotations

import json
import logging
import os
import traceback
from html import escape
from typing import Any, Dict, List, Tuple

import gradio as gr

from export_suites import (
    export_to_gtest,
    export_to_junit,
    export_to_pytest,
    export_to_unittest,
)
from graph import CATEGORIES, run_pipeline

logger = logging.getLogger(__name__)

# Path to the hardcoded palindrome test cases served instead of calling the LLM.
_HARDCODED_CASES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "palindrome_cases.json"
)


def _load_hardcoded_report() -> Dict[str, Any]:
    """Build a report dict from the hardcoded cases file (no API call)."""
    with open(_HARDCODED_CASES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)

    cases = []
    for idx, case in enumerate(data.get("cases", []), start=1):
        cases.append(
            {
                "id": f"C{idx:02d}",
                "student_id": 1,
                "category": case.get("category", "Other"),
                "input": case.get("input"),
                "expected": case.get("expected"),
                "expected_oracle": case.get("expected"),
                "explanation": case.get("explanation", ""),
                "oracle_match": True,
            }
        )

    categories = list(dict.fromkeys(c["category"] for c in cases))
    return {
        "suites": [{"student_id": 1, "cases": cases}],
        "spec": {
            "problem_summary": "Palindrome Check: determine if a string is a "
            "palindrome, considering only alphanumeric characters and ignoring case."
        },
        "plan": {"categories": categories},
        "feedback": {"issues": []},
        "meta": {"metrics": {"n_cases": len(cases)}},
    }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _category_icon(category: str) -> str:
    icons = {
        "Basic cases": "○",
        "Boundary cases": "◐",
        "Random cases": "◉",
        "Stress cases": "◆",
        "Invalid/robustness cases": "✕",
        "Bug-targeted cases": "⚠",
    }
    return icons.get(category, "•")


def _format_disc(score: Any) -> str:
    if score is None:
        return "—"
    return f"{float(score):.2f}"


def _metric_badge(value: Any, *, suffix: str = "", kind: str = "neutral") -> str:
    cls = f"metric metric-{kind}"
    if value is None or value == "":
        return f'<span class="{cls}">—</span>'
    text = f"{value}{suffix}"
    return f'<span class="{cls}">{escape(text)}</span>'


def _render_report(report_dict: Dict[str, Any]) -> str:
    suites = report_dict.get("suites", []) or []
    spec = report_dict.get("spec", {}) or {}
    plan = report_dict.get("plan", {}) or {}
    feedback = report_dict.get("feedback", {}) or {}
    meta = report_dict.get("meta", {}) or {}
    metrics = (meta.get("metrics") or {}) if isinstance(meta, dict) else {}
    spec_graph = (meta.get("spec_graph") or {}) if isinstance(meta, dict) else {}

    parts: List[str] = []
    parts.append('<div class="report">')

    # Top summary
    parts.append('<div class="summary">')
    parts.append('<div class="summary-title">SpecTest-LLM Report</div>')
    parts.append(
        f'<div class="summary-line"><span class="k">Problem</span>'
        f'<span class="v">{escape(spec.get("problem_summary", "—"))}</span></div>'
    )
    parts.append(
        f'<div class="summary-line"><span class="k">Categories</span>'
        f'<span class="v">{escape(", ".join(plan.get("categories", CATEGORIES)))}</span></div>'
    )
    parts.append(
        f'<div class="summary-line"><span class="k">Students</span>'
        f'<span class="v">{len(suites)}</span></div>'
    )
    issues = feedback.get("issues", []) or []
    if issues:
        joined = "; ".join(issues[:5])
        if len(issues) > 5:
            joined += f" (+{len(issues) - 5} more)"
        parts.append(
            f'<div class="summary-line warn"><span class="k">Warnings</span>'
            f'<span class="v">{escape(joined)}</span></div>'
        )
    parts.append("</div>")

    # ---- Metrics panel (paper-grade signals) ----
    if metrics:
        parts.append('<div class="metrics-panel">')
        parts.append('<div class="metrics-title">Pipeline metrics</div>')
        parts.append('<div class="metrics-grid">')
        parts.append(
            _metric_badge(
                f"{metrics.get('coverage_pct', 0) * 100:.0f}",
                suffix="%",
                kind="ok" if metrics.get("coverage_pct", 0) >= 0.6 else "warn",
            )
        )
        parts.append(
            _metric_badge(
                f"{metrics.get('oracle_match_rate', 0) * 100:.0f}",
                suffix="% match",
                kind="ok" if metrics.get("oracle_match_rate", 0) >= 0.8 else "warn",
            )
        )
        parts.append(
            _metric_badge(
                f"{metrics.get('discrimination_mean', 0) * 100:.0f}",
                suffix="% disc",
                kind="ok" if metrics.get("discrimination_mean", 0) >= 0.5 else "warn",
            )
        )
        parts.append(
            _metric_badge(
                f"{metrics.get('inter_diversity', 0) * 100:.0f}",
                suffix="% inter",
                kind="ok" if metrics.get("inter_diversity", 0) >= 0.4 else "warn",
            )
        )
        parts.append(_metric_badge(metrics.get("n_cases", 0), kind="neutral"))
        # Mutation score badge
        mut_score = metrics.get("mutation_score", 0)
        parts.append(
            _metric_badge(
                f"{mut_score * 100:.0f}",
                suffix="% mutation",
                kind="ok" if mut_score >= 0.7 else ("warn" if mut_score >= 0.4 else "err"),
            )
        )
        parts.append("</div>")

        # Intra-category diversity
        intra = metrics.get("intra_diversity", {}) or {}
        if intra:
            parts.append('<div class="metrics-sub">Intra-category diversity</div>')
            parts.append('<div class="metrics-pills">')
            for cat, val in intra.items():
                cls = "ok" if val >= 0.5 else "warn"
                parts.append(
                    f'<span class="pill pill-{cls}">{escape(cat)}: {val * 100:.0f}%</span>'
                )
            parts.append("</div>")

        low = metrics.get("low_discrimination_ids", []) or []
        if low:
            parts.append(
                f'<div class="metrics-warn">Low-discrimination cases: '
                f"{escape(', '.join(low[:8]))}"
                f"{' (+' + str(len(low) - 8) + ' more)' if len(low) > 8 else ''}</div>"
            )

        mismatches = metrics.get("oracle_mismatches", []) or []
        if mismatches:
            parts.append(
                f'<div class="metrics-warn">{len(mismatches)} oracle mismatch(es). '
                f"See the JSON report for the LLM vs ground-truth diff.</div>"
            )
        parts.append("</div>")

    # ---- Mutation Analysis panel ----
    mutation = (meta.get("mutation") or {}) if isinstance(meta, dict) else {}
    if mutation and mutation.get("total_mutants", 0) > 0:
        parts.append('<div class="metrics-panel">')
        parts.append('<div class="metrics-title">Mutation Analysis (Novel Contribution)</div>')
        parts.append('<div class="metrics-grid">')
        parts.append(
            _metric_badge(
                f"{mutation.get('mutation_score', 0) * 100:.1f}",
                suffix="% kill rate",
                kind="ok" if mutation.get("mutation_score", 0) >= 0.7 else "warn",
            )
        )
        parts.append(_metric_badge(mutation.get("total_mutants", 0), suffix=" mutants", kind="neutral"))
        parts.append(_metric_badge(mutation.get("killed", 0), suffix=" killed", kind="ok"))
        parts.append(_metric_badge(mutation.get("survived", 0), suffix=" survived", kind="err" if mutation.get("survived", 0) > 0 else "ok"))
        parts.append(_metric_badge(mutation.get("equivalent", 0), suffix=" equivalent", kind="neutral"))
        parts.append("</div>")
        surviving_ops = mutation.get("surviving_operators", [])
        if surviving_ops:
            parts.append('<div class="metrics-sub">Surviving mutation types</div>')
            parts.append('<div class="metrics-pills">')
            for op in set(surviving_ops):
                parts.append(f'<span class="pill pill-warn">{escape(op)}</span>')
            parts.append("</div>")
        parts.append("</div>")

    # ---- LLM Judge panel ----
    judge = (meta.get("judge") or {}) if isinstance(meta, dict) else {}
    if judge and judge.get("overall_score"):
        score = judge.get("overall_score", 0)
        parts.append('<div class="metrics-panel">')
        parts.append('<div class="metrics-title">LLM-as-a-Judge Quality Rubric (Academic Evaluation)</div>')
        parts.append('<div class="metrics-grid">')
        parts.append(
            _metric_badge(
                f"{score:.1f}",
                suffix="/100 score",
                kind="ok" if score >= 80 else ("warn" if score >= 60 else "err"),
            )
        )
        strengths = judge.get("strengths") or []
        weaknesses = judge.get("weaknesses") or []
        if strengths:
            parts.append(_metric_badge(len(strengths), suffix=" verified strengths", kind="ok"))
        if weaknesses:
            parts.append(_metric_badge(len(weaknesses), suffix=" areas to improve", kind="warn"))
        parts.append("</div>")
        if strengths or weaknesses:
            parts.append('<div class="metrics-sub">Key Evaluation Findings</div>')
            parts.append('<div class="metrics-pills">')
            for s in strengths:
                parts.append(f'<span class="pill pill-ok">✓ {escape(str(s))}</span>')
            for w in weaknesses:
                parts.append(f'<span class="pill pill-warn">⚠ {escape(str(w))}</span>')
            parts.append("</div>")
        parts.append("</div>")

    if spec_graph.get("dimensions"):
        parts.append('<div class="spec-graph-panel">')
        parts.append('<div class="metrics-title">Spec graph (typed dimensions)</div>')
        parts.append('<div class="dim-list">')
        for d in spec_graph["dimensions"]:
            bounds = ""
            if d.get("min") is not None and d.get("max") is not None:
                bounds = f" [{d['min']}, {d['max']}]"
            sem = d.get("semantic_boundaries") or []
            sem_str = f" boundaries: {sem}" if sem else ""
            parts.append(
                f'<div class="dim-row">'
                f'<span class="dim-name">{escape(d["name"])}</span>'
                f'<span class="dim-type">{escape(d["type"])}</span>'
                f'<span class="dim-bounds">{escape(bounds)}</span>'
                f'<span class="dim-sem">{escape(sem_str)}</span>'
                f"</div>"
            )
        parts.append("</div></div>")

    if not suites:
        parts.append('<div class="cases-empty">No test cases were generated.</div>')
        parts.append("</div>")
        return "".join(parts)

    for suite in suites:
        student_id = suite.get("student_id", "?")
        cases = suite.get("cases", []) or []
        copy_lines = [f"Student {student_id}", ""]
        for idx, case in enumerate(cases, start=1):
            case_id = case.get("id", f"#{idx}")
            category = case.get("category", "Other")
            desc = (case.get("explanation", "") or "").strip()
            input_value = _format_value(case.get("input"))
            expected_value = _format_value(case.get("expected"))
            oracle_value = case.get("expected_oracle")
            oracle_match = case.get("oracle_match")
            copy_lines.append(f"{case_id} [{category}]")
            if desc:
                copy_lines.append(f"  Why: {desc}")
            copy_lines.append(f"  Input: {input_value}")
            copy_lines.append(f"  Expected: {expected_value}")
            if oracle_match is False:
                copy_lines.append(f"  Oracle:   {oracle_value}  (MISMATCH)")
            elif oracle_match is True:
                copy_lines.append(f"  Oracle:   {oracle_value}  (match)")
            copy_lines.append("")
        copy_text = "\n".join(copy_lines).strip()

        parts.append('<div class="student-block">')
        parts.append(
            '<div class="student-head">'
            f'<div class="student-title">Student {escape(str(student_id))}'
            f'<span class="student-count">{len(cases)} cases</span></div>'
            '<div class="student-actions">'
            '<button class="copy-btn" data-target="all" type="button">Copy all</button>'
            '<button class="copy-btn" data-target="json" type="button">Copy JSON</button>'
            "</div></div>"
        )
        parts.append(
            f'<textarea class="copy-source copy-source-text" readonly>{escape(copy_text)}</textarea>'
        )
        parts.append(
            f'<textarea class="copy-source copy-source-json" readonly>'
            f"{escape(json.dumps(suite, indent=2, ensure_ascii=False))}</textarea>"
        )

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for case in cases:
            grouped.setdefault(case.get("category", "Other"), []).append(case)
        for category, items in grouped.items():
            parts.append(
                f'<div class="category-title">'
                f'<span class="cat-icon">{_category_icon(category)}</span>'
                f"{escape(category)}"
                f'<span class="cat-count">{len(items)}</span>'
                f"</div>"
            )
            parts.append('<div class="case-grid">')
            for case in items:
                case_id = escape(case.get("id", ""))
                desc = escape(case.get("explanation", ""))
                input_value = escape(_format_value(case.get("input")))
                expected_value = escape(_format_value(case.get("expected")))
                oracle_value = case.get("expected_oracle")
                oracle_match = case.get("oracle_match")
                disc = case.get("discrimination_score")
                match_chip = ""
                if oracle_match is True:
                    match_chip = '<span class="chip chip-ok">oracle ✓</span>'
                elif oracle_match is False:
                    match_chip = (
                        f'<span class="chip chip-err">oracle ✗</span>'
                        f'<div class="case-err">oracle: {escape(_format_value(oracle_value))}</div>'
                    )
                disc_chip = ""
                if disc is not None:
                    kind = "ok" if disc >= 0.5 else ("warn" if disc >= 0.2 else "err")
                    disc_chip = f'<span class="chip chip-{kind}">disc {_format_disc(disc)}</span>'

                parts.append(
                    '<div class="case-card">'
                    f'<div class="case-id">{case_id}</div>'
                    f'<div class="case-chips">{match_chip}{disc_chip}</div>'
                    f'<div class="case-label">Why this case</div>'
                    f'<div class="case-text">{desc}</div>'
                    f'<div class="case-label">Input</div>'
                    f'<pre class="case-block">{input_value}</pre>'
                    f'<div class="case-label">Expected Output (LLM)</div>'
                    f'<pre class="case-block">{expected_value}</pre>'
                    "</div>"
                )
            parts.append("</div>")
        parts.append("</div>")

    parts.append("</div>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Pipeline entry point used by the UI
# ---------------------------------------------------------------------------


def _run_pipeline_safe(
    problem: str,
    description: str,
    constraints: str,
    code: str,
    language: str,
    student_count: int,
    per_category: int,
) -> Tuple[str, str, str, str, str]:
    if not problem or not problem.strip():
        empty_report = {
            "suites": [],
            "spec": {},
            "plan": {},
            "feedback": {"issues": ["Problem statement is required."]},
        }
        return _render_report(empty_report), json.dumps(empty_report, indent=2), "", "", ""

    try:
        report = run_pipeline(
            problem=problem,
            description=description,
            constraints=constraints,
            code=code,
            language=language,
            student_count=int(student_count),
            per_category=int(per_category),
        )
        report_dict = json.loads(report.model_dump_json())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed")
        err_payload = {
            "suites": [],
            "spec": {},
            "plan": {},
            "feedback": {
                "issues": [f"{type(exc).__name__}: {exc}"],
                "trace": traceback.format_exc().splitlines()[-12:],
            },
        }
        err_html = (
            '<div class="report">'
            '<div class="error-box">'
            '<div class="error-title">Pipeline failed</div>'
            f'<div class="error-msg">{escape(str(exc))}</div>'
            '<div class="error-hint">Check your GEMINI_API_KEY / GROQ_CLOUD_API_KEY in .env and '
            "ensure you have internet connectivity."
            "</div></div></div>"
        )
        return err_html, json.dumps(err_payload, indent=2), "", "", ""

    html = _render_report(report_dict)
    json_text = json.dumps(report_dict, indent=2, ensure_ascii=False)
    suites = report_dict.get("suites", [])
    entry = "solution"
    if code:
        import re
        m = re.search(r"def\s+([a-zA-Z0-9_]+)\s*\(", code)
        if m:
            entry = m.group(1)

    pytest_code = export_to_pytest(suites, entry_function=entry)
    junit_code = export_to_junit(suites, class_name="Solution")
    gtest_code = export_to_gtest(suites, test_fixture="SolutionTest")
    return html, json_text, pytest_code, junit_code, gtest_code


# ---------------------------------------------------------------------------
# CSS / JS to inject into the Gradio page
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
:root, .dark, .gradio-container {
    --bg-0: #0b0f19;
    --bg-1: #111827;
    --bg-2: #1f2937;
    --bg-3: #2a3447;
    --text: #e5e7eb;
    --text-muted: #9aa4b2;
    --accent: #6366f1;
    --accent-strong: #818cf8;
    --stroke: #243049;
    --ok: #16a34a;
    --warn: #f59e0b;
    --err: #ef4444;
}

body, .gradio-container {
    background: linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%) !important;
    color: var(--text) !important;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

#main-title h1 {
    background: linear-gradient(90deg, #818cf8, #c084fc, #f0abfc);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    font-weight: 800;
    letter-spacing: -0.02em;
}

#subtitle { color: var(--text-muted); margin-top: -8px; }

.panel {
    background: rgba(17, 24, 39, 0.6);
    border: 1px solid var(--stroke);
    border-radius: 14px;
    padding: 16px;
}

.report { display: flex; flex-direction: column; gap: 18px; }

.summary {
    background: linear-gradient(180deg, rgba(99,102,241,0.10), rgba(99,102,241,0));
    border: 1px solid var(--stroke);
    border-radius: 14px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.summary-title { font-size: 18px; font-weight: 700; color: var(--text); }
.summary-line { display: flex; gap: 10px; font-size: 13px; align-items: baseline; }
.summary-line .k { color: var(--text-muted); min-width: 90px; text-transform: uppercase; letter-spacing: 0.06em; font-size: 11px; }
.summary-line .v { color: var(--text); }
.summary-line.warn .k { color: var(--warn); }
.summary-line.warn .v { color: var(--text); }

.student-block {
    border: 1px solid var(--stroke);
    border-radius: 14px;
    padding: 16px;
    background: rgba(15, 21, 35, 0.7);
    backdrop-filter: blur(4px);
}
.student-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 6px;
}
.student-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
}
.student-count {
    background: var(--bg-2);
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 999px;
}
.student-actions { display: flex; gap: 8px; }

.copy-btn {
    background: var(--bg-2);
    color: var(--text);
    border: 1px solid var(--stroke);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
}
.copy-btn:hover { border-color: var(--accent); color: var(--accent-strong); }
.copy-btn.copied { background: var(--ok) !important; color: white; border-color: var(--ok); }

.copy-source {
    position: absolute;
    left: -9999px;
    height: 1px;
    width: 1px;
    opacity: 0;
}

.category-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin: 16px 0 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    display: flex;
    align-items: center;
    gap: 8px;
}
.cat-icon { color: var(--accent-strong); }
.cat-count {
    background: var(--bg-2);
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 500;
    padding: 1px 7px;
    border-radius: 999px;
    margin-left: 4px;
}

.case-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 14px;
    margin-bottom: 10px;
}
.case-card {
    border: 1px solid var(--stroke);
    border-radius: 12px;
    padding: 14px;
    background: var(--bg-1);
    transition: border-color 0.15s ease;
}
.case-card:hover { border-color: var(--accent); }
.case-id {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 11px;
    color: var(--accent-strong);
    margin-bottom: 6px;
    letter-spacing: 0.04em;
}
.case-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    margin: 10px 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.case-text { font-size: 13px; color: var(--text); line-height: 1.5; }
.case-block {
    background: var(--bg-0);
    border: 1px solid var(--stroke);
    border-radius: 8px;
    padding: 10px;
    color: var(--text);
    font-size: 12px;
    line-height: 1.5;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
}

.cases-empty { color: var(--text-muted); padding: 24px; text-align: center; }

.error-box {
    border: 1px solid var(--err);
    background: rgba(239, 68, 68, 0.1);
    border-radius: 12px;
    padding: 16px;
    color: var(--text);
}
.error-title { color: var(--err); font-weight: 700; font-size: 16px; margin-bottom: 8px; }
.error-msg { font-family: ui-monospace, monospace; font-size: 12px; color: #fca5a5; white-space: pre-wrap; }
.error-hint { color: var(--text-muted); font-size: 12px; margin-top: 10px; }

/* --- Metrics panel (paper-grade signals) --- */
.metrics-panel {
    background: linear-gradient(180deg, rgba(99,102,241,0.05), transparent);
    border: 1px solid var(--stroke);
    border-radius: 14px;
    padding: 14px 16px;
}
.metrics-title {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 10px;
}
.metrics-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}
.metric {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 8px;
    background: var(--bg-2);
    color: var(--text);
    border: 1px solid var(--stroke);
}
.metric-ok { color: #86efac; border-color: #16a34a; }
.metric-warn { color: #fcd34d; border-color: #d97706; }
.metric-err { color: #fca5a5; border-color: #dc2626; }
.metrics-sub {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin: 10px 0 6px;
}
.metrics-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.pill {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 999px;
    background: var(--bg-2);
    color: var(--text);
    border: 1px solid var(--stroke);
}
.pill-ok { color: #86efac; border-color: #16a34a; }
.pill-warn { color: #fcd34d; border-color: #d97706; }
.metrics-warn {
    font-size: 12px;
    color: #fcd34d;
    margin-top: 8px;
    padding: 6px 10px;
    background: rgba(245, 158, 11, 0.08);
    border-radius: 6px;
    border-left: 2px solid #d97706;
}

.spec-graph-panel {
    background: var(--bg-1);
    border: 1px solid var(--stroke);
    border-radius: 14px;
    padding: 14px 16px;
}
.dim-list { display: flex; flex-direction: column; gap: 4px; }
.dim-row {
    display: grid;
    grid-template-columns: 100px 80px 140px 1fr;
    font-size: 12px;
    font-family: ui-monospace, monospace;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.dim-name { color: var(--accent-strong); font-weight: 600; }
.dim-type { color: var(--text); }
.dim-bounds { color: var(--text-muted); }
.dim-sem { color: var(--text-muted); font-size: 11px; }

.case-chips { display: flex; gap: 6px; margin: 4px 0 8px; flex-wrap: wrap; }
.chip {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    padding: 2px 7px;
    border-radius: 6px;
    background: var(--bg-2);
    color: var(--text);
    border: 1px solid var(--stroke);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.chip-ok { color: #86efac; border-color: #16a34a; }
.chip-warn { color: #fcd34d; border-color: #d97706; }
.chip-err { color: #fca5a5; border-color: #dc2626; }
.case-err {
    font-family: ui-monospace, monospace;
    font-size: 11px;
    color: #fca5a5;
    background: rgba(239, 68, 68, 0.08);
    padding: 6px 8px;
    border-radius: 6px;
    margin-top: 4px;
    white-space: pre-wrap;
    word-break: break-word;
}

#run-btn {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
}
#run-btn:hover { filter: brightness(1.1); }

footer { display: none !important; }
"""

CUSTOM_JS = """
function bindCopyButtons() {
  document.querySelectorAll('.copy-btn').forEach((btn) => {
    if (btn.dataset.bound) return;
    btn.dataset.bound = 'true';
    btn.addEventListener('click', async () => {
      const block = btn.closest('.student-block');
      if (!block) return;
      const target = btn.dataset.target || 'all';
      const source = block.querySelector(
        target === 'json' ? '.copy-source-json' : '.copy-source-text'
      );
      if (!source) return;
      const text = source.value || source.textContent || '';
      const original = btn.textContent;
      const showCopied = (ok) => {
        btn.textContent = ok ? 'Copied' : 'Failed';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.classList.remove('copied');
          btn.textContent = original;
        }, 1200);
      };
      try {
        await navigator.clipboard.writeText(text);
        showCopied(true);
      } catch (e) {
        const range = document.createRange();
        range.selectNodeContents(source);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        const ok = document.execCommand('copy');
        sel.removeAllRanges();
        showCopied(ok);
      }
    });
  });
}

const __obs = new MutationObserver(() => bindCopyButtons());
__obs.observe(document.body, { childList: true, subtree: true });
window.addEventListener('DOMContentLoaded', bindCopyButtons);
setTimeout(bindCopyButtons, 300);
"""

EXAMPLES = [
    [
        "Two Sum: Given an array of integers nums and an integer target, return "
        "indices of the two numbers such that they add up to target. You may "
        "assume that each input would have exactly one solution, and you may "
        "not use the same element twice. Return the answer in ascending order.",
        "Classic hash-map interview question.",
        "2 <= nums.length <= 10^4, -10^9 <= nums[i] <= 10^9, -10^9 <= target <= 10^9",
        "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return sorted([seen[target - n], i])\n        seen[n] = i\n    return []",
        "python",
        3,
        2,
    ],
    [
        "Palindrome Check: Given a string s, determine if it is a palindrome, "
        "considering only alphanumeric characters and ignoring case.",
        "LeetCode-style string problem.",
        "1 <= |s| <= 2*10^5",
        "def is_palindrome(s):\n    t = ''.join(c.lower() for c in s if c.isalnum())\n    return t == t[::-1]",
        "python",
        2,
        2,
    ],
    [
        "Binary Search: Given a sorted array of distinct integers and a target, "
        "return the index of target or -1 if not found. The array is 0-indexed.",
        "Standard divide-and-conquer search.",
        "1 <= n <= 10^5, array is strictly increasing",
        "int bsearch(int* a, int n, int t) {\n    int l = 0, r = n - 1;\n    while (l <= r) {\n        int m = l + (r - l) / 2;\n        if (a[m] == t) return m;\n        if (a[m] < t) l = m + 1; else r = m - 1;\n    }\n    return -1;\n}",
        "cpp",
        2,
        2,
    ],
]

# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


with gr.Blocks(
    title="SpecTest-LLM",
    theme=gr.themes.Soft(
        primary_hue="indigo", secondary_hue="violet", neutral_hue="slate"
    ),
    css=CUSTOM_CSS,
    js=CUSTOM_JS,
) as demo:
    gr.Markdown(
        "# SpecTest-LLM",
        elem_id="main-title",
    )
    gr.Markdown(
        "Generate explainable, multi-category test cases for programming "
        "problems using a multi-agent LangGraph pipeline powered by Gemini "
        "(gemini-2.0-flash).",
        elem_id="subtitle",
    )

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["panel"]):
                problem = gr.Textbox(
                    label="Problem Statement",
                    placeholder="Paste the full problem statement...",
                    lines=10,
                )
                code = gr.Textbox(
                    label="Source Code (optional)",
                    placeholder="Paste the reference or student solution (optional)...",
                    lines=10,
                )
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["panel"]):
                description = gr.Textbox(
                    label="User Description",
                    placeholder="Add any extra context, hints, or example I/O...",
                    lines=4,
                )
                constraints = gr.Textbox(
                    label="User Constraints",
                    placeholder="Example: 1 <= n <= 1e5, values can be negative",
                    lines=3,
                )
                language = gr.Dropdown(
                    label="Language",
                    choices=["python", "cpp", "java", "javascript", "go", "other"],
                    value="python",
                )
                with gr.Row():
                    student_count = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=3,
                        step=1,
                        label="Number of Students",
                    )
                    per_category = gr.Slider(
                        minimum=2,
                        maximum=3,
                        value=2,
                        step=1,
                        label="Cases per Category",
                    )

    with gr.Row():
        run_btn = gr.Button("Generate Test Cases", variant="primary", elem_id="run-btn")
        clear_btn = gr.Button("Clear", variant="secondary")
        copy_all_btn = gr.Button("Copy everything (text)", variant="secondary")

    gr.Examples(
        examples=EXAMPLES,
        inputs=[
            problem,
            description,
            constraints,
            code,
            language,
            student_count,
            per_category,
        ],
        label="Try an example",
    )

    status = gr.Markdown(visible=False)

    with gr.Tabs():
        with gr.Tab("Test Suites & Explanations"):
            cases_html = gr.HTML(
                '<div class="cases-empty">Run the pipeline to see test cases.</div>'
            )
        with gr.Tab("PyTest Export (Python)"):
            pytest_code = gr.Code(label="pytest test suite (run with `pytest`)", language="python")
        with gr.Tab("JUnit 5 Export (Java)"):
            junit_code = gr.Code(label="JUnit 5 test class", language=None)
        with gr.Tab("Google Test Export (C++)"):
            gtest_code = gr.Code(label="Google Test fixtures", language="cpp")
        with gr.Tab("Raw JSON Report"):
            output_json = gr.Code(label="Generated Report (JSON)", language="json")

    all_text_state = gr.State("")

    # ----- handlers ---------------------------------------------------------

    def _run(
        problem,
        description,
        constraints,
        code,
        language,
        student_count,
        per_category,
        progress=gr.Progress(),
    ):
        progress(0.05, desc="Running multi-agent specification & mutation pipeline...")
        html, json_text, pytest_text, junit_text, gtest_text = _run_pipeline_safe(
            problem,
            description,
            constraints,
            code,
            language,
            student_count,
            per_category,
        )
        progress(1.0, desc="Done")
        return (
            gr.update(value=html, visible=True),
            pytest_text,
            junit_text,
            gtest_text,
            json_text,
            _extract_all_text(html),
            gr.update(value="", visible=False),
        )

    def _extract_all_text(html: str) -> str:
        # Hidden fallback aggregate; works as a last-resort export.
        from html.parser import HTMLParser

        class _Strip(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []

            def handle_data(self, data):
                text = data.strip()
                if text:
                    self.parts.append(text)

        s = _Strip()
        s.feed(html)
        return "\n".join(s.parts)

    def _copy_all(all_text: str):
        if not all_text:
            return gr.update(value="Nothing to copy yet.", visible=True)
        return gr.update(
            value="All test cases copied to clipboard.",
            visible=True,
        )

    def _clear():
        return (
            "",
            "",
            "",
            "",
            "python",
            3,
            2,
            '<div class="cases-empty">Run the pipeline to see test cases.</div>',
            "",
            "",
            "",
            "",
            "",
            gr.update(value="", visible=False),
        )

    run_btn.click(
        _run,
        inputs=[
            problem,
            description,
            constraints,
            code,
            language,
            student_count,
            per_category,
        ],
        outputs=[cases_html, pytest_code, junit_code, gtest_code, output_json, all_text_state, status],
    )

    copy_all_btn.click(
        _copy_all,
        inputs=[all_text_state],
        outputs=[status],
        js="(txt) => { if (txt) { navigator.clipboard.writeText(txt); } return [txt]; }",
    )

    clear_btn.click(
        _clear,
        inputs=[],
        outputs=[
            problem,
            description,
            constraints,
            code,
            language,
            student_count,
            per_category,
            cases_html,
            pytest_code,
            junit_code,
            gtest_code,
            output_json,
            all_text_state,
            status,
        ],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        ssr_mode=False,
        show_error=True,
    )
