import random
import re

import sympy as sp
from sympy import simplify
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

from src.schemas.study import Concept, QuizQuestion, RagChunk
from src.services.problem_templates import TEMPLATES, instantiate

TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

X = sp.Symbol("x")

NUM_QUESTIONS = 10   # questions per topic
MIN_QUESTIONS = 3   # fewer usable questions than this counts as a failure

TASKS = ("evaluate", "simplify", "expand", "factor", "solve", "differentiate", "limit")

def _simplest(expr):
    """The shortest of a few standard forms. sp.simplify alone often factors (4x^2 - 2x -> 2x(2x - 1))."""
    candidates = []
    forms = [sp.expand, sp.cancel, sp.factor]
    if expr.has(sp.sin, sp.cos, sp.tan):
        forms.append(sp.trigsimp)  # sp.simplify can run for ages on some inputs, so it is not used here
    for form in forms:
        try:
            candidates.append(form(expr))
        except Exception:
            pass
    return min(candidates, key=sp.count_ops)  # first of equally short ones, so expand wins ties


# For these tasks "typing the question back" is mathematically equal to the key,
# so the student's answer must also already be in the requested form.
FORM_TASKS = {"simplify": _simplest, "expand": sp.expand, "factor": sp.factor}
FORM_VERBS = {"simplify": "Simplify", "expand": "Expand", "factor": "Factor"}

