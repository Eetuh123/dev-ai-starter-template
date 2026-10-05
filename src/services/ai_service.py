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
from src.services.assessment import next_question, find_gaps
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


def _concepts_by_id() -> dict[str, Concept]:
    return {c.id: c for c in load_concept_map()}


def start_assessment(goal_id: str | None) -> AssessmentStep:
    """Load saved progress and return the first assessment question."""
    if not goal_id:
        return AssessmentStep(message="Pick a goal first.")

    progress = load_progress()
    question = next_question(goal_id, progress)
    message = "" if question else "Nothing to assess, you already know the prerequisites."
    return AssessmentStep(progress=progress, question=question, message=message)


def submit_answer(
    goal_id: str,
    progress: dict[str, ConceptProgress],
    question: QuizQuestion | None,
    answer_text: str,
) -> AssessmentStep:
    """Check an answer, update and save progress, return the next question."""
    if question is None:
        return AssessmentStep(progress=progress, message="No active question. Start the assessment first.")

    if not answer_text or not answer_text.strip():
        return AssessmentStep(progress=progress, question=question, message="Please type an answer first.")

    correct = check_answer(question, answer_text.strip())

    # Placeholder rule: one answer decides the status. Real logic belongs in assessment.py.
    entry = progress.get(question.concept_id) or ConceptProgress(concept_id=question.concept_id)
    entry.quiz_scores.append(correct)
    entry.status = "known" if correct else "missing"
    progress[question.concept_id] = entry
    save_progress(progress)

    message = "Correct!" if correct else f"Not quite. Expected: `{question.answer}`"
    return AssessmentStep(progress=progress, question=next_question(goal_id, progress), message=message)


def get_study_material(goal_id: str, progress: dict[str, ConceptProgress]) -> StudyMaterial:
    """For each missing concept: retrieve -> lesson -> verify -> quiz."""
    try:
        concepts = _concepts_by_id()
        items: list[StudyItem] = []

        for concept_id in find_gaps(goal_id, progress):
            concept = concepts.get(concept_id)
            if concept is None:
                continue

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