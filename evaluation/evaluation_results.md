# Evaluation Results Summary

## Summary Overview

Evaluation includes development-stage retrieval tests, automated
input validation tests, manual application testing, and a comparison
of three local language models.

- **Models compared:** llama3.2, qwen3.5:4b, qwen3.5:9b
- **Comparison scope:** Five prompts per model, 15 responses in total
- **RAG input validation:** Three automated tests passed
- **Selected model:** qwen3.5:9b

A single overall pass rate is not reported because these evaluations
measure different aspects of the system. Model review scores are
reported separately from functional test results.

## Key Findings

- Chain rule retrieval returned relevant formulas and source references.
- Updating the fractions source improved retrieval, but some material
  remained too advanced for beginners.
- Material generation worked through the application, but generated
  lessons could contain mathematical errors.
- The placeholder verifier was corrected to display lessons as
  UNVERIFIED rather than claiming that their content was checked.
- Qwen3.5:9b received the highest correctness and clarity scores
  in the five-prompt comparison, with a mean response time of 10.78 seconds.


## Preliminary RAG Retrieval Tests - Lauri

- Chain rule: successful. The search returned the correct module,
  chain rule formulas, and source references.
- Fractions: did not meet the learning objective. The search mainly
  returned properties of real numbers and order-of-operations material.
- Planned correction: change the fractions skill's source to the
  Rational Expressions module and repeat the retrieval test.

These are development-stage observations, not final evaluation results.



### Fractions retrieval: source correction - Lauri

Changed the fractions skill's source from module m51239
(Real Numbers: Algebra Essentials) to m51248 (Rational Expressions)
and rebuilt the index as openstax_math_e5_v2.

Retested using a question about simplifying fractions and the four
arithmetic operations. Results included calculation rules and a
numerical fraction-addition example.

Outcome: partially successful. Retrieval relevance improved, but
the first result involved complex algebraic fractions. The material
is better suited to revision than teaching fractions from scratch.


### RAG input validation - Lauri

Command:
python -m pytest tests/test_rag_validation.py -v

Result: 3 passed in 6.60 seconds.

Verified that unknown concept IDs and non-positive result counts
raise ValueError before accessing the Chroma collection.

These tests check input validation, not retrieval relevance.


## Preliminary llama3.2 Application Test - Lauri

### Method

A manual application test was performed using the local `llama3.2`
model through Ollama.

The learning goal was Chain rule. After selecting the goal, the
Get study material action generated lessons for prerequisite topics.

The lesson generation code supplied retrieved OpenStax text chunks
to the model. The displayed output was manually reviewed for successful
generation, source references, and mathematical correctness.

### Results

| Test ID | Check | Result |
| --- | --- | --- |
| llama32-initial-01 | Lessons, practice questions, and source references are displayed | Pass |
| llama32-initial-02 | Derivative rules worked example is mathematically correct | Fail |
| llama32-initial-03 | Function notation lesson uses a valid geometric example | Fail |

These are three checks of one preliminary application run, not three
independent model benchmark prompts. They should not be interpreted
as an overall model accuracy measurement.

### Observed Errors

The derivative rules lesson included an incorrect differentiation
example for f(x) = 3x^2 + 2x - 5. The correct derivative is 6x + 2,
but the generated working retained polynomial terms incorrectly.

The functions lesson described A = s^2 as the area of a triangle
with side length s. The formula describes the area of a square.

### Verification Status

During the initial test, lessons were labelled verified.
Inspection of verifier.py showed that it returned passed=True
unconditionally and did not check the content.

The placeholder verifier was changed to return passed=False with
a notice that automatic content verification is not implemented.

A subsequent UI test confirmed that lessons were displayed as
UNVERIFIED and that the notice was visible. This change corrected
the verification label; it did not correct generated mathematical
errors or implement factual verification.

### Interpretation and Limitations

The test confirmed that material generation worked through the
application, but the generated lessons contained mathematical errors
despite receiving retrieved source material.

Response time was not measured. The output was reviewed manually,
and the same prompts have not yet been run across multiple models.

A controlled model comparison is still required to assess correctness,
explanation clarity, and response time under comparable conditions.


## Model Comparison — 23 October 2026

### Method

We compared `llama3.2`, `qwen3.5:4b`, and `qwen3.5:9b` using
`scripts/compare_models.py`.

Each model answered the same five questions covering:

- Fraction arithmetic
- Function composition
- Limits
- Differentiation rules
- The chain rule

Source chunks were retrieved once per question and reused for all
models. Each prompt included up to three chunks, limited to the first
4,000 characters of each chunk.

The existing model client used `think=False` and `num_ctx=8192`.
Other generation settings used model defaults.

Each model received a separate warm-up request before testing.
Response time was measured around the complete generation call,
excluding retrieval and the warm-up request.

The test environment was Windows 11 with Python 3.12.15.
Each prompt was run once per model, producing 15 responses.
All generation requests completed with non-empty answers.

### Scoring

Answers were reviewed against the expected
results and supplied sources. Scores are subjective review judgments,
not automated accuracy measurements.

Correctness per answer:

- 0: Incorrect or unusable.
- 1: Partially correct, incomplete, or containing an incorrect claim.
- 2: Correct and sufficiently complete.

Correctness includes calculations, explanations, and claims about
the supplied sources.

Explanation clarity per answer:

- 1: Confusing or misleading.
- 2: Understandable but incomplete or imprecise.
- 3: Clear and suitable for a student.

### Summary Results

| Model | Correctness / 10 | Mean clarity / 3 | Mean response time |
| --- | --- | --- | --- |
| llama3.2 | 7 | 2.2 | 2.71 s |
| qwen3.5:4b | 8 | 2.2 | 4.53 s |
| qwen3.5:9b | 9 | 2.8 | 10.78 s |

### Scores by Question

Each cell shows correctness / clarity.

| Question | llama3.2 | qwen3.5:4b | qwen3.5:9b |
| --- | --- | --- | --- |
| Fractions | 2 / 3 | 2 / 3 | 2 / 3 |
| Function composition | 1 / 2 | 2 / 3 | 2 / 3 |
| Limits | 2 / 2 | 2 / 2 | 1 / 2 |
| Differentiation rules | 1 / 2 | 1 / 2 | 2 / 3 |
| Chain rule | 1 / 2 | 1 / 1 | 2 / 3 |

### Findings

**llama3.2**

The model was fastest and produced correct final calculations.
However, some explanations were inaccurate.

The composition answer incorrectly suggested that the two compositions
were unequal for every x. The differentiation answer stated the
constant multiple rule using misleading self-referential notation.
The chain rule answer incorrectly described the role of the inner
derivative in its closing explanation.

**qwen3.5:4b**

The model produced mostly relevant explanations, but its differentiation
answer omitted the requested final result, 6x + 2.

Its chain rule calculation was correct, but the explanation falsely
claimed that the total derivative could remain non-zero when the
outer derivative evaluated at the inner function was zero.

**qwen3.5:9b**

The model gave the clearest and most complete explanations overall,
with correct final calculations.

However, its limit answer incorrectly claimed that Source 1 supported
matching one-sided limits. The supplied source actually described
one-sided limits of 3 and 0.


### Decision and Limitations

We selected `qwen3.5:9b` because it received the highest correctness
and clarity scores in this comparison. 

This comparison used only five questions and one run per model.
Generation settings other than thinking mode and context size used
model defaults, which may differ between models. Timing may include
model reloads and depends on the test computer.

The comparison evaluates short, source-supported problem explanations.
It does not establish the quality of every generated lesson, quiz,
or the complete application workflow.


## Progress Persistence Test — 23 October 2026

After Real numbers and Order of operations were marked as known,
the application was stopped and restarted. The same learning goal
was selected again, and both skills remained marked as known.

Result: Pass. Skill status persisted across an application restart.


## Learning Progression Test — 23 October 2026

A manual UI test covered the learning path from Real numbers
and Order of operations to Algebraic expressions.

The assessment accepted correct answers and rejected an incorrect
answer. A score of 4/5 met the 80% threshold.

After completing the prerequisites, the Algebraic expressions quiz
was accessible. Submitting four correct answers and one incorrect
answer produced a passing result, and the target skill turned green.

Result: Pass for the tested learning path.

This test checks application behavior, not student learning outcomes
or the correctness of all generated study material.


## Failed Quiz and Retry Test — 23 October 2026

Submitting five incorrect answers produced a failed result of 0/5.
The application displayed the expected answers, explained the 80%
passing threshold, and offered a retry.

Clicking "Try again with new questions" opened a new quiz with
different questions.

Result: Pass for failure feedback and retry generation.