# Only these words may appear in an expression (the text is later given to SymPy's parser).
ALLOWED_WORDS = {"x", "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "ln", "exp", "pi", "abs"}


def _parse(text: str, evaluate: bool = True):
    # Python's built-in abs() would evaluate immediately, SymPy's Abs keeps |-7| as written.
    text = re.sub(r"\babs\b", "Abs", text.strip())
    return parse_expr(text, transformations=TRANSFORMS, evaluate=evaluate)


def _check_text(text) -> None:
    """Reject anything that is not a plain math expression. Raises ValueError."""
    if not isinstance(text, str) or not text.strip() or len(text) > 80:
        raise ValueError("expression is missing or too long")
    if not re.fullmatch(r"[0-9A-Za-z\s+\-*/^().]+", text):
        raise ValueError(f"unsupported characters in '{text}'")
    for word in re.findall(r"[A-Za-z]+", text):
        if word not in ALLOWED_WORDS:
            raise ValueError(f"unsupported word '{word}' in '{text}'")


def _latex(obj) -> str:
    """LaTeX for display, cleaned up. Parsing without evaluation leaves artifacts such as
    '(-1) 9', '1 x' and '1 * 1/3', which are removed here."""
    try:
        text = sp.latex(obj, ln_notation=True)
    except TypeError:  # older SymPy
        text = sp.latex(obj)
    text = re.sub(r"\\left\(-1\\right\) (\d+(?:\.\d+)?)", r"-\1", text)
    text = re.sub(r"(?<![\w.^])1 \\cdot (?=\\frac)", "", text)
    text = re.sub(r"(?<![\w.^])1 (?=[A-Za-z\\])(?!\\cdot|\\right|\\to)", "", text)
    for short, full in (("asin", "arcsin"), ("acos", "arccos"), ("atan", "arctan")):
        text = text.replace(r"\operatorname{" + short + "}", "\\" + full)
    return text


def _numeric_latex(text: str):
    """LaTeX straight from a numbers-only expression, so '3/4*2/5' keeps its fractions and
    '8*10^(-3)' keeps its power. Returns None when the text has anything else in it."""
    if not re.fullmatch(r"[0-9\s+\-*/^().]+", text):
        return None
    if "^" in text and "/" in text:
        return None  # mixing powers and fractions: let SymPy lay it out
    s = text.replace(" ", "")
    s = re.sub(r"\(([^()]*)\)/(\d+)", r"\\frac{\1}{\2}", s)
    s = re.sub(r"(\d+)/\(([^()]*)\)", r"\\frac{\1}{\2}", s)
    s = re.sub(r"(\d+)/(\d+)", r"\\frac{\1}{\2}", s)
    s = re.sub(r"\^\(([^()]*)\)", r"^{\1}", s)
    s = re.sub(r"\^(\d+)", r"^{\1}", s)
    s = s.replace("*", r" \cdot ")
    s = re.sub(r"(?<=[\d}\)])([+\-])(?=[\d(\\])", r" \1 ", s)
    return s.replace("(", r"\left(").replace(")", r"\right)")


def _read_expression(text):
    """Parse a model-written expression.

    Returns (value, written): value is SymPy's simplified-as-it-parses form, used for
    calculating. written keeps the expression as the model wrote it, used for display.
    """
    _check_text(text)
    value = _parse(text)
    if not value.free_symbols <= {X}:
        raise ValueError(f"'{text}' may only use the variable x")
    try:
        written = _parse(text, evaluate=False)
    except Exception:
        written = value
    return value, written


def _key(value) -> str:
    """Answer key as text the student sees and SymPy can parse again, e.g. 'x^2 + 1'."""
    return sp.sstr(value).replace("**", "^")


def _build_question(item, concept: Concept, number: int, allowed: tuple, substitute: bool = False) -> QuizQuestion:
    """Turn one {task, expression} pair into a question. SymPy calculates the answer key.

    Raises ValueError (or any SymPy error) when the pair is unusable.
    """
    if not isinstance(item, dict):
        raise ValueError("question is not a JSON object")

    task = str(item.get("task", "")).strip().lower()
    if task not in TASKS:
        raise ValueError(f"unknown task '{task}'")
    if task not in allowed:
        raise ValueError(f"task '{task}' does not fit this topic, use only: {', '.join(allowed)}")

    text = item.get("expression")
    label = f"{task} {text}"

    if task == "solve":
        if not isinstance(text, str) or text.count("=") != 1:
            raise ValueError(f"'{label}' needs exactly one '='")
        (left, left_written), (right, right_written) = (
            _read_expression(side) for side in text.split("=")
        )
        equation = sp.Eq(left, right)
        if not isinstance(equation, sp.Eq) or X not in equation.free_symbols:
            raise ValueError(f"'{label}' is not an equation in x")
        solutions = [s for s in sp.solve(equation, X) if s.is_real and s.is_rational]
        if len(solutions) != 1:
            raise ValueError(f"'{label}' must have exactly one rational solution")
        answer = solutions[0]
        shown = f"Solve for $x$: ${_latex(sp.Eq(left_written, right_written, evaluate=False))}$"

    else:
        value, written = _read_expression(text)

        if task == "evaluate":
            at = item.get("at")
            if at is not None and not substitute:
                raise ValueError(f"'{label}': this topic uses numbers only, no x")
            if at is None:
                if value.free_symbols or written.is_Number:
                    raise ValueError(f"'{label}' must be numbers only (or give a number in \"at\" to put in for x)")
                answer = sp.simplify(value)
                shown = f"Evaluate ${_numeric_latex(text) or _latex(written)}$"
            else:
                at_text = str(at) if isinstance(at, (int, float)) else at
                _check_text(at_text)
                point = _parse(at_text)
                if point.free_symbols or not (point.is_number and point.is_finite):
                    raise ValueError(f"'{label}': 'at' must be a finite number")
                if X not in value.free_symbols:
                    raise ValueError(f"'{label}' has 'at' but no x")
                answer = sp.simplify(value.subs(X, point))
                shown = f"Evaluate ${_latex(written)}$ when $x = {_latex(point)}$"
            if not (answer.is_number and answer.is_finite):
                raise ValueError(f"'{label}' has no finite value")

        elif task in FORM_TASKS:
            if X not in written.free_symbols:
                raise ValueError(f"'{label}' does not contain x")
            answer = FORM_TASKS[task](value)
            if answer == value and sp.count_ops(written) <= sp.count_ops(value):
                raise ValueError(f"'{label}' is already in the requested form")
            if task == "simplify" and sp.count_ops(answer) >= sp.count_ops(written):
                raise ValueError(f"'{label}' does not get simpler")
            shown = f"{FORM_VERBS[task]} ${_latex(written)}$"

        elif task == "differentiate":
            if X not in value.free_symbols:
                raise ValueError(f"'{label}' does not contain x")
            order = item.get("order", 1)
            if order not in (1, 2, 3):
                order = 1
            at = item.get("at")
            if at is not None:
                at_text = str(at) if isinstance(at, (int, float)) else at
                _check_text(at_text)
                point = _parse(at_text)
                if point.free_symbols or not (point.is_number and point.is_finite):
                    raise ValueError(f"'{label}': 'at' must be a finite number")
                answer = sp.simplify(sp.diff(value, X).subs(X, point))
                if not (answer.is_number and answer.is_finite):
                    raise ValueError(f"'{label}' has no finite derivative at {at_text}")
                shown = f"Find $f'({_latex(point)})$ when $f(x) = {_latex(written)}$"
            else:
                answer = _simplest(sp.diff(value, X, order))
                if answer == 0:
                    raise ValueError(f"'{label}' has derivative 0")
                if order == 1:
                    shown = f"Differentiate ${_latex(written)}$ with respect to $x$"
                else:
                    name = "second" if order == 2 else "third"
                    shown = f"Find the {name} derivative of ${_latex(written)}$ with respect to $x$"

        else:  # limit
            at = item.get("at")
            at_text = str(at) if isinstance(at, (int, float)) else at
            _check_text(at_text)
            point = _parse(at_text)
            if point.free_symbols or not (point.is_number and point.is_finite):
                raise ValueError(f"'{label}': 'at' must be a finite number")
            side = item.get("side", "+-")
            if side not in ("+", "-", "+-"):
                side = "+-"
            answer = sp.limit(value, X, point, dir=side)
            if isinstance(answer, sp.Limit) or not (answer.is_number and answer.is_finite):
                raise ValueError(f"'{label}' at {at_text} has no finite limit")
            shown = f"Evaluate ${_latex(sp.Limit(written, X, point, dir=side))}$"

    key = _key(answer)
    if len(key) > 45:
        raise ValueError(f"'{label}': answer key '{key}' is too long to type")
    if simplify(_parse(key) - answer) != 0:
        raise ValueError(f"'{label}': answer key '{key}' does not parse back correctly")

    difficulty = item.get("difficulty")
    if difficulty not in (1, 2, 3):
        difficulty = 2

    return QuizQuestion(
        id=f"q{number}",
        concept_id=concept.id,
        question=item.get("text") or shown,  # templates may bring their own wording
        answer=key,
        difficulty=difficulty,
        task=task,
    )


def _from_templates(concept: Concept, needed: int, seen: set, start_number: int) -> list:
    """Questions from the AI-generated templates, new random numbers every time."""
    templates = TEMPLATES.get(concept.id)
    if not templates or needed <= 0:
        return []

    order = random.sample(templates, len(templates))  # a different template for each question
    made: list[QuizQuestion] = []
    for attempt in range(needed * 40):
        if len(made) >= needed:
            break
        try:
            item = instantiate(order[attempt % len(order)])
            question = _build_question(item, concept, start_number + len(made), TASKS, True)
        except Exception:
            continue  # unusable numbers (trivial, undefined, ...): draw again
        if question.question in seen:
            continue
        seen.add(question.question)
        made.append(question)
    return made


def generate_quiz(concept: Concept, chunks: list[RagChunk] | None = None) -> list[QuizQuestion]:
    """Practice questions for one topic, built from the AI-generated templates with new random
    numbers every time. SymPy computes every answer key, so no model is involved and no key
    can be wrong. Topics without templates get an empty list (the UI says no questions yet).
    `chunks` is unused, kept so the caller does not change."""
    questions = _from_templates(concept, NUM_QUESTIONS, set(), 1)
    if 0 < len(questions) < MIN_QUESTIONS:
        raise ValueError(f"only {len(questions)} usable questions for '{concept.id}'")
    questions.sort(key=lambda q: q.difficulty)
    return questions


# Symbols a student may type or paste from the rendered question.
SYMBOLS = str.maketrans({
    "\u2212": "-", "\u2013": "-", "\u2014": "-",   # minus sign, en dash, em dash
    "\u00d7": "*", "\u00b7": "*", "\u22c5": "*",   # times, middle dots
    "\u00f7": "/",
    "\u00b2": "^2", "\u00b3": "^3",
})


def _clean_answer(text: str) -> str:
    """Normalise a typed answer: '1,5' -> '1.5', 'x\u00b2' -> 'x^2', 'x = 5' -> '5'."""
    text = text.translate(SYMBOLS)
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    if "=" in text:
        text = text.split("=")[-1]
    return text.strip()


def _size(text: str) -> int:
    """How many operations the text contains, counted as typed (nothing merged or simplified)."""
    try:
        return sp.count_ops(_parse(text, evaluate=False))
    except Exception:
        return sp.count_ops(_parse(text))


def check_answer(question: QuizQuestion, text: str) -> bool:
    cleaned = _clean_answer(text)
    try:
        _check_text(cleaned)  # plain math only, never hand arbitrary text to the parser
        student = _parse(cleaned)
        key = _parse(question.answer)

        if simplify(student - key) != 0:
            return False

        form = FORM_TASKS.get(question.task)
        if form is not None:
            # "Simplify/expand/factor" must be answered in that form, not by retyping the question.
            in_form = student == key or form(student) == student
            # SymPy merges like terms while parsing (2x+3x -> 5x), so also compare the
            # size of what was actually typed with the size of the key.
            not_longer = _size(cleaned) <= _size(question.answer) + 1
            return in_form and not_longer
        return True
    except Exception:
        return cleaned.replace(" ", "") == question.answer.replace(" ", "")
