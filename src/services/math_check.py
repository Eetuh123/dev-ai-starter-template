import re

import sympy as sp

from src.services.quiz import _check_text, _parse


def _clean(line: str) -> str:
    """One line of calculation as plain text SymPy can read."""
    line = line.strip().strip("`$").strip()
    line = line.replace("−", "-").replace("–", "-").replace("×", "*").replace("·", "*")
    line = line.replace("⋅", "*")
    return re.sub(r"^=+\s*", "", line).strip()


def _value(text: str):
    """The value of one side of an equation, or None if it is not a plain number-only expression."""
    text = _clean(text)
    if not text:
        return None
    try:
        _check_text(text)
        value = _parse(text)
    except Exception:
        return None
    return None if value.free_symbols else value


def check_steps(lines: list[str]) -> bool | None:
    """
    Is every number-only equation of a worked example true?

    Each line is checked on its own, like "5^2 - 4*1*6 = 1" or "2*(3+4) = 2*7 = 14": all the
    sides of the line must have the same value. Lines in the example may have different values
    from each other (different steps calculate different things).
    True: all checked equations hold. False: some equation is wrong.
    None: no equation could be read, cannot tell. SymPy does the arithmetic, so a model cannot get it wrong.
    """
    checked = 0
    for raw in lines:
        sides = [_value(side) for side in raw.split("=")] if raw.count("=") else []
        sides = [value for value in sides if value is not None]
        if len(sides) < 2:
            continue  # not a readable number-only equation, skip the line
        checked += 1
        if not all(sp.simplify(value - sides[0]) == 0 for value in sides[1:]):
            return False
    return True if checked else None
