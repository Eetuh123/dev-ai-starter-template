import copy
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from src.models.model_client import (
    OllamaModelClient,
    ModelClientError,
    OllamaConnectionError,
    ModelNotFoundError,
)
from src.schemas.responses import UserRequest, AIResponse
from src.schemas.study import Concept, ConceptProgress, Lesson, QuizQuestion

from src.capabilities.rag import load_concept_map, retrieve
from src.capabilities.memory import load_progress, save_progress
from src.capabilities.verifier import verify
from src.services.assessment import (
    get_assessment_concepts as assessment_get_concepts,
    build_tree as assessment_build_tree,
    get_questions as assessment_get_questions,
    find_gaps,
    topic_status,
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    PASS_PERCENT,
    pick_assessment_questions,
    start_topic as assessment_start_topic
)
from src.services.lesson import generate_lesson
from src.services.quiz import generate_quiz, check_answer

# ---------------------------------------------------------------------------
# Result types returned to the UI
# ---------------------------------------------------------------------------

class AssessmentStep(BaseModel):
    """One step of the assessment: updated progress + next question (None = done)."""
    progress: dict[str, ConceptProgress] = {}
    question: QuizQuestion | None = None
    message: str = ""
    # "known" (80% right) / "missing" once decided, "untested" while more answers are needed.
    topic_status: str = "untested"


class StudyItem(BaseModel):
    """Material for one missing concept."""
    concept: Concept
    lesson: Lesson
    quiz: list[QuizQuestion] = []
    verifier_issues: list[str] = []


class StudyMaterial(BaseModel):
    items: list[StudyItem] = []
    error: str | None = None

# ---------------------------------------------------------------------------
# Study flow (called by the UI)
# ---------------------------------------------------------------------------

def list_goals() -> list[Concept]:
    """All concepts the user can pick as a goal. Empty list if the map can't be loaded."""
    try:
        return load_concept_map()
    except (OSError, ValueError):
        # OSError: file missing. ValueError: bad JSON or Pydantic validation error.
        return []

def get_progress() -> dict[str, ConceptProgress]:
    """Saved progress from disk, so the UI can continue where the user left off."""
    return load_progress()

def _concepts_by_id() -> dict[str, Concept]:
    return {c.id: c for c in load_concept_map()}

def start_assessment(goal_id: str | None) -> AssessmentStep:
    """Load saved progress and return the first assessment question."""
    if not goal_id:
        return AssessmentStep(message="Pick a goal first.")

    progress = load_progress()
    concepts = get_assessment_concepts(goal_id)
    if not concepts:
        return AssessmentStep(progress=progress,
                              message="No prerequisite assessments for this goal.")

    first_concept = concepts[0]
    questions = get_questions(first_concept)
    if not questions:
        return AssessmentStep(progress=progress,
                              message="No questions available.")

    return AssessmentStep(progress=progress, question=questions[0], 
                          message="")

def get_assessment_concepts(goal_id: str):
    return assessment_get_concepts(goal_id)

def get_tree(goal_id: str) -> dict | None:
    """The goal and its prerequisites as a nested tree of topic ids."""
    return assessment_build_tree(goal_id)

def get_questions(concept_id: str) -> list[QuizQuestion]:
    return assessment_get_questions(concept_id)

def start_topic(
    progress: dict[str, ConceptProgress], concept_id: str
) -> dict[str, ConceptProgress]:
    """A new assessment round for one topic: clear its old answers and save."""
    assessment_start_topic(progress, concept_id)
    save_progress(progress)
    return progress

def get_assessment_questions(goal_id: str) -> list[QuizQuestion]:
    questions = []
    for concept_id in get_assessment_concepts(goal_id):
        questions.extend(get_questions(concept_id))
    return questions

def submit_answer(
    goal_id: str,
    progress: dict[str, ConceptProgress],
    question: QuizQuestion | None,
    answer_text: str,
) -> AssessmentStep:
    """Check an answer and save the result."""
    if question is None:
        return AssessmentStep(progress=progress,
            message="No active question. Start the assessment first.")

    if not answer_text or not answer_text.strip():
        return AssessmentStep(progress=progress, question=question,
                              message="Please type an answer first.")

    correct = check_answer(question, answer_text.strip())

    entry = progress.get(question.concept_id) or ConceptProgress(
        concept_id=question.concept_id)
    entry.quiz_scores.append(correct)

    # Known at 80% right. Stops early when clear, asks more questions while it is open.
    available = len(get_questions(question.concept_id))
    status = topic_status(entry.quiz_scores, available)
    if status != "untested":
        entry.status = status

    progress[question.concept_id] = entry
    save_progress(progress)

    message = (
        "Correct!"
        if correct
        else f"Not quite. Expected: `{question.answer}`")

    answers = entry.quiz_scores[-MAX_QUESTIONS:]
    score = f"{sum(answers)}/{len(answers)}"
    if status == "untested":
        if len(answers) >= MIN_QUESTIONS:
            message += f"\n\n{score} right so far, 80% is needed, so there is one more question."
    else:
        message += f"\n\n**Topic result: {status}** ({score} right)."

    return AssessmentStep(progress=progress, question=None,
                          message=message, topic_status=status)

