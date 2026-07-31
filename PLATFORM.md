# SpecTest-LLM — Platform Documentation & Change Log

*A coverage-driven, oracle-verified multi-agent framework for automated test-case
synthesis. This document explains the whole system end-to-end (architecture,
algorithms, and data contracts), records every change made during the Groq
migration and production hardening, and gives exact instructions to run and
reproduce it. It is written to be usable both as an onboarding document for a
collaborator and as the raw material for a methods/implementation section of a
research paper.*

---

## 1. Executive summary

SpecTest-LLM takes a programming problem (statement, optional constraints, and an
optional reference solution) and produces, for one or more simulated "students",
a set of **explainable, multi-category test cases**. It is deliberately more than
a thin wrapper around a chat model. A naïve LLM test generator uses the same model
as both the *input synthesizer* and the *answer key*, so its errors compound and
its "boundary" and "stress" labels are applied by intuition rather than by
anything measurable. SpecTest-LLM separates those roles and adds four measurable
mechanisms on top of a single Groq-hosted model (`openai/gpt-oss-120b`):

1. **Dual-oracle verification** — when a reference implementation is supplied, each
   generated input is *executed* in a sandboxed subprocess. The runtime return
   value becomes the ground truth (`expected_oracle`); the LLM's own guess
   (`expected`) is kept separately and the two are compared. The LLM is never the
   oracle.
2. **Spec-graph coverage model** — a typed graph of input dimensions, declared
   bounds, and semantic boundaries is extracted from the problem. It seeds the
   generator with concrete boundary values and lets us *measure* dimension
   coverage empirically rather than assert it.
3. **Coverage-aware diversity sampling** — pairwise Jaccard distance is computed
   per category and across students. Each student is conditioned on anti-examples
   of what previous students already produced, forcing concrete diversity.
4. **Low-discrimination detection** — every case is run against a library of
   deliberately wrong ("mutant") implementations. A case that yields the same
   answer for the correct code *and* every wrong one is flagged as
   low-discrimination: it passes broken code, so it does not help find bugs.

The pipeline emits a `PipelineMetrics` object with seven signals suitable for a
results table: `coverage_pct`, `oracle_match_rate`, `discrimination_mean`,
per-category `intra_diversity`, `inter_diversity`, `low_discrimination_ids`, and
`oracle_mismatches`.

---

## 2. What changed in this revision

Two workstreams were completed: (a) migrating the LLM backend from Google Gemini
to Groq Cloud, and (b) production-hardening the app (a UI startup bug and an
inert copy button). No changes were made to the scientific mechanisms — the
oracle, spec-graph, diversity, and discrimination logic are model-agnostic and
were left intact.

### 2.1 LLM backend: Gemini → Groq Cloud

The only place the provider is named is `llms.py`; every pipeline node calls a
single `build_llm(temperature)` factory, so the migration is genuinely a
one-file change plus dependency and documentation updates. Groq exposes an
**OpenAI-compatible** Chat Completions endpoint, so the switch is from
`langchain_google_genai.ChatGoogleGenerativeAI` to
`langchain_openai.ChatOpenAI` pointed at Groq's base URL.

`llms.py` now reads, in full:

```python
from __future__ import annotations
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

def build_llm(temperature: float, model_name: str | None = None) -> ChatOpenAI:
    api_key = os.getenv("GROQ_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("GROQ_CLOUD_API_KEY is not set in the environment.")
    return ChatOpenAI(
        model=model_name or GROQ_MODEL,
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=temperature,
        timeout=90,
        max_retries=2,
    )
```

Design notes worth capturing for the paper's reproducibility section:

- **One model, six temperatures.** Provider selection lives in exactly one place.
  Each agent role calls the factory with a role-specific temperature (see §4),
  which is the only knob that varies between nodes.
- **`base_url` is the whole trick.** Because Groq is OpenAI-compatible, no request
  or response reshaping was needed; LangChain's `ChatOpenAI` speaks the protocol
  directly. Swapping to any other OpenAI-compatible host later is again a
  one-line change.
