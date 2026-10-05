from src.schemas.study import Concept, QuizQuestion, RagChunk

def generate_quiz(concept: Concept, chunks: list[RagChunk]) -> list[QuizQuestion]:
    return [
        QuizQuestion(
            id="fake-q1",
            concept_id=concept.id,
            question="Differentiate sin(x^2)",
            answer="2*x*cos(x**2)",
            difficulty=2,
        )
    ]
    
def check_answer(question: QuizQuestion, text: str) -> bool:
    return text.replace(" ", "") == question.answer