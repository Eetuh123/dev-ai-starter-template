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
MAX_TOPICS = 8   # never assess more topics than this

# Per topic: ask 2 questions. Both right = known, both wrong = missing.
# A split result is unclear, so a third question breaks the tie.
# 8 topics * 2..3 questions = 16..24 questions in total.
MIN_QUESTIONS = 2
MAX_QUESTIONS = 3

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
 
def pick_assessment_questions(
    questions: list[QuizQuestion],
    count: int = MAX_QUESTIONS,
) -> list[QuizQuestion]:
    """
    Choose the few questions the assessment asks, from the full list sorted by difficulty.

    The first two (one easier, one harder) decide the topic.
    The third is the tie-breaker, taken from the middle.
    """
    if len(questions) <= count:
        return list(questions)

    ordered = sorted(questions, key=lambda q: q.difficulty)
    size = len(ordered)
    # With more than 3 questions these three positions are always different.
    positions = [size // 4, (size * 3) // 4, size // 2]
    return [ordered[i] for i in positions[:count]]


def get_questions(concept_id: str) -> list[QuizQuestion]:
    """The assessment questions for one topic (2 decide it, the 3rd breaks a tie)."""
    if concept_id not in GENERATED_QS:
        concepts = load_concepts()

        concept_data = next(
            (item for item in concepts if item["id"] == concept_id),
            None,
        )

        if concept_data is None:
            return []

        concept = Concept.model_validate(concept_data)
        chunks = retrieve(concept_id)
        GENERATED_QS[concept_id] = generate_quiz(concept, chunks)

    return pick_assessment_questions(GENERATED_QS[concept_id])


def topic_status(scores: list[bool], available: int = MAX_QUESTIONS) -> str:
    """
    Decide a topic from the answers of one assessment round.

    available is how many questions the topic has (some topics have fewer than 3).
    Returns "known", "missing", or "untested" when more answers are needed.
    """
    limit = min(MAX_QUESTIONS, available)
    answers = scores[-MAX_QUESTIONS:]
    right = sum(answers)
    count = len(answers)

    if count == 0 or limit == 0:
        return "untested"

    # Everything the topic has was answered: majority decides.
    if count >= limit:
        return "known" if right * 2 > count else "missing"

    # Two answers, more questions left: only a clear result stops early.
    if count >= MIN_QUESTIONS:
        if right == count:
            return "known"
        if right == 0:
            return "missing"
    return "untested"


def start_topic(progress: dict[str, ConceptProgress], concept_id: str) -> None:
    """Begin a new assessment round for a topic. Old answers are cleared, the old status stays."""
    entry = progress.get(concept_id)
    if entry is not None:
        entry.quiz_scores = []

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