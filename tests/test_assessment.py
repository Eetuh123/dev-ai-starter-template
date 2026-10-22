import pytest

from src.schemas.study import QuizQuestion
from src.services.assessment import pick_assessment_questions, topic_status


@pytest.mark.parametrize(
    "scores, available, expected",
    [
        ([], 3, "untested"),
        ([True], 3, "untested"),
        ([True, True], 3, "known"),
        ([False, False], 3, "missing"),
        ([True, False], 3, "untested"),  # mixed: one more question
        ([True, False, True], 3, "known"),
        ([True, False, False], 3, "missing"),
        ([True], 1, "known"),  # topic has only one question
        ([True, False], 2, "missing"),  # only two questions and mixed: be careful
        ([False, False, False, True, True], 3, "known"),  # only the latest round counts
    ],
)
def test_topic_status(scores, available, expected):
    assert topic_status(scores, available) == expected


def _question(number: int, difficulty: int) -> QuizQuestion:
    return QuizQuestion(
        id=f"q{number}", concept_id="c", question="?", answer="1", difficulty=difficulty
    )


@pytest.mark.parametrize("size", [0, 1, 2, 3, 4, 7, 10])
def test_pick_assessment_questions(size):
    questions = [_question(i, 1 + (i * 3) // max(size, 1)) for i in range(size)]
    picked = pick_assessment_questions(questions)

    assert len(picked) == min(size, 3)
    assert len({q.id for q in picked}) == len(picked)