QUIZ_QUESTIONS = 5   # questions in one quiz attempt; passing needs PASS_PERCENT right

class TopicMaterial(BaseModel):
    """Everything the topic window shows: lesson + practice (the quiz is drawn separately)."""
    concept: Concept
    lesson: Lesson
    practice: list[QuizQuestion] = []
    verifier_issues: list[str] = []
    error: str | None = None


class QuizResult(BaseModel):
    progress: dict[str, ConceptProgress] = {}
    right: int = 0
    total: int = 0
    passed: bool = False
    feedback: list[str] = []


_TOPIC_CACHE: dict[str, TopicMaterial] = {}   # a lesson takes a while to write, so keep it
_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "lesson_cache"   # survives restarts

def _cache_file(concept_id: str) -> Path:
    return _CACHE_DIR / (re.sub(r"[^A-Za-z0-9_.-]", "_", concept_id) + ".json")

def _cached_material(concept_id: str) -> Optional[TopicMaterial]:
    """Memory first, then disk. Delete data/lesson_cache to force new lessons."""
    if concept_id in _TOPIC_CACHE:
        return _TOPIC_CACHE[concept_id]
    try:
        material = TopicMaterial.model_validate_json(_cache_file(concept_id).read_text(encoding="utf-8"))
    except Exception:
        return None
    _TOPIC_CACHE[concept_id] = material
    return material

def _save_material(concept_id: str, material: TopicMaterial) -> None:
    _TOPIC_CACHE[concept_id] = material
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_file(concept_id).write_text(material.model_dump_json(), encoding="utf-8")
    except Exception:
        pass   # disk cache is best effort

def _error_text(err: Exception) -> str:
    if isinstance(err, OllamaConnectionError):
        return "Could not connect to Ollama. Check that it is running."
    if isinstance(err, ModelNotFoundError):
        return "The configured model is not installed in Ollama."
    if isinstance(err, ModelClientError):
        return "Something went wrong talking to the AI model."
    return f"Unexpected error: {err}"


def get_gaps(goal_id: str, progress: dict[str, ConceptProgress]) -> list[Concept]:
    """The topics of this goal that are not known yet."""
    concepts = _concepts_by_id()
    return [concepts[cid] for cid in find_gaps(goal_id, progress) if cid in concepts]


def _fresh_questions(concept_id: str, count: int, avoid: set[str]) -> list[QuizQuestion]:
    """New questions for a topic (new random numbers each time), avoiding the given texts."""
    concept = _concepts_by_id().get(concept_id)
    if concept is None:
        return []
    questions = generate_quiz(concept)
    fresh = [q for q in questions if q.question not in avoid]
    pool = fresh if len(fresh) >= min(count, len(questions)) else questions
    return pick_assessment_questions(pool, count)


def get_topic_material(concept_id: str) -> TopicMaterial:
    """Lesson (retrieve -> write -> verify) and practice questions for one topic."""
    cached = _cached_material(concept_id)
    if cached:
        return cached

    concept = _concepts_by_id().get(concept_id)
    if concept is None:
        concept = Concept(id=concept_id, name=concept_id, description="")
        return TopicMaterial(concept=concept, lesson=Lesson(concept_id=concept_id, content=""),
                             error="Unknown topic.")
    try:
        chunks = retrieve(concept_id, top_k=5)
        lesson = generate_lesson(concept, chunks, retriever=retrieve)

        # Dont automatically verify
        lesson.verified = False
        issues = []
        '''
        # Verifier down -> still show the lesson, marked unverified.     
        try:
            result = verify(lesson.content, chunks)
            lesson.verified = result.passed
            issues = result.issues
        except Exception:
            lesson.verified = False
            issues = ["Verifier unavailable, this material is unverified."]
        '''
        practice = _fresh_questions(concept_id, QUIZ_QUESTIONS, set())
    except Exception as err:
        return TopicMaterial(concept=concept, lesson=Lesson(concept_id=concept_id, content=""),
                             error=_error_text(err))

    material = TopicMaterial(concept=concept, lesson=lesson, practice=practice, verifier_issues=issues)
    _save_material(concept_id, material)
    return material

def regenerate_topic_material(concept_id: str) -> TopicMaterial:
    """Throw away the saved lesson of a topic and write a new one."""
    _TOPIC_CACHE.pop(concept_id, None)
    try:
        _cache_file(concept_id).unlink()
    except OSError:
        pass   # nothing saved on disk, or it cannot be removed
    return get_topic_material(concept_id)


def verify_topic_material(concept_id: str) -> TopicMaterial:
    # Verify the existing lesson only when the user requests it
    material = get_topic_material(concept_id)

    if material.error: return material

    try:
        chunks = retrieve(concept_id, top_k=5)
        result = verify(material.lesson.content, chunks)

        # Dont fix lessons
        material.lesson.verified = result.passed
        material.verifier_issues = (
            [] if result.passed else result.issues
        )

    except Exception as error:
        material.lesson.verified = False
        material.verifier_issues = [
            f"Verification failed ({type(error).__name__})."
        ]

    _save_material(concept_id, material)
    return material


