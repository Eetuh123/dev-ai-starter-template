import json
from pathlib import Path

from src.schemas.study import Concept, QuizQuestion
from src.capabilities.rag import retrieve
from src.services.quiz import generate_quiz

CONCEPTS_FILE = Path("data/concepts.json")
GENERATED_QS: dict[str, list[QuizQuestion]] = {}

def load_concepts():
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def get_assessment_concepts(goal_id: str):
    concepts = load_concepts()

    for concept in concepts:
        if concept["id"] == goal_id:
            return concept["prerequisites"]

    return []

def get_questions(concept_id: str) -> list[QuizQuestion]:
    if concept_id in GENERATED_QS:
        return GENERATED_QS[concept_id]

    concepts = load_concepts()

    concept_data = next(
        (item for item in concepts if item["id"] == concept_id),
        None,
    )

    if concept_data is None:
        return []

    concept = Concept.model_validate(concept_data)
    chunks = retrieve(concept_id)
    questions = generate_quiz(concept, chunks)

    GENERATED_QS[concept_id] = questions

    return questions

# Vanha koodi talteen perhaps
'''
base
from src.schemas.study import ConceptProgress, QuizQuestion

def next_question(goal: str, progress: dict[str, ConceptProgress]) -> QuizQuestion | None:
    if goal in progress:
        return None
    return QuizQuestion(id="fake-a1", concept_id=goal,
                        question="Differentiate x^2", answer="2*x", difficulty=1)

def find_gaps(goal: str, progress: dict[str, ConceptProgress]) -> list[str]:
    return [goal]
'''