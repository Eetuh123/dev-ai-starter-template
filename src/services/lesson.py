from src.schemas.study import Concept, Lesson, RagChunk

def generate_lesson(concept: Concept, chunks: list[RagChunk]) -> Lesson:
    return Lesson(concept_id=concept.id, content=f"# {concept.name}\n\nFake lesson.",
                  source_chunk_ids=[c.id for c in chunks])