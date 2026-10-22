import pytest

from src.schemas.study import QuizQuestion
from src.services.assessment import pick_assessment_questions, topic_status


@pytest.mark.parametrize(
    "scores, available, expected",
    [
        ([], 10, "untested"),
        ([True] * 4, 10, "untested"),  # fewer than 5 answers: never decided
        ([True] * 5, 10, "known"),
        ([True, True, True, True, False], 10, "known"),  # 4/5 = 80%
        ([True, True, True, False, False], 10, "untested"),  # 3/5, 80% still reachable
        ([True, True, False, False, False], 10, "missing"),  # best case 7/10
        ([True, True, True, False, False, True, True, True, True], 10, "untested"),  # 7/9
        ([True, True, True, False, False, True, True, True, True, True], 10, "known"),  # 8/10
        ([True, True, True, False, False, True, True, True, True, False], 10, "missing"),  # 7/10
        ([False] * 3, 3, "missing"),  # topic with only 3 questions
        ([True] * 3, 3, "known"),
        ([True, True, False], 3, "missing"),  # 3 questions: all must be right
        ([True, True, True, True, False], 5, "known"),
        ([True, True, True, False, False], 5, "missing"),  # 5 questions: 4/5 needed
        ([False] * 5 + [True] * 10, 10, "known"),  # only the latest 10 answers count
    ],
)
def test_topic_status(scores, available, expected):
    assert topic_status(scores, available) == expected


def _question(number: int, difficulty: int) -> QuizQuestion:
    return QuizQuestion(
        id=f"q{number}", concept_id="c", question="?", answer="1", difficulty=difficulty
    )


@pytest.mark.parametrize("size", [0, 1, 4, 5, 6, 10, 14])
def test_pick_assessment_questions(size):
    questions = [_question(i, 1 + (i * 3) // max(size, 1)) for i in range(size)]
    picked = pick_assessment_questions(questions)

    assert len(picked) == min(size, 10)
    assert len({q.id for q in picked}) == len(picked)
