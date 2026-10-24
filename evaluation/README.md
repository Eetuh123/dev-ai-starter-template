# Evaluation Results

## 1. Evaluation Overview

The application was evaluated using manual UI tests, manual retrieval tests, a manual review of generated study material, and automated `pytest` tests. The evaluation focused on three main areas: study material generation using the Llama 3.2 model, retrieval-augmented generation (RAG), and error handling for invalid retrieval requests.

The test cases were divided into successful cases, difficult cases, and failure cases. Each test was assigned a status of `pass`, `fail`, or `partial` based on the observed results and the expected behavior.

## 2. Test Results

A total of nine test cases were evaluated. The results were:

- **Passed:** 6
- **Failed:** 2
- **Partially passed:** 1

### 2.1 Successful Cases

The successful cases tested whether the application could generate study material and retrieve relevant textbook content.

In the preliminary UI test (`llama32-01`), the application successfully generated study lessons for the prerequisites of the Chain Rule topic. The output included practice questions and references to OpenStax books and sections. Material generation completed without an Ollama connection error.

The retrieval test (`rag-01`) successfully returned three relevant chunks about the Chain Rule from *Calculus Volume 1*, module `m53581`. The results included the Chain Rule formula, Leibniz notation, and source URLs.

These results demonstrate that the application can generate study material and retrieve relevant mathematical source content under the tested conditions.

### 2.2 Difficult Cases

The difficult cases examined mathematical correctness, the relevance of retrieved content, and the handling of a Finnish mathematical term.

The manual review of the derivative rules lesson (`llama32-02`) identified incorrect differentiation. The generated example for \(f(x) = 3x^2 + 2x - 5\) did not produce the correct derivative, \(f'(x) = 6x + 2\), and included an incorrect explanation of why the constant term disappears. This test failed because the generated lesson contained mathematical errors.

The functions lesson review (`llama32-03`) also failed. The generated lesson used \(A = s^2\) as the area formula for a triangle, although this formula represents the area of a square.

The Finnish retrieval test (`rag-02`) passed. The query for *ketjusääntö* was mapped to the Chain Rule topic, and the system returned relevant material from the expected textbook module. This demonstrates support for the tested Finnish alias, but it does not establish general multilingual retrieval performance.

The fraction retrieval test (`rag-03`) partially passed. The results contained relevant arithmetic rules and a numerical example of fraction addition. However, the first result focused on complex algebraic fractions, making it too advanced for a beginner. Changing the source module improved relevance but did not fully resolve the difficulty-level mismatch.

### 2.3 Failure and Error-Handling Cases

The failure cases tested whether the retrieval system handled invalid requests appropriately.

The automated test for an unknown concept (`rag-04`) passed. It confirmed that the system raised a `ValueError` before accessing the Chroma collection.

The two invalid result-count tests (`rag-05` and `rag-06`) also passed. Both zero and negative values for `top_k` were rejected with a `ValueError` before the Chroma collection was accessed.

These results indicate that the tested input-validation checks prevent invalid retrieval requests from proceeding to the database layer. However, these tests do not cover all possible failure conditions, such as connection interruptions or malformed model responses.

## 3. Summary and Discussion

The evaluation showed that the application could generate study material, retrieve relevant textbook content, recognize the tested Finnish alias, and reject invalid retrieval requests. However, the manual lesson reviews revealed a significant limitation: successful generation does not guarantee mathematical correctness.

The derivative rules and functions lessons both contained mathematical errors. The fraction retrieval test also showed that relevant search results may still be too advanced for the intended learner. These findings indicate that source retrieval and lesson generation need to be evaluated separately.

The results support the use of source references and verification mechanisms to help identify potential problems in generated material. Nevertheless, the tests do not establish that all generated lessons are correct or that verification detects every mathematical error.

## 4. Limitations

The evaluation was limited to nine test cases, and several tests were conducted manually. The results therefore provide an initial assessment rather than comprehensive evidence of system reliability.

Response times were not measured in the Llama 3.2 UI tests. The evaluation also did not systematically test large inputs, ambiguous learning goals, empty user inputs, connection failures, or the ability of the verification mechanism to detect known mathematical errors.

Further testing should include additional mathematical topics, more beginner-level retrieval queries, automated checks for known mathematical results, and tests of controlled error handling when the model or retrieval service is unavailable.

## 5. Conclusion

The application demonstrated working study material generation and retrieval functionality, as well as successful validation of the tested invalid retrieval requests. However, the evaluation identified mathematical correctness and retrieval difficulty as areas requiring improvement.

The most important next step is to strengthen the validation of generated lessons and evaluate whether the verification mechanism reliably identifies incorrect mathematical explanations. Further testing should also assess whether retrieved material is appropriate for the learner's level and whether the application handles failures consistently.
