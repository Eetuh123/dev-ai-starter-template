import json
from pathlib import Path
from src.schemas.study import ConceptProgress, QuizQuestion

CONCEPTS_FILE = Path("data/concepts.json")

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

MAX_DEPTH = 3   # how many levels below the goal we walk
MAX_TOPICS = 8  # never assess more topics than this

def get_assessment_concepts(
    goal_id: str,
    max_depth: int = MAX_DEPTH,
    max_topics: int = MAX_TOPICS,
) -> list[str]:
    """
    Collect the prerequisites of a goal, nearest first.
 
    Walks the concept map level by level (breadth first) from the goal downwards.
    Every topic appears only once even if several paths lead to it, and the walk
    stops at max_depth levels or max_topics topics, whichever comes first.
    """
    prerequisites = {c["id"]: c["prerequisites"] for c in load_concepts()}
 
    if goal_id not in prerequisites:
        return []
 
    found = []
    seen = {goal_id}  # also protects against cycles in the map
    current_level = [goal_id]
 
    for _ in range(max_depth):
        next_level = []
        for concept_id in current_level:
            for prereq_id in prerequisites[concept_id]:
                if prereq_id in seen or prereq_id not in prerequisites:
                    continue
                seen.add(prereq_id)
                found.append(prereq_id)
                if len(found) >= max_topics:
                    return found
                next_level.append(prereq_id)
        current_level = next_level
 
    return found
 
def get_questions(concept_id: str) -> list[QuizQuestion]:
    return DEMO_QUESTIONS.get(concept_id, [])

def get_questions(concept_id: str) -> list[QuizQuestion]:
    return DEMO_QUESTIONS.get(concept_id, [])

def find_gaps(goal_id: str, progress: dict[str, ConceptProgress]) -> list[str]:
    prerequisites = get_assessment_concepts(goal_id)
    gaps = []
    for concept_id in prerequisites:
        entry = progress.get(concept_id)
        if entry is None or entry.status != "known":
            gaps.append(concept_id)
    return gaps

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