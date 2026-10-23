import re
from typing import Callable

from src.models.model_client import OllamaModelClient
from src.schemas.study import Concept, Lesson, RagChunk
from src.services.math_check import check_steps

NO_SOURCE_TEXT = (
    "No source material was found for this topic, so no lesson was generated."
)
EMPTY_ANSWER_TEXT = "The model returned an empty answer. Please try again."
NO_EXAMPLE_TEXT = "*No worked example was found in the sources for this topic.*"
REMOVED_EXAMPLE_TEXT = "*A worked example was left out because its calculation did not check out.*"

# The lesson is written in small parts. Each part has its own search, its own sources and one job,
# which keeps a small local model from mixing things up.
RULES = (
    "- Use ONLY the source material below. Do not add facts, formulas or examples that are not in it.\n"
    "- Stay strictly on the topic. Ignore anything in the sources that belongs to another topic.\n"
    "- Do not use stories or everyday analogies.\n"
    "- Write math in LaTeX, for example $f(x) = x^2$.\n"
    "- Use Markdown. Do not write a title or heading and do not greet the student.\n"
)

EXPLAIN_TASK = (
    "Explain the key definitions and rules of this topic in simple English, in at most 120 words. "
    "Do not give worked examples here."
)
EXAMPLE_TASK = (
    "Present ONE worked example about this topic that appears in the sources. Write the problem first, "
    "then every solving step on its own line with all numbers shown, then the final answer. "
    "Do not invent an example and do not change its numbers. "
    "If the sources contain no worked example for this topic, answer with exactly: NONE"
)
MISTAKES_TASK = (
    "List up to 3 common mistakes students make with this topic, only ones that the sources mention "
    "or warn about. Use a bullet list with one short line each. "
    "If the sources mention none, answer with exactly: NONE"
)


STEPS_TASK = (
    "Below is a worked example from a math lesson. Rewrite its calculation as equations with numbers only, "
    "one equation per line, in the order of the steps, for example: 5^2 - 4*1*6 = 1. "
    "Use only digits, + - * / ^ ( ) = and sqrt( ). Write every multiplication with *. "
    "Include only the steps where both sides are numbers only (no letters like x or y). "
    "Copy the numbers EXACTLY as they are written in the example. Do not correct, recalculate or fix "
    "anything, even if a step looks wrong. Output only the equations, nothing else. "
    "If there are no such steps, output exactly: NONE\n\n"
)


def _format_sources(chunks: list[RagChunk]) -> str:
    return "\n\n".join(
        f"[Source {number}] {chunk.book}, {chunk.section}\n{chunk.text}"
        for number, chunk in enumerate(chunks, start=1)
    )


def _build_prompt(concept: Concept, chunks: list[RagChunk], task: str) -> str:
    return (
        "You are a math tutor writing one part of a study lesson for a student.\n"
        f"Topic: {concept.name}\n\n"
        f"Your task: {task}\n\n"
        f"Rules:\n{RULES}\n"
        f"Source material:\n\n{_format_sources(chunks)}\n"
    )


def _fix_braces(text: str) -> str:
    """
    Make set braces in math safe for the page.

    Markdown treats a backslash before a brace as an escape and removes it, which breaks
    \\left\\{ ... \\right\\} in the formulas. \\lbrace and \\rbrace have no such problem.
    """
    text = text.replace("\\left\\{", "\\left\\lbrace ").replace("\\right\\}", "\\right\\rbrace ")
    # The same braces after the backslash was already lost.
    text = text.replace("\\left{", "\\left\\lbrace ").replace("\\right}", "\\right\\rbrace ")
    return text.replace("\\{", "\\lbrace ").replace("\\}", "\\rbrace ")


def _fix_dashes(text: str) -> str:
    """The book conversion turns a minus sign into '--' and a dash into '---'. Undo that."""
    text = re.sub(r"(?<![-\w])--(?=\d)", "−", text)
    return re.sub(r"(?<=\w)---(?=\w)", " – ", text)


