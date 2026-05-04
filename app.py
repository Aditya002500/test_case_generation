from __future__ import annotations

import json
from html import escape

import gradio as gr

from graph import run_pipeline


def _format_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def _render_report(report_dict: dict) -> str:
    suites = report_dict.get("suites", [])
    if not suites:
        return '<div class="cases-empty">No test cases generated.</div>'

    sections = []
    for suite in suites:
        student_id = suite.get("student_id", "?")
        cases = suite.get("cases", [])
        copy_lines = [f"Student {student_id}"]
        for idx, case in enumerate(cases, start=1):
            category = case.get("category", "Other")
            desc = case.get("explanation", "").strip()
            input_value = _format_value(case.get("input"))
            copy_lines.append(f"Test Case {idx}")
            copy_lines.append(f"Category: {category}")
            if desc:
                copy_lines.append(f"Description: {desc}")
            copy_lines.append(f"Input: {input_value}")
            copy_lines.append("")
        copy_text = "\n".join(copy_lines).strip()
        sections.append('<div class="student-block">')
        sections.append(
            '<div class="student-head">'
            f'<div class="student-title">Student {escape(str(student_id))}</div>'
            '<button class="copy-btn" type="button">Copy student cases</button>'
            "</div>"
        )
        sections.append(f'<textarea class="copy-source">{escape(copy_text)}</textarea>')
        grouped = {}
        for case in cases:
            category = case.get("category", "Other")
            grouped.setdefault(category, []).append(case)
        for category, items in grouped.items():
            sections.append(f'<div class="category-title">{escape(category)}</div>')
            sections.append('<div class="case-grid">')
            for idx, case in enumerate(items, start=1):
                desc = escape(case.get("explanation", ""))
                input_value = escape(_format_value(case.get("input")))
                expected_value = escape(_format_value(case.get("expected")))
                sections.append(
                    '<div class="case-card">'
                    f'<div class="case-title">Test Case {idx}</div>'
                    f'<div class="case-label">Description</div>'
                    f'<div class="case-text">{desc}</div>'
                    f'<div class="case-label">Input</div>'
                    f'<pre class="case-block">{input_value}</pre>'
                    f'<div class="case-label">Expected Output</div>'
                    f'<pre class="case-block">{expected_value}</pre>'
                    "</div>"
                )
            sections.append("</div>")
        sections.append("</div>")
    return "".join(sections)


def generate_tests(
    problem: str,
    description: str,
    constraints: str,
    code: str,
    language: str,
    student_count: int,
    per_category: int,
):
    if not problem.strip():
        return '{\n  "error": "Problem statement is required."\n}'
    report = run_pipeline(
        problem=problem,
        description=description,
        constraints=constraints,
        code=code,
        language=language,
        student_count=student_count,
        per_category=per_category,
    )
    report_dict = report.model_dump()
    html = _render_report(report_dict)
    return html, json.dumps(report_dict, indent=2)


with gr.Blocks(title="SpecTest-LLM") as demo:
    gr.Markdown(
        """
<style>
  :root {
    --bg-dark: #0b0f19;
    --card-dark: #151c2b;
    --text-primary: #eef2ff;
    --text-muted: #9aa4b2;
    --accent: #3b82f6;
    --stroke: #243049;
  }
  .cases-wrap {
    border: 1px solid var(--stroke);
    border-radius: 12px;
    padding: 16px;
    background: var(--bg-dark);
    max-height: 520px;
    overflow-y: auto;
  }
  .student-title {
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 12px 0 8px;
  }
  .student-block {
    border: 1px solid var(--stroke);
    border-radius: 12px;
    padding: 14px;
    background: #0f1523;
    margin-bottom: 16px;
  }
  .student-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .copy-btn {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
  }
  .copy-btn.copied {
    background: #16a34a;
  }
  .copy-source {
    position: absolute;
    left: -9999px;
    height: 1px;
    width: 1px;
    opacity: 0;
  }
  .category-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 16px 0 10px;
  }
  .case-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
    margin-bottom: 12px;
  }
  .case-card {
    border: 1px solid var(--stroke);
    border-radius: 12px;
    padding: 14px;
    background: var(--card-dark);
  }
  .case-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
  }
  .case-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin: 10px 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .case-text {
    font-size: 13px;
    color: var(--text-primary);
  }
  .case-block {
    background: #1f2937;
    border-radius: 8px;
    padding: 10px;
    color: #e5e7eb;
    font-size: 12px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .cases-empty {
    color: var(--text-muted);
  }
</style>
<script>
  function bindCopyButtons(root) {
    const container = root || document;
    container.querySelectorAll(".copy-btn").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "true";
      btn.addEventListener("click", async () => {
        const block = btn.closest(".student-block");
        const source = block ? block.querySelector(".copy-source") : null;
        if (!source) return;
        const text = source.value || source.textContent || "";
        try {
          await navigator.clipboard.writeText(text);
          btn.classList.add("copied");
          const original = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(() => {
            btn.classList.remove("copied");
            btn.textContent = original;
          }, 1200);
        } catch (err) {
          const range = document.createRange();
          range.selectNodeContents(source);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          document.execCommand("copy");
          selection.removeAllRanges();
        }
      });
    });
  }
  const observer = new MutationObserver(() => bindCopyButtons(document));
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener("load", () => bindCopyButtons(document));
</script>
        """
    )
    gr.Markdown(
        "# SpecTest-LLM\n"
        "Generate explainable, multi-category test cases using a multi-agent "
        "LangGraph pipeline."
    )

    with gr.Row():
        problem = gr.Textbox(
            label="Problem Statement",
            placeholder="Paste the full problem statement...",
            lines=8,
        )
        code = gr.Textbox(
            label="Source Code (optional)",
            placeholder="Paste code for analysis (optional)",
            lines=8,
        )

    description = gr.Textbox(
        label="User Description",
        placeholder="Add any extra context or summary...",
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
            maximum=50,
            value=5,
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

    run_btn = gr.Button("Generate Test Cases")

    gr.Markdown("## Generated Test Cases")
    cases_html = gr.HTML('<div class="cases-wrap"></div>')
    output = gr.Code(label="Generated Report (JSON)", language="json")

    run_btn.click(
        generate_tests,
        inputs=[
            problem,
            description,
            constraints,
            code,
            language,
            student_count,
            per_category,
        ],
        outputs=[cases_html, output],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        ssr_mode=False,
        show_error=True,
    )
