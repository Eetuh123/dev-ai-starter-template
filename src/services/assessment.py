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
MAX_TOPICS = 12  # never assess more topics than this

# Per topic: ask at least 5 questions. A topic is "known" when at least 80% of the answers are right.
# After 5 answers it stops if the result is clear (4/5 or 5/5 = known). While 80% can still be
# reached it asks more, up to 10 questions. When 80% can no longer be reached it is "missing".
PASS_PERCENT = 80
MIN_QUESTIONS = 5
MAX_QUESTIONS = 10

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
 
def build_tree(
    goal_id: str,
    max_depth: int = MAX_DEPTH,
    max_topics: int = MAX_TOPICS,
) -> dict | None:
    """
    The goal and its prerequisites as a tree: {"id": ..., "children": [...]}.

    Same topics as get_assessment_concepts. A topic that several paths lead to appears once,
    under the first parent that reaches it. None if the goal is not in the map.
    """
    prerequisites = {c["id"]: c["prerequisites"] for c in load_concepts()}
    if goal_id not in prerequisites:
        return None

    root = {"id": goal_id, "children": []}
    nodes = {goal_id: root}
    seen = {goal_id}
    level = [goal_id]
    count = 0

    for _ in range(max_depth):
        next_level = []
        for concept_id in level:
            for prereq_id in prerequisites[concept_id]:
                if prereq_id in seen or prereq_id not in prerequisites:
                    continue
                seen.add(prereq_id)
                count += 1
                node = {"id": prereq_id, "children": []}
                nodes[concept_id]["children"].append(node)
                nodes[prereq_id] = node
                if count >= max_topics:
                    return root
                next_level.append(prereq_id)
        level = next_level

    return root


def _spaced(items: list, count: int) -> list:
    """`count` items spread evenly over the list (first and last included)."""
    if count >= len(items):
        return list(items)
    if count == 1:
        return [items[len(items) // 2]]
    last = len(items) - 1
    return [items[round(i * last / (count - 1))] for i in range(count)]


def pick_assessment_questions(
    questions: list[QuizQuestion],
    count: int = MAX_QUESTIONS,
) -> list[QuizQuestion]:
    """
    Choose and order the questions the assessment can ask.

    The first MIN_QUESTIONS are spread over the whole difficulty range, because they usually
    decide the topic. The rest are only asked while the result is still open.
    """
    ordered = sorted(questions, key=lambda q: q.difficulty)
    chosen = _spaced(ordered, count)

    first = _spaced(chosen, min(MIN_QUESTIONS, len(chosen)))
    first_ids = {id(q) for q in first}
    rest = [q for q in chosen if id(q) not in first_ids]
    return first + rest


def get_questions(concept_id: str) -> list[QuizQuestion]:
    """The assessment questions for one topic (the first 5 usually decide it)."""
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

    available is how many questions the topic has (some topics have fewer than 10).
    Returns "known" (at least 80% right), "missing" (80% can no longer be reached),
    or "untested" when more answers are needed.
    """
    limit = min(MAX_QUESTIONS, available)
    answers = scores[-MAX_QUESTIONS:]
    count = len(answers)
    right = sum(answers)

    if count == 0 or limit == 0:
        return "untested"

    # Too few answers to decide, unless the topic has fewer questions than the minimum.
    if count < min(MIN_QUESTIONS, limit):
        return "untested"

    # Enough answers and already at 80%: no need to ask more.
    if right * 100 >= PASS_PERCENT * count:
        return "known"

    # Even if every remaining question is right, the final result stays under 80%.
    best_possible = right + max(limit - count, 0)
    if best_possible * 100 < PASS_PERCENT * limit:
        return "missing"

    # Everything was answered and it is under 80%.
    if count >= limit:
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