def _tidy(answer: str) -> str:
    """Clean the model's answer: no thinking block, no heading (the page shows the topic name)."""
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL)
    answer = re.sub(r"\A\s*#{1,6}[^\n]*\n+", "", answer.strip())
    answer = re.sub(r"\s*\[Reference:[^\]]*\]", "", answer)   # links to figures and examples of the book
    answer = re.sub(r"\n\s*NONE\W*\Z", "", answer)   # the answer followed by a stray NONE line
    return _fix_dashes(_fix_braces(answer)).strip()


NONE_PHRASES = (
    "does not mention", "do not mention", "not mention", "no common mistakes", "no worked example",
    "not explicitly", "does not contain", "do not contain", "no example",
)


# A model that thinks out loud in its answer ("Wait, let me re-read the sources") has no usable answer.
REASONING_MARKERS = ("wait,", "let me ", "let's ", "re-read", "re-evaluat", "looking closely", "the prompt")


def _is_none(text: str) -> bool:
    """True when the model says there is nothing (it does not always answer with exactly NONE)."""
    if not text:
        return True
    if any(marker in text.lower() for marker in REASONING_MARKERS):
        return True
    if re.fullmatch(r"\W*none\W*", text, flags=re.IGNORECASE):
        return True
    lowered = text.lower()
    return len(text) < 400 and (
        re.match(r"\W*none\b", lowered) or any(phrase in lowered for phrase in NONE_PHRASES)
    )


def _has_steps(example: str) -> bool:
    """A worked example must show at least one solving step (an equation), not only a problem."""
    return "=" in example


def _math_ok(model, example: str) -> bool | None:
    """Ask the model to copy the example's number lines, then let SymPy check that they agree."""
    reply = _tidy(model.generate(STEPS_TASK + "Worked example:\n" + example))
    if _is_none(reply):
        return None
    return check_steps(reply.splitlines())


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
    retriever: Callable[..., list[RagChunk]] | None = None,
) -> Lesson:
    """
    Write a lesson in parts: explanation, one worked example, common mistakes.

    `chunks` are the general sources for the explanation. With a `retriever`, the example and the
    mistakes get their own search (retriever(concept_id, top_k=..., query=...)).
    """
    # No sources: do not let the small model invent math from memory.
    if not chunks:
        return Lesson(concept_id=concept.id, content=NO_SOURCE_TEXT, source_chunk_ids=[])

    model = client or OllamaModelClient()
    used = list(chunks)

    explanation = _tidy(model.generate(_build_prompt(concept, chunks, EXPLAIN_TASK)))
    if not explanation:
        return Lesson(concept_id=concept.id, content=EMPTY_ANSWER_TEXT, source_chunk_ids=[])

    def part(task: str, query: str, top_k: int) -> str:
        part_chunks = retriever(concept.id, top_k=top_k, query=query) if retriever else chunks
        if not part_chunks:
            return ""
        text = _tidy(model.generate(_build_prompt(concept, part_chunks, task)))
        if not _is_none(text):
            used.extend(part_chunks)   # only the sources that were really used are listed
        return text

    example_query = f"Example using {concept.name}: a problem and its solution"
    example = part(EXAMPLE_TASK, example_query, 4)
    if not _is_none(example) and not _has_steps(example):
        example = part(EXAMPLE_TASK, example_query, 4)   # no steps in it, try once more
        if not _is_none(example) and not _has_steps(example):
            example = ""
    removed = False
    if not _is_none(example) and _math_ok(model, example) is False:
        # A step of the example is wrong. Try once more, and drop it if it is still wrong.
        example = part(EXAMPLE_TASK, example_query, 4)
        if not _is_none(example) and _math_ok(model, example) is False:
            example, removed = "", True
    mistakes = part(MISTAKES_TASK, "common mistakes and errors to avoid", 2)

    sections = [explanation, "### Worked example\n\n" + (
        (REMOVED_EXAMPLE_TEXT if removed else NO_EXAMPLE_TEXT) if _is_none(example) else example)]
    if not _is_none(mistakes):
        sections.append("### Common mistakes\n\n" + mistakes)

    unique = list({chunk.id: chunk for chunk in used}.values())
    content = "\n\n".join(sections) + f"\n\n---\n ### Sources\n{_source_list(unique)}\n"
    return Lesson(
        concept_id=concept.id,
        content=content,
        source_chunk_ids=[chunk.id for chunk in unique],
    )
