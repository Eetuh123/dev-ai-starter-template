import json
from pathlib import Path
from src.capabilities.rag import retrieve
from src.services.quiz import generate_quiz
from src.schemas.study import Concept, ConceptProgress, QuizQuestion

CONCEPTS_FILE = Path("data/concepts.json")
GENERATED_QS: dict[str, list[QuizQuestion]] = {}

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
    if concept_id in GENERATED_QS:
        return GENERATED_QS[concept_id]

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