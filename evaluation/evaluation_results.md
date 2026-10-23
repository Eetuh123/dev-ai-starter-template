# Evaluation Results Summary

Document your team's evaluation results below.

## Summary Overview

- **Date of Evaluation:** YYYY-MM-DD
- **Model Evaluated:** (e.g., `llama3.2`)
- **Total Test Cases Executed:** 0
- **Passed:** 0
- **Failed:** 0
- **Pass Rate:** 0%

## Performance by Category

| Category | Total Cases | Passed | Failed | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| Successful Cases | 0 | 0 | 0 | 0% |
| Difficult Cases | 0 | 0 | 0 | 0% |
| Failure / Edge Cases | 0 | 0 | 0 | 0% |

## Key Findings & Failure Analysis

### What worked well
- Observation 1
- Observation 2

### Observed failure modes
- Description of case where the system failed and why.

## Action Items & Improvements
- [ ] Planned fix or enhancement based on evaluation findings.


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