import json

from pydantic import ValidationError

from src.models.model_client import (
    OllamaModelClient,
    ModelClientError,
    OllamaConnectionError,
    ModelNotFoundError,
)
from src.schemas.study import Concept, QuizQuestion, RagChunk


def generate_quiz(
    concept: Concept,
    chunks: list[RagChunk],
) -> list[QuizQuestion]:
    client = OllamaModelClient()

    context = "\n\n".join(
        f"Source: {chunk.book}, {chunk.section}\n{chunk.text}"
        for chunk in chunks
    )

    prompt = f"""
        Generate 5 mathematics assessment questions about this concept.

        Concept ID: {concept.id}
        Concept: {concept.name}
        Description: {concept.description}

        Use the source material when available:
        {context}

        Return only a JSON object with this structure:
        {{
        "questions": [
            {{
            "id": "q1",
            "concept_id": "{concept.id}",
            "question": "Differentiate sin(x^2)",
            "answer": "2*x*cos(x**2)",
            "difficulty": 2
            }}
        ]
        }}

        Requirements:
        - Generate exactly 5 questions.
        - Use unique question IDs.
        - Every concept_id must be "{concept.id}".
        - Difficulty must be an integer from 1 to 3.
        - Answers must be mathematically correct and SymPy-parseable.
        - Return only valid JSON, without Markdown.
        """

    for attempt in range(2):
        response = client.generate(prompt)

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

            return validated

        except (json.JSONDecodeError, ValidationError, ValueError, KeyError) as error:
            if attempt == 1:
                raise ValueError(
                    "Question generation failed validation after one retry."
                ) from error

            prompt = f"""
Your previous response was invalid.

Validation error:
{error}

Generate the complete set of 5 questions again for:
{concept.name} (concept ID: {concept.id})

Return only valid JSON using the exact same schema and requirements.
"""

    raise RuntimeError("Question generation failed.")


def check_answer(question: QuizQuestion, text: str) -> bool:
    return text.replace(" ", "") == question.answer