- **Secret handling.** The key is read by reference from the environment
  (`GROQ_CLOUD_API_KEY`) and never hardcoded. `build_llm` fails fast with a clear
  error if it is missing.
- **Model override.** `GROQ_MODEL` may be set in `.env` to pin or change the model
  without touching code.

Supporting edits:

| File | Change |
| --- | --- |
| `requirements.txt` | `langchain-google-genai` → `langchain-openai>=0.2.0` |
| `.env.example` | `GEMINI_API_KEY` → `GROQ_CLOUD_API_KEY` (+ optional `GROQ_MODEL`), with a link to `https://console.groq.com/keys` |
| `app.py` | Error hint now names `GROQ_CLOUD_API_KEY`; subtitle reads "powered by Groq (openai/gpt-oss-120b)" |
| `README.md` | All four Gemini references replaced; module table and quickstart updated; rate-limit note rewritten for Groq's per-model limits (HTTP 429) |
| `Synopsis.md` | All remaining Gemini references replaced (model integration section, dependency list, architecture diagrams) |

A repository-wide search for `gemini`, `google`, and `genai` across all Python,
Markdown, and text files now returns **zero** matches.

### 2.2 UI fixes (production hardening)

Two real defects in `app.py` were corrected:

1. **Startup-breaking bug: `theme`/`css`/`js` on `launch()`.** In Gradio 5.x these
   are constructor arguments of `gr.Blocks(...)`, not `demo.launch(...)`. As
   written, `launch()` would raise `TypeError: got an unexpected keyword argument
   'theme'` and the app would never start — and even if it had, the entire custom
   dark theme and the clipboard JavaScript would have been silently dropped. They
   were moved onto `gr.Blocks(...)`, where they take effect. This is the single
   most important production-readiness fix: without it the demo does not launch.

2. **Inert "Copy everything" button.** The global copy button previously injected a
   `<script>` string into a Markdown component. Gradio sanitizes Markdown, so the
   script never executed and the button silently did nothing. The clipboard write
   now happens client-side through the event's `js=` hook
   (`(txt) => { if (txt) navigator.clipboard.writeText(txt); return [txt]; }`),
   which is reliable across Gradio 5.x, while Python only sets the confirmation
   status text. The per-student "Copy all" / "Copy JSON" buttons were already
   correct (bound via a `MutationObserver` in `CUSTOM_JS`) and were left as is.

Everything else in the UI was already solid: a responsive card grid, a
paper-grade metrics banner, per-category diversity pills, a spec-graph panel,
oracle ✓/✗ chips per case, worked examples, and graceful error boxes.

---

## 3. System architecture

The pipeline is a **LangGraph `StateGraph`**. A single typed `GraphState`
dictionary is threaded through the nodes; each node returns a partial dict that
is merged into the state.

```
start ──┬─> spec ────────┐
        ├─> analysis ─────┤
        └─> spec_graph ───┴─> plan ─> generate ─> discrimination ─> metrics ─> feedback ─┐
                                                                                          │
                                                            refine (≤ 1 cycle) ◄──────────┘
                                                                                          │
                                                                                        END
```

`start` fans out to three **parallel preparation** nodes — `spec`, `analysis`, and
`spec_graph` — which have no dependencies on one another. All three converge on
`plan`. The generator then runs once per student. `discrimination` and `metrics`
compute the evaluation signals, and `feedback` decides whether a single refinement
cycle back to `plan` is warranted (`MAX_REFINES = 1`).

### Module map

