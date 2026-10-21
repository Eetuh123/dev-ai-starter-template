from src.models.model_client import OllamaModelClient
from src.schemas.study import Concept, Lesson, RagChunk

NO_SOURCE_TEXT = (
    "No source material was found for this topic, so no lesson was generated."
)
EMPTY_ANSWER_TEXT = "The model returned an empty answer. Please try again."


def _build_prompt(concept: Concept, chunks: list[RagChunk]) -> str:
    sources = "\n\n".join(
        f"[Source {number}] {chunk.book}, {chunk.section}\n{chunk.text}"
        for number, chunk in enumerate(chunks, start=1)
    )

    return (
        "You are a math tutor writing a short study lesson for a student.\n"
        f"Topic: {concept.name}\n\n"
        "Rules:\n"
        "- Use ONLY the source material below.\n"
        "- Do not add facts, formulas or examples that are not in the sources.\n"
        "- If the sources do not cover something, leave it out. Do not guess.\n"
        "- Explain step by step in simple English.\n"
        "- Include a worked example if the sources contain one.\n"
        "- Write math in LaTeX, for example $f(x) = x^2$.\n"
        "- Use Markdown. Keep the lesson under about 300 words.\n\n"
        f"Source material:\n\n{sources}\n"
    )


def _source_list(chunks: list[RagChunk]) -> str:
    seen = []
    for chunk in chunks:
        line = f"- {chunk.book}, {chunk.section}"
        if line not in seen:
            seen.append(line)
    return "\n".join(seen)


def generate_lesson(
    concept: Concept,
    chunks: list[RagChunk],
    client: OllamaModelClient | None = None,
) -> Lesson:
    # No sources: do not let the small model invent math from memory.
    if not chunks:
        return Lesson(
            concept_id=concept.id,
            content=f"# {concept.name}\n\n{NO_SOURCE_TEXT}",
            source_chunk_ids=[],
        )

    model = client or OllamaModelClient()
    answer = model.generate(_build_prompt(concept, chunks)).strip()

    if not answer:
        return Lesson(
            concept_id=concept.id,
            content=f"# {concept.name}\n\n{EMPTY_ANSWER_TEXT}",
            source_chunk_ids=[],
        )

    content = f"# {concept.name}\n\n{answer}\n\n---\n**Sources:**\n{_source_list(chunks)}"
    return Lesson(
        concept_id=concept.id,
        content=content,
        source_chunk_ids=[chunk.id for chunk in chunks],
    )