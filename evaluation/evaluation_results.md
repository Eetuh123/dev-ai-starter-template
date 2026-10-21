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