| File | Responsibility |
| --- | --- |
| `app.py` | Gradio UI: inputs, sliders, examples, copy buttons, error handling, HTML report renderer, metrics panel. |
| `graph.py` | LangGraph pipeline: node definitions, category enforcement, JSON repair, retries, oracle wiring, type coercion, refinement routing. |
| `agents.py` | Prompt templates and Pydantic parsers for each LLM role, plus the six-category rubric. |
| `schemas.py` | Pydantic v2 models — the data contract between every stage. |
| `spec_graph.py` | Typed input-dimension model, deterministic boundary sampling, empirical coverage measurement, heuristic fallback. |
| `oracle.py` | Subprocess-based Python execution with resource limits and JSON I/O markers. |
| `discrimination.py` | Adversarial ("mutant") implementation templates and per-case discrimination scoring. |
| `diversity.py` | Jaccard-based intra-category and inter-student diversity; anti-example rendering. |
| `metrics.py` | `PipelineMetrics` aggregation, summary line, dict round-trip. |
| `llms.py` | `ChatOpenAI` factory pointed at Groq's OpenAI-compatible endpoint; loads `GROQ_CLOUD_API_KEY`. |

---

## 4. The agents (nodes)

Each node builds its own LLM at a role-specific temperature. Preparation and
verification nodes want determinism; the generator wants controlled variety.

| Node | Temp | Chain style | Output schema | Purpose |
| --- | --- | --- | --- | --- |
| `spec` | 0.2 | `prompt \| llm \| parser` (strict) | `Spec` | Extract summary, input/output format, constraints, edge & hidden cases. |
| `analysis` | 0.2 | `prompt \| llm \| parser` (strict) | `CodeAnalysis` | Reason about loops, conditions, risks, assumptions from the source (no execution). Skipped when no code is supplied. |
| `spec_graph` | 0.1 | `prompt \| llm` (raw + repair) | `SpecGraph` | Extract typed input dimensions, bounds, and semantic boundaries. |
| `plan` | 0.3 | `prompt \| llm \| parser` (strict) | `TestPlan` | Design a balanced six-category plan; per-category targets are then overwritten deterministically. |
| `generate` | 0.5 | `prompt \| llm` (raw + repair) | `TestCaseList` | Per student, synthesize cases in every category, conditioned on anti-examples. |
| `feedback` | 0.2 | `prompt \| llm \| parser` (strict) | `FeedbackSignal` | Decide whether one refinement cycle is needed. |

**Why two chain styles.** Nodes with tightly-shaped output use LangChain's
`PydanticOutputParser` for strict validation. The two nodes most prone to
free-form drift — the spec-graph extractor and, especially, the bulk test
generator — instead take the **raw** model text and run it through a hand-rolled
repair pipeline (§6). This matters more with a reasoning model like
`gpt-oss-120b`, which can wrap answers in prose or emit Python-ish literals; the
repair path recovers valid JSON where a strict parser would simply throw.

**Category rubric.** `agents.py` defines `CATEGORY_RUBRIC`, six verbatim
definitions — *Basic, Boundary, Random, Stress, Invalid/robustness, Bug-targeted*
— injected into both the plan and generator prompts so the model applies the
labels consistently rather than by feel.

**Retry policy.** Every LLM call is wrapped by `_retry_invoke`, which retries only
on thrown exceptions (`LLM_RETRIES = 2`, up to three attempts) with linear
backoff (`2.0 × attempt` seconds). Parse failures inside the generator do not
throw — they return an empty list and are recorded as an issue instead — so the
whole run degrades gracefully rather than crashing.

---

## 5. The four novel mechanisms

### 5.1 Dual-oracle verification (`oracle.py`, `graph.py`)

When a Python reference solution is provided, `_detect_oracle_entry` finds its
entry function by regex (preferring a non-dunder name that is not `main`,
`Solution`, or `Test`). For each generated case, `_run_oracle_for_case`:

1. Coerces the LLM input toward the spec-graph's declared types
   (`_coerce_input_to_spec` — e.g. the string `"7"` becomes the integer `7`).
2. Shapes the payload for the call convention (`args_list`, `kwargs`, or
   `stdin_single_arg`).
3. Executes the reference in a sandboxed subprocess and captures the JSON return
   value as `expected_oracle`.
4. Sets `oracle_match = (oracle_value == case.expected)`, comparing the ground
   truth against the LLM's own guess.

