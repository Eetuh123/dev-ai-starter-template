import json
from pathlib import Path
from src.schemas.study import QuizQuestion

CONCEPTS_FILE = Path("data/conceptsMockup.json")

DEMO_QUESTIONS = {
    "functions": [
        QuizQuestion(
            id="functions-1",
            concept_id="functions",
            question="If f(x) = x², what is f(3)?",
            answer="9",
            difficulty=1,
        ),
        QuizQuestion(
            id="functions-2",
            concept_id="functions",
            question="If f(x) = 2x + 1, what is f(4)?",
            answer="9",
            difficulty=1,
        ),
    ],

    "function_composition": [
        QuizQuestion(
            id="composition-1",
            concept_id="function_composition",
            question="What does f(g(x)) represent?",
            answer="The composition of f and g.",
            difficulty=1,
        ),
        QuizQuestion(
            id="composition-2",
            concept_id="function_composition",
            question="If f(x) = x + 1 and g(x) = 2x, what is f(g(2))?",
            answer="5",
            difficulty=1,
        ),
    ],

    "limits": [
        QuizQuestion(
            id="limits-1",
            concept_id="limits",
            question="What is the limit of x + 2 as x approaches 3?",
            answer="5",
            difficulty=1,
        ),
        QuizQuestion(
            id="limits-2",
            concept_id="limits",
            question="What does a limit describe?",
            answer="The value a function approaches.",
            difficulty=1,
        ),
    ],

    "derivative_rules": [
        QuizQuestion(
            id="derivative-1",
            concept_id="derivative_rules",
            question="What is the derivative of x²?",
            answer="2x",
            difficulty=1,
        ),
        QuizQuestion(
            id="derivative-2",
            concept_id="derivative_rules",
            question="What is the derivative of a constant?",
            answer="0",
            difficulty=1,
        ),
    ],

    "chain_rule": [
        QuizQuestion(
            id="chain-1",
            concept_id="chain_rule",
            question="When is the chain rule used?",
            answer="When differentiating a composite function.",
            difficulty=1,
        ),
    ],
}

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
    return DEMO_QUESTIONS.get(concept_id, [])

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