import re

import sympy as sp

from src.services.quiz import _check_text, _parse


def _clean(line: str) -> str:
    """One line of calculation as plain text SymPy can read."""
    line = line.strip().strip("`$").strip()
    line = line.replace("−", "-").replace("–", "-").replace("×", "*").replace("·", "*")
    line = line.replace("⋅", "*")
    return re.sub(r"^=+\s*", "", line).strip()


def check_steps(lines: list[str]) -> bool | None:
    """
    Do all number-only lines of a worked example have the same value?

    True: they agree. False: some step is wrong. None: fewer than two readable lines, cannot tell.
    SymPy does the arithmetic, so a model cannot get it wrong here.
    """
    values = []
    for raw in lines:
        text = _clean(raw)
        if not text:
            continue
        try:
            _check_text(text)
            value = _parse(text)
        except Exception:
            continue  # not a plain expression, skip the line
        if value.free_symbols:
            continue
        values.append(value)

    if len(values) < 2:
        return None
    return all(sp.simplify(value - values[0]) == 0 for value in values[1:])