The subprocess harness (`oracle.py`) is the security-critical piece: it runs
`python3 -I` (isolated mode) on a generated wrapper, starts a new session with
`os.setsid()` so the whole tree can be killed, applies POSIX resource limits
(`RLIMIT_AS` 256 MB, `RLIMIT_CPU` 5 s), enforces a wall-clock timeout (1.5 s in
the pipeline), and communicates results through `###STDOUT###…###END###` markers
so ordinary prints from user code cannot corrupt the parsed value.

### 5.2 Spec-graph coverage model (`spec_graph.py`)

The `SpecGraph` is a typed model of the problem's input surface: a list of
`Dimension`s (name, type, role, min/max, semantic boundaries) plus `Invariant`s
and a call style. It is extracted by the `spec_graph` node and, if that fails,
falls back to a heuristic that mines numeric ranges out of the constraints text
(`fallback_spec_graph`).

Two deterministic operations make coverage *measurable* rather than asserted:

- **Boundary sampling** (`_sample`) generates concrete candidates per dimension —
  declared semantic boundaries first, then `{lo, lo+1, mid, hi−1, hi}` clamped to
  range and de-duplicated. These seed the generator prompt with real edge values.
- **Coverage percentage** (`coverage_pct`) is the fraction of input dimensions for
  which at least one produced case matches a boundary sample:

  ```
  coverage_pct = (# input dimensions with a matching case) / (# input dimensions)
  ```

  Numeric matching uses a tolerance of `|a − b| ≤ max(1.0, 0.05·|b|)` so that a
  case landing near a boundary still counts.

### 5.3 Coverage-aware diversity sampling (`diversity.py`)

Diversity is average pairwise **Jaccard distance** (`1 − similarity`) over case
*inputs*. The signature used for each input is shape-aware: strings become
character 3-grams, numeric lists become 8-bin histograms, and everything else
becomes token 2-grams. Two headline signals:

- **Intra-category diversity** — mean pairwise distance within each category, per
  student. Low values mean the model produced near-duplicate cases.
- **Inter-student diversity** — mean pairwise distance between students'
  aggregated input signatures. This is what "different students" is supposed to
  mean, made concrete.

The generator is actively pushed toward diversity: before student *k* runs,
`_anti_examples_text` renders a sample of every earlier student's inputs into the
prompt with an explicit instruction to pick different values. A per-student
deterministic seed (`_build_student_seed`) additionally jitters numeric input
pairs so repeated runs are reproducible yet distinct.

### 5.4 Low-discrimination detection (`discrimination.py`)

`adversarial_implementations` produces eleven deliberately-wrong Python
implementations of the entry function (constant outputs, identity, reverse,
off-by-one, wrong operator, sign/bool errors, etc.). For each case,
`score_case` runs the reference and every mutant on the same input:

```
discrimination_score = (# mutants whose output differs from the reference) / (# usable mutants)
```

A score of `0` means the case cannot distinguish correct code from any broken
version — it is **low-discrimination** and is surfaced to the user; a score of `1`
means it "kills" every mutant. Mutant comparison uses a numeric tolerance of
`|a − b| ≤ max(1.0, 1e−6·|b|)` and recurses element-wise over equal-length lists.
To keep the demo responsive, scoring is capped at two cases per category with a
0.6 s per-call timeout.

---

## 6. JSON robustness for a reasoning model (`graph.py`)

Reasoning models emit valid answers that are not always valid JSON: markdown
fences, trailing commas, Python `True/False/None`, or expression literals such as
`"ab" * 3` and `"x".repeat(5)`. Rather than rejecting these, `_parse_case_list`
runs a repair pipeline before validation:

