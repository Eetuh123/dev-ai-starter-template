import json
import re

from pydantic import ValidationError
from sympy import simplify
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

from src.models.model_client import (
    OllamaModelClient,
    ModelClientError,
    OllamaConnectionError,
    ModelNotFoundError,
)
from src.schemas.study import Concept, QuizQuestion, RagChunk

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

def _parse(text: str):
    return parse_expr(text.strip(), transformations=TRANSFORMS)


def generate_quiz(
    concept: Concept,
    chunks: list[RagChunk],
) -> list[QuizQuestion]:
    client = OllamaModelClient()

    context = "\n\n".join(
        f"Source: {chunk.book}, {chunk.section}\n{chunk.text}"
        for chunk in chunks
        if not chunk.id.startswith("fake")  # placeholder retrieve() chunks
    )

    prompt = f"""
        Generate 5 mathematics assessment questions about this concept.

        Concept ID: {concept.id}
        Concept: {concept.name}
        Description (may be in Finnish, use it only for understanding the topic): {concept.description}

        Use the source material when available:
        {context}

        Return only a JSON object with this structure:
        {{
        "questions": [
            {{
            "id": "q1",
            "concept_id": "{concept.id}",
            "question": "What is 1/2 + 1/4?",
            "answer": "3/4",
            "difficulty": 2
            }}
        ]
        }}

        Requirements:
        - Write every question in English, even if the description is in Finnish.
        - Generate exactly 5 questions.
        - Use unique question IDs.
        - Every concept_id must be "{concept.id}".
        - Difficulty must be an integer from 1 to 3.
        - Answers must be mathematically correct and SymPy-parseable.
        - Every question must test "{concept.name}" and nothing more advanced.
        - Each answer is a number or a short expression, never words.
        - Every question must ask for a value to compute, e.g. "Evaluate ...", "Simplify ..." or "Solve ...".
        - Return only valid JSON, without Markdown.
        """

    original_prompt = prompt

    for attempt in range(2):
        response = client.generate(prompt, format="json")

        try:
            data = json.loads(response)
            questions = data["questions"]

            if len(questions) != 5:
                raise ValueError("Exactly 5 questions are required.")

            validated = [
                QuizQuestion.model_validate(question)
                for question in questions
            ]

            ids = [question.id for question in validated]

            if len(ids) != len(set(ids)):
                raise ValueError("Question IDs must be unique.")

            if any(
                question.concept_id != concept.id
                for question in validated
            ):
                raise ValueError("Question concept IDs do not match.")

            for question in validated:
                try:
                    letters = re.sub(r"sqrt|sin|cos|tan|log|ln|exp|pi", "", question.answer)
                    if re.search(r"[A-Za-z]{2,}", letters):
                        raise ValueError("answer contains words")
                    _parse(question.answer)
                except Exception:
                    raise ValueError(
                        f"Answer for {question.id} is not SymPy-parseable."
                    )

            return validated

        except (json.JSONDecodeError, ValidationError, ValueError, KeyError) as error:
            if attempt == 1:
                raise ValueError(
                    "Question generation failed validation after one retry."
                ) from error

            prompt = f"""{original_prompt}

Your previous response was invalid.

Validation error:
{error}

Generate the complete set of 5 questions again for:
{concept.name} (concept ID: {concept.id})

Return only valid JSON using the exact same schema and requirements.
"""

    raise RuntimeError("Question generation failed.")


def check_answer(question: QuizQuestion, text: str) -> bool:
    try:
        return simplify(_parse(text) - _parse(question.answer)) == 0
    except Exception:
        return text.replace(" ", "") == question.answer