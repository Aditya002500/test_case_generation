# SpecTest-LLM

A coverage-driven, oracle-verified multi-agent framework for automated test
case synthesis. Built for both an interactive research demo and as a
reproducible baseline for the paper.

## What's novel (paper contributions)

A naïve LLM-in-the-loop test generator is a thin prompt over a chat model:
it is fast to build, but the LLM is both the *input synthesizer* and the
*answer key*, so errors compound, categories are mis-applied, and "boundary
case" gets defined by vibes. SpecTest-LLM introduces four measurable
mechanisms on top of the same Groq (`openai/gpt-oss-120b`) backbone:

1. **Dual-Oracle verification.** When a reference implementation is
   provided, each generated input is executed in a sandboxed subprocess
   (`oracle.py`) with strict timeouts and resource limits. The runtime
   return value becomes the ground-truth `expected_oracle`; the LLM's own
   `expected` is kept as a separate field and the two are compared. The
   LLM is the input synthesizer only, never the oracle.
2. **Spec-graph coverage model.** A typed graph (`spec_graph.py`) of input
   dimensions, declared bounds, and semantic boundaries is extracted from
   the problem statement. The graph is used to (a) seed the test plan with
   concrete boundary values, (b) drive type-coerced oracle calls, and
   (c) measure dimension coverage empirically.
3. **Coverage-aware diversity sampling.** Pairwise Jaccard distance is
   computed per category and across students (`diversity.py`). The
   generator is conditioned on anti-examples of cases already produced,
   forcing concrete diversity between students. Intra-category and
   inter-student Jaccard are reported as first-class metrics.
4. **Low-discrimination test detection.** Each test is evaluated against a
   library of adversarial "obviously wrong" implementations
   (`discrimination.py`). A case that produces the same output for the
   reference and every wrong impl is flagged as a low-discrimination
   test and surfaced to the user.

The pipeline produces a `PipelineMetrics` object (`metrics.py`) with
seven measurable signals suitable for inclusion in the paper's results
section: `coverage_pct`, `oracle_match_rate`, `discrimination_mean`,
`intra_diversity` per category, `inter_diversity`, `low_discrimination_ids`,
and `oracle_mismatches`.

## Architecture

```
start ──> spec ──┐
      ──> analysis ─┤
      ──> spec_graph ─┴─> plan ──> generate ──> discrimination ──> metrics ──> feedback ─┐
                                                                                         │
                                                                  refine (≤ 1 cycle) ◄───┘
                                                                                         │
                                                                                       END
```

`spec`, `analysis`, `spec_graph` run in parallel as preparation. The
generator runs once per student, producing per-category cases. The
discrimination step runs adversarial implementations only when a Python
reference is provided. `metrics` aggregates all signals and `feedback`
decides whether to refine.

## Modules

| File                | Responsibility                                                            |
| ------------------- | ------------------------------------------------------------------------- |
| `app.py`            | Gradio UI: inputs, sliders, examples, copy buttons, error handling, metrics panel. |
| `graph.py`          | LangGraph pipeline, category enforcement, JSON repair, retries, coercion. |
| `agents.py`         | Prompt templates and parsers for each LLM role, including spec-graph.     |
| `oracle.py`         | Subprocess-based Python execution; resource limits; JSON I/O markers.     |
| `spec_graph.py`     | Typed input-dimension model, coverage measurement, fallback extraction.   |
| `diversity.py`      | Jaccard-based intra-category and inter-student diversity, anti-examples.  |
| `discrimination.py` | Adversarial impl templates and per-case discrimination scoring.            |
| `metrics.py`        | `PipelineMetrics` aggregation, summary line, dictionary round-trip.       |
| `schemas.py`        | Pydantic models: data contract between every stage.                      |
| `llms.py`           | `ChatOpenAI` factory (Groq OpenAI-compatible endpoint); loads `GROQ_CLOUD_API_KEY`. |

## Quickstart

```bash
python -m venv .chain-env
source .chain-env/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put your Groq Cloud key in .env
python app.py          # http://localhost:7860
```

The UI shows, in addition to the test cases: a top metrics banner
(coverage %, oracle match %, mean discrimination, inter-diversity, total
cases), an intra-diversity pill per category, a warning list for
low-discrimination cases and oracle mismatches, and a chip on each case
card showing `oracle ✓` or `oracle ✗` plus the ground-truth value.

## Experiments

Each of the seven signals is a row in the experiments table. Suggested
baselines for the paper:

- **Single-prompt LLM** — one prompt, no oracle, no diversity loop.
- **Multi-agent (no oracle)** — the same pipeline minus `node_metrics`,
  `node_discrimination`, and oracle calls.
- **SpecTest-LLM (full)** — the pipeline as shipped.
- **EvoSuite / Pynguin** — classical search-based test generators.

Datasets: a curated set of 20–30 programming problems spanning
arithmetic, string manipulation, dynamic programming, and graph problems.
Each problem is run with and without a reference implementation to
exercise both oracle and disagreement-voting paths.

## Tests

```bash
python -m pytest tests/ -v
```

44 unit tests cover parsing, normalization, enforcement, refinement,
oracle execution (including timeout), spec-graph extraction and
coverage, diversity metrics, discrimination scoring, and metric
aggregation. Tests run without LLM calls.

## Security

Never commit `.env`. Groq Cloud enforces per-model rate limits (requests
and tokens per minute/day) on the free tier; budget accordingly when
running the experiments and watch for HTTP 429 responses. Oracle
subprocesses are sandboxed with rlimits (256 MB address space, 5s CPU)
and a 1.5s wall-clock timeout.