1. `_strip_markdown` — remove ```` ```json ```` fences.
2. `_rewrite_repeat_calls` — turn `"x".repeat(5)` into `"x" * 5`.
3. `_replace_string_expressions` — safely evaluate string concatenation/repetition
   expressions with a tiny bespoke tokenizer/parser (no `eval`), capping results
   at 200 characters.
4. `_extract_json_blob` — slice out the outermost `{…}` or `[…]`.
5. `_normalize_pythonish` — `True/False/None` → `true/false/null`; strip trailing
   commas.
6. `json.loads` → `TestCaseList.model_validate`.

The expression evaluator is intentionally *not* a general interpreter: it only
accepts string/int literals joined by `+` and `*`, so there is no code-execution
surface. If any step fails, the function returns an empty `TestCaseList` and the
run continues. After parsing, `_enforce_targets` normalizes free-form category
labels to the six canonical names and trims each category to its target count,
reporting any shortfall as an issue that can trigger the single refinement cycle.

---

## 7. Data contracts (`schemas.py`)

All inter-node data is typed with Pydantic v2, which is what makes the pipeline
composable and testable. The central models are `Spec`, `CodeAnalysis`,
`TestPlan`, `TestCase`, `StudentTestSuite`, `FeedbackSignal`, and the top-level
`FinalReport`. A `TestCase` is the atom of the system and deliberately carries
*both* answers side by side so the oracle disagreement is first-class:

```python
class TestCase(BaseModel):
    id: str = ""
    student_id: int = 0
    category: str
    input: Any
    expected: Optional[Any] = None          # the LLM's guess
    expected_oracle: Optional[Any] = None   # ground truth from execution
    explanation: str
    oracle_match: Optional[bool] = None      # expected == expected_oracle ?
    oracle_error: Optional[str] = None
    discrimination_score: Optional[float] = None
```

`FinalReport.meta` carries the serialized `spec_graph` and the `PipelineMetrics`
dict, which is exactly what the UI renders in its metrics and spec-graph panels.

---

## 8. Metrics reference (`metrics.py`)

`PipelineMetrics` is the paper-facing artifact. Each field is one column in a
results table, computed as follows:

| Metric | Definition |
| --- | --- |
| `coverage_pct` | Fraction of input dimensions covered by ≥1 boundary-matching case (§5.2). |
| `oracle_match_rate` | Over cases with a runnable oracle, fraction where the LLM's `expected` equals the executed ground truth. |
| `discrimination_mean` / `discrimination_min` | Mean / min discrimination score over sampled cases (§5.4). |
| `intra_diversity` | Per-category mean pairwise Jaccard distance of inputs. |
| `inter_diversity` | Mean pairwise Jaccard distance between students. |
| `low_discrimination_ids` | Case IDs with discrimination below `0.3`. |
| `oracle_mismatches` | List of `{student_id, case_id, category, llm_expected, oracle_expected}` where the LLM disagreed with the oracle. |
| `n_students`, `n_cases`, `duration_ms` | Bookkeeping. |

`metrics_summary_line` renders a one-line log/banner form of all of the above.

---

## 9. Security & sandboxing

Because arbitrary reference/student code is executed, the oracle is the trust
boundary. Its defenses: isolated interpreter (`python3 -I`), a dedicated process
group killable as a tree, `RLIMIT_AS` 256 MB and `RLIMIT_CPU` 5 s, a wall-clock
timeout (1.5 s pipeline / 0.6 s discrimination), output-size limits, and
marker-delimited result parsing so program output cannot spoof the return value.
This is a strong sandbox for a research demo but is *not* a substitute for OS-level
isolation (containers/VMs) if untrusted code from the public is ever run at scale
— call that out explicitly in the paper's threat-model discussion.

On secrets: `.env` is git-ignored and must never be committed; the API key is only
ever read from the environment by reference. Groq's free tier enforces per-model
request- and token-rate limits (HTTP 429) — budget batch experiments accordingly.

---

## 10. Running the platform (on your Mac)

The project targets Python 3.12 (its virtual environment, `.chain-env`, was built
against pyenv 3.12.8). Run these from the project folder:

```bash
cd "~/Desktop/test_case generation"

# 1) Create & activate a fresh virtual environment
python3 -m venv .chain-env
source .chain-env/bin/activate

# 2) Install dependencies (now Groq/OpenAI-compatible, no Google packages)
pip install -r requirements.txt

# 3) Configure your key
cp .env.example .env
#   then edit .env and set:
#   GROQ_CLOUD_API_KEY=gsk_...your key from https://console.groq.com/keys
#   (optionally) GROQ_MODEL=openai/gpt-oss-120b

