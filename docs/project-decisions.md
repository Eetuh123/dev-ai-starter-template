# Project decisions

## Decision 1 — Model selection

**Decision:**

Select `qwen3.5:9b` for the project based on our exploratory
comparison of three local models.

**Alternatives considered:**

- `llama3.2`
- `qwen3.5:4b`
- `qwen3.5:9b`

**Why we chose this:**

We tested each model with the same five mathematics prompts and
the same retrieved source texts. Qwen3.5:9b received the highest
review scores for correctness and explanation clarity, although
it was slower than the smaller models.

| Model | Correctness / 10 | Mean clarity / 3 | Mean response time |
| --- | --- | --- | --- |
| llama3.2 | 7 | 2.2 | 2.71 s |
| qwen3.5:4b | 8 | 2.2 | 4.53 s |
| qwen3.5:9b | 9 | 2.8 | 10.78 s |

Response times were measured automatically. Correctness and clarity
were assessed by reviewing the saved answers.

We prioritize explanation quality over response speed for this
study assistant. 

This was a small comparison with one response per prompt per model.
It supports our project decision but does not neccesserily establish general
model accuracy. Detailed findings are recorded in
`evaluation/evaluation_results.md`.

---

## Decision 2 — Additional AI capability

**Decision:**

Use RAG with OpenStax textbooks, Chroma, and the
`intfloat/multilingual-e5-small` embedding model.

A map of 74 skills connects topics to prerequisites and source modules.
Books are converted to Markdown with LaTeX formulas and split into
chunks tagged with skill IDs and source references.

**Why it is needed:**

Retrieval supplies relevant textbook material for lesson generation
and allows the application to display source references.

Generated lessons can still contain errors. Automatic content
verification is not implemented, so lessons are marked UNVERIFIED.

**Alternatives considered:**

Generating lessons without retrieved sources and using keyword
search alone.

---

## Decision 3 — Architecture

**Decision:**

All UI interactions pass through `src/services/ai_service.py`.
Retrieval, lesson generation, assessment, and memory remain
separate components coordinated by the service.

**Why:**

This allows team members to develop their components independently
and replace mock implementations through shared interfaces.

On Windows, Chroma is stored in
`%LOCALAPPDATA%\dev-ai-project\chroma`.
This location worked after the database in the OneDrive project
directory produced an index loading error.

Books and generated RAG data are excluded from Git.
The README provides instructions for building the local index.