def new_quiz(concept_id: str, avoid: list[str] | None = None) -> list[QuizQuestion]:
    """A fresh quiz. Never reuses the practice questions or the ones in `avoid` if it can help it."""
    cached = _cached_material(concept_id)
    skip = set(avoid or [])
    if cached:
        skip |= {q.question for q in cached.practice}
    return _fresh_questions(concept_id, QUIZ_QUESTIONS, skip)


def grade_quiz(
    progress: dict[str, ConceptProgress],
    concept_id: str,
    questions: list[QuizQuestion],
    answers: list[str],
) -> QuizResult:
    """Check a whole quiz. Passing (80% right) marks the topic known; failing leaves it as it was."""
    if not questions:
        return QuizResult(progress=progress, feedback=["No quiz questions for this topic yet."])

    progress = copy.deepcopy(progress)   # a new object, so the page notices that the progress changed
    flags, feedback = [], []
    for number, (question, text) in enumerate(zip(questions, answers), start=1):
        text = (text or "").strip()
        ok = bool(text) and check_answer(question, text)
        flags.append(ok)
        feedback.append(f"{number}. ✅ Correct." if ok else f"{number}. ❌ Not quite. Expected: `{question.answer}`")

    right, total = sum(flags), len(questions)
    passed = right * 100 >= PASS_PERCENT * total
    if passed:
        entry = progress.get(concept_id) or ConceptProgress(concept_id=concept_id)
        entry.status = "known"
        progress[concept_id] = entry
        save_progress(progress)

    return QuizResult(progress=progress, right=right, total=total, passed=passed, feedback=feedback)


def get_study_material(goal_id: str, progress: dict[str, ConceptProgress]) -> StudyMaterial:
    """For each missing concept: retrieve -> lesson -> verify -> quiz."""
    try:
        concepts = _concepts_by_id()
        items: list[StudyItem] = []
        
        for concept_id in find_gaps(goal_id, progress):
            concept = concepts.get(concept_id)
            if concept is None: continue

            chunks = retrieve(concept_id)
            lesson = generate_lesson(concept, chunks)

            # Verifier down -> still show the lesson, marked unverified.
            try:
                result = verify(lesson.content, chunks)
                if result.corrected_content:
                    lesson.content = result.corrected_content
                lesson.verified = result.passed
                issues = result.issues
            except Exception:
                lesson.verified = False
                issues = ["Verifier unavailable, this material is unverified."]

            quiz = generate_quiz(concept, chunks)
            items.append(StudyItem(concept=concept, lesson=lesson, quiz=quiz, verifier_issues=issues))

        return StudyMaterial(items=items)

    except OllamaConnectionError:
        return StudyMaterial(error="Could not connect to Ollama. Check that it is running.")
    except ModelNotFoundError:
        return StudyMaterial(error="The configured model is not installed in Ollama.")
    except ModelClientError:
        return StudyMaterial(error="Something went wrong talking to the AI model.")
    except Exception as err:
        return StudyMaterial(error=f"Unexpected error: {err}")


# ---------------------------------------------------------------------------
# Original starter code (kept so the template tests still pass)
# ---------------------------------------------------------------------------

class AIService:
    """
    Application service layer responsible for validating user input,
    orchestrating model client requests, and catching exceptions gracefully.
    """

    def __init__(self, model_client: Optional[OllamaModelClient] = None):
        self.model_client = model_client

    def _get_client(self) -> OllamaModelClient:
        if self.model_client is None:
            self.model_client = OllamaModelClient()
        return self.model_client

    def process_message(self, user_message: str) -> AIResponse:
        if not user_message or not user_message.strip():
            return AIResponse(
                content="Please enter a message before sending.",
                success=False,
                error_message="User message was empty.",
            )

        try:
            request = UserRequest(message=user_message.strip())
            client = self._get_client()
            response_text = client.generate(request.message)
            return AIResponse(content=response_text, success=True)

        except OllamaConnectionError as err:
            return AIResponse(
                content=(
                    "[Error] Could not connect to Ollama.\n\n"
                    "Please verify that Ollama is installed and running locally on your machine."
                ),
                success=False,
                error_message=str(err),
            )

        except ModelNotFoundError as err:
            return AIResponse(
                content=(
                    "[Error] The configured AI model is unavailable in Ollama.\n\n"
                    "Please verify your MODEL_NAME setting or run 'ollama run <model_name>'."
                ),
                success=False,
                error_message=str(err),
            )

        except ModelClientError as err:
            return AIResponse(
                content="[Error] An unexpected communication error occurred with the AI model.",
                success=False,
                error_message=str(err),
            )

        except Exception as err:
            return AIResponse(
                content="[Error] An unexpected application error occurred.",
                success=False,
                error_message=str(err),
            )


def generate_response(user_message: str, service: Optional[AIService] = None) -> str:
    active_service = service or AIService()
    response = active_service.process_message(user_message)
    return response.content