# 4) Sanity-check the backend without the UI (one cheap request):
python -c "from llms import build_llm; print(build_llm(0.2).invoke('say hi').content)"

# 5) Run the full test suite (no API calls; validates all helper logic)
python -m pytest tests/ -v

# 6) Launch the web app
python app.py          # opens http://localhost:7860
```

Notes:

- Steps 4–6 must be run **on your Mac**, not in this assistant's sandbox, because
  the sandbox has no outbound network and cannot reach Groq or install packages.
- If step 4 raises `GROQ_CLOUD_API_KEY is not set`, the `.env` was not loaded from
  the current directory — run from the project root.
- If you see HTTP 429, you have hit Groq's rate limit; lower the student count or
  wait before re-running.

The `curl` shape Groq expects (for reference) is:

```bash
curl https://api.groq.com/openai/v1/chat/completions -s \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_CLOUD_API_KEY" \
  -d '{"model":"openai/gpt-oss-120b","messages":[{"role":"user","content":"ping"}]}'
```

---

## 11. Testing status

The suite in `tests/test_smoke.py` contains **44** unit tests covering category
normalization and enforcement, the JSON repair pipeline, refinement routing,
oracle execution (including timeout and error propagation), spec-graph parsing /
fallback / coverage, type coercion, diversity metrics, discrimination scoring, and
metric aggregation. Crucially, **none of them call the LLM**, so they are provider-
agnostic — the Gemini→Groq migration does not change their behavior. Every source
file compiles cleanly (`py_compile`). The end-to-end path (a live run against
Groq) can only be exercised on your Mac, per §10.

---

## 12. Suggested experiments for the paper

Each of the seven metrics is a row in the results table. Suggested baselines:

- **Single-prompt LLM** — one prompt, no oracle, no diversity loop.
- **Multi-agent (no oracle)** — the full pipeline minus `discrimination`,
  `metrics`, and oracle execution.
- **SpecTest-LLM (full)** — the pipeline as shipped.
- **Classical search-based generators** — EvoSuite / Pynguin as external points
  of comparison.

Dataset: 20–30 problems spanning arithmetic, string manipulation, dynamic
programming, and graphs, each run with and without a reference implementation to
exercise both the oracle-verified and unverified paths. The natural ablations map
directly onto the four mechanisms in §5.

---

## 13. Limitations & future work

The oracle currently executes **Python only**; other languages are accepted as
input but skip execution-based verification (so `oracle_match_rate` and
discrimination are undefined for them). Coverage is measured over declared input
dimensions, not over reference-code branches — pairing the spec-graph signal with
real branch/path coverage of the reference would strengthen the coverage claim.
The refinement loop is capped at a single cycle for latency; making the cap
configurable and studying its effect on the metrics is an easy, publishable
ablation. Finally, the sandbox is process-level, not OS-level; scaling to
untrusted submissions warrants container isolation.

---

## 14. Change log (quick reference)

| # | Area | Change | Files |
| --- | --- | --- | --- |
| 1 | Backend | Gemini `ChatGoogleGenerativeAI` → Groq `ChatOpenAI` (OpenAI-compatible endpoint), key by env reference, fail-fast | `llms.py` |
| 2 | Deps | `langchain-google-genai` → `langchain-openai` | `requirements.txt` |
| 3 | Config | `GEMINI_API_KEY` → `GROQ_CLOUD_API_KEY` (+ optional `GROQ_MODEL`) | `.env.example` |
| 4 | UI copy | Error hint & subtitle now name Groq / `openai/gpt-oss-120b` | `app.py` |
| 5 | UI bug | Moved `theme`/`css`/`js` from `launch()` to `gr.Blocks()` — app now starts and styling applies | `app.py` |
| 6 | UI bug | "Copy everything" now writes to the clipboard via the event `js=` hook instead of an inert injected `<script>` | `app.py` |
| 7 | Docs | Removed all Gemini references; rewrote rate-limit and integration sections for Groq | `README.md`, `Synopsis.md` |
| 8 | Docs | This platform document | `PLATFORM.md` |
```
