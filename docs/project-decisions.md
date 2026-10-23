# Project decisions

## Decision 1 — Model selection

**Decision:**

Use `qwen3.5:9b` as the preferred model based on preliminary testing.
Confirm the selection with a documented comparison.

**Alternatives considered:**

- `llama3.2` (3B): our initial baseline.
- `qwen3.5:4b`: tested by a team member.
- `qwen3.5:9b`: tested by a team member.

**Why we chose this:**

Our initial application tests with `llama3.2` produced mathematical
errors despite using retrieved textbook material.

The conducted tests showed that `qwen3.5:4b` produced better results
than `llama3.2`, and that `qwen3.5:9b` performed better still.
Based on these preliminary observations, we intend to use
`qwen3.5:9b`.

These observations are qualitative. A comparison using the same
5–10 mathematics prompts and source texts is still needed to
document correctness, explanation clarity, and response time.

| Model | Preliminary observation | Correctness score | Clarity score | Response time |
| --- | --- | --- | --- | --- |
| llama3.2 | Mathematical errors observed in generated lessons | Pending | Pending | Not measured |
| qwen3.5:4b | Reported improvement over llama3.2 by a team member | Pending | Pending | Not recorded |
| qwen3.5:9b | Reported as the best of the three; preferred model | Pending | Pending | Not recorded |

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