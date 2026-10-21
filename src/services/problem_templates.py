"""AI-generated problem templates, one list per concept id.

Every template is a tuple:  (task, expression, at, difficulty, params [, extras])

  task        evaluate, simplify, expand, factor, solve, differentiate or limit
  expression  plain math with {placeholders}. Use {b:+d} for a signed number ("x{b:+d}" -> "x-3").
  at          the point for limits and for evaluate/differentiate "at x = ...", or None
  difficulty  1 (easy) to 3 (hard)
  params      what the placeholders can be, separated by spaces:
                a=2..9        a whole number from 2 to 9
                a=-9..9!0     the same without 0 (list more with !0,1)
                a=2,4,6       one of these values
                c:=a*k+b      derived from earlier parameters (plain Python, no spaces)
                ?s!=0         a condition that must hold, otherwise new numbers are drawn
  extras      optional dict, e.g. {"order": 2} for a second derivative

Nothing here calculates answers. quiz.py builds each question from a template and SymPy
computes the answer key, so a wrong key is not possible. Templates that SymPy rejects
(trivial, undefined, ...) are simply skipped and new numbers are drawn.
"""
import random

_SAFE = {"__builtins__": {}, "abs": abs}


def _sample_params(spec):
    """Draw numbers for one template. Returns a dict of placeholder values."""
    if not spec:
        return {}
    for _ in range(60):
        values = {}
        conditions = []
        for part in spec.split():
            if part.startswith("?"):
                conditions.append(part[1:])
            elif ":=" in part:
                name, code = part.split(":=", 1)
                values[name] = eval(code, _SAFE, dict(values))
            else:
                name, rng = part.split("=", 1)
                excluded = set()
                if "!" in rng:
                    rng, bad = rng.split("!", 1)
                    excluded = {int(v) for v in bad.split(",")}
                if ".." in rng:
                    low, high = rng.split("..")
                    options = list(range(int(low), int(high) + 1))
                else:
                    options = [int(v) for v in rng.split(",")]
                values[name] = random.choice([v for v in options if v not in excluded])
        if all(eval(cond, _SAFE, dict(values)) for cond in conditions):
            return values
    raise ValueError(f"no valid numbers for: {spec}")


def instantiate(template):
    """Turn a template into a {task, expression, at, difficulty} item with real numbers."""
    task, expression, at, difficulty, spec, *rest = template
    values = _sample_params(spec)
    item = {"task": task, "expression": expression.format(**values), "difficulty": difficulty}
    if at is not None:
        item["at"] = at.format(**values)
    if rest:
        extras = dict(rest[0])
        text = extras.pop("text", None)
        item.update(extras)
        if text:
            item["text"] = text.format(**values)  # own wording, e.g. 'Find the midpoint of ...'
    return item


# ----------------------------------------------------------------------------------------
# Shared pieces
# ----------------------------------------------------------------------------------------

_ROOTS = "r=-6..6!0 t=-6..6!0 s:=r+t p:=r*t ?s!=0"   # (x+r)(x+t) = x^2 + s*x + p

FACTOR_QUADRATICS = [
    ("factor", "x^2{s:+d}*x{p:+d}", None, 2, _ROOTS),
    ("factor", "x^2 - {q}", None, 1, "a=2..9 q:=a*a"),
    ("factor", "{a}*x^2{m:+d}*x", None, 1, "a=2..6 k=-5..5!0 m:=a*k"),
    ("factor", "{a}*x^2{s:+d}*x{p:+d}", None, 3, "a=2..3 r=-5..5!0 t=-5..5!0 s:=a*t+r p:=r*t ?s!=0"),
    ("factor", "x^3 - {q}*x", None, 2, "a=2..6 q:=a*a"),
]

LIMIT_FACTOR = [
    ("limit", "(x^2 - {q})/(x - {a})", "{a}", 2, "a=2..9 q:=a*a"),
    ("limit", "(x^2{s:+d}*x{p:+d})/(x{r:+d})", "{nr}", 2, "r=-6..6!0 t=-6..6!0 s:=r+t p:=r*t nr:=-r ?s!=0"),
    ("limit", "(x^3 - {q})/(x - {a})", "{a}", 3, "a=1..4 q:=a*a*a"),
    ("limit", "(sqrt(x{a:+d}) - {b})/(x{nc:+d})", "{c}", 3, "b=2..5 a=1..9 c:=b*b-a nc:=-c ?c!=0"),
    ("limit", "(x^2 - {a}*x)/x", "0", 1, "a=1..9"),
    ("limit", "sin(x)/x", "0", 2, ""),
]

LIMIT_DIRECT = [
    ("limit", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 1, "a=1..4 b=-6..6!0 c=-6..6!0 p=-3..4"),
    ("limit", "({a}*x{b:+d})/(x{c:+d})", "{p}", 2, "a=2..5 b=-5..5!0 c=-5..5!0 p=-4..5 ?p+c!=0"),
    ("limit", "x^2*({a}*x{b:+d})", "{p}", 2, "a=2..4 b=-5..5!0 p=-3..4"),
    ("limit", "sqrt(x{a:+d}) + {b}*x", "{p}", 2, "s=1..5 a=1..6 b=1..4 p:=s*s-a"),
    ("limit", "({a}*x{b:+d})*(x{c:+d})", "{p}", 1, "a=2..4 b=-5..5!0 c=-5..5!0 p=-3..4"),
]

POLY_DERIVS = [
    ("differentiate", "{a}*x^3{b:+d}*x^2{c:+d}*x{d:+d}", None, 2, "a=1..5 b=-6..6!0 c=-6..6!0 d=-9..9!0"),
    ("differentiate", "{a}*x^4{b:+d}*x^2{c:+d}", None, 2, "a=1..4 b=-6..6!0 c=-9..9!0"),
    ("differentiate", "{a}*x^2{b:+d}*x", None, 1, "a=2..9 b=-9..9!0"),
    ("differentiate", "x^{n}{a:+d}*x", None, 1, "n=3..7 a=-6..6!0"),
    ("differentiate", "({a}*x{b:+d})*(x{c:+d})", None, 2, "a=2..4 b=-5..5!0 c=-5..5!0"),
]

_SLOPE = ("evaluate", "({d}{nb:+d})/({c}{na:+d})", None, 2,
          "a=-5..5!0 c=-5..5 b=-5..5!0 d=-5..5 na:=-a nb:=-b ?a!=c",
          {"text": "Find the slope of the line through the points $({a}, {b})$ and $({c}, {d})$."})
_DIST = ("evaluate", "sqrt({dx}^2 + {dy}^2)", None, 2,
         "t=0..3 dx:=[3,5,8,6][t] dy:=[4,12,15,8][t] h:=[5,13,17,10][t] x1=-4..4 y1=-4..4 x2:=x1+dx y2:=y1+dy",
         {"text": "Find the distance between the points $({x1}, {y1})$ and $({x2}, {y2})$."})
_TRIPLE = "t=0..3 dx:=[3,5,8,6][t] dy:=[4,12,15,8][t] h:=[5,13,17,10][t]"


TEMPLATES = {
    # ------------------------------------------------------------------ numbers
    "real_numbers": [
        ("evaluate", "abs({a}) + abs({b})", None, 1, "a=-9..9!0 b=-9..9!0"),
        ("evaluate", "sqrt({s}^2) + {c}", None, 1, "s=2..12 c=1..9"),
        ("evaluate", "{a} - ({b} - {c})", None, 1, "a=1..9 b=1..9 c=1..9"),
        ("evaluate", "abs({a}{b:+d}) - abs({c})", None, 2, "a=-9..9 b=-9..9!0 c=-9..9!0"),
        ("evaluate", "{a}^2 - {b}*{c}", None, 2, "a=2..9 b=2..9 c=2..9"),
    ],
    "arithmetic": [
        ("evaluate", "{a} + {b}*{c}", None, 1, "a=1..9 b=2..9 c=2..9"),
        ("evaluate", "({a} + {b})*{c} - {d}", None, 1, "a=1..9 b=1..9 c=2..6 d=1..9"),
        ("evaluate", "{a}*({b} - {c})^2", None, 2, "a=2..5 b=5..12 c=1..4"),
        ("evaluate", "{a} + {b}^2/2", None, 2, "a=1..9 b=2,4,6,8"),
        ("evaluate", "{a}*{b} - {c}*{d} + {e}", None, 2, "a=2..9 b=2..9 c=2..9 d=2..9 e=1..9"),
        ("evaluate", "({a}{b:+d})/{c} + {d}^2", None, 2, "c=2..5 k=2..6 a=1..9 b:=c*k-a d=2..5"),
    ],
    "fractions": [
        ("evaluate", "{a}/{b} + {c}/{d}", None, 2, "a=1..5 b=2..9 c=1..5 d=2..9 ?b!=d"),
        ("evaluate", "{a}/{b} - {c}/{d}", None, 2, "a=1..5 b=2..9 c=1..5 d=2..9 ?b!=d"),
        ("evaluate", "({a}/{b})*({c}/{d})", None, 1, "a=1..7 b=2..9 c=1..7 d=2..9"),
        ("evaluate", "{a} + {b}/{c}", None, 1, "a=1..5 b=1..9 c=2..9"),
    ],
    "expressions": [
        ("evaluate", "{a}*x{b:+d}", "{p}", 1, "a=2..9 b=-9..9!0 p=-4..6"),
        ("evaluate", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 2, "a=1..4 b=-6..6!0 c=-6..6!0 p=-3..4"),
        ("evaluate", "({a}*x{b:+d})*(x{c:+d})", "{p}", 2, "a=2..4 b=-5..5!0 c=-5..5!0 p=-3..5"),
        ("evaluate", "{a} - {b}*x", "{p}", 1, "a=1..20 b=2..6 p=-4..6"),
        ("simplify", "{a}*x + {b}*x{c:+d}", None, 1, "a=2..7 b=1..6 c=-9..9!0"),
        ("simplify", "{a}*(x{b:+d}) - {c}*x", None, 2, "a=3..7 b=-5..5!0 c=1..2"),
        ("simplify", "{a}*x^2{b:+d}*x + {c}*x^2{d:+d}*x", None, 2, "a=1..5 b=-6..6!0 c=1..5 d=-6..6!0 ?b+d!=0"),
    ],
    "exponent_rules": [
        ("evaluate", "{a}^{m}*{a}^{n}", None, 1, "a=2,3 m=2..4 n=2..3"),
        ("evaluate", "{a}^{m}/{a}^{n}", None, 1, "a=2,3,5 m=4..7 n=1..3"),
        ("evaluate", "({a}^{m})^{n}", None, 2, "a=2,3 m=2..3 n=2..3"),
        ("evaluate", "{a}^(-{m})", None, 2, "a=2,3,5 m=2..3"),
        ("simplify", "x^{m}*x^{n}", None, 1, "m=2..6 n=2..6"),
        ("simplify", "x^{m}/x^{n}", None, 1, "m=5..9 n=1..4"),
        ("simplify", "(x^{m})^{n}", None, 2, "m=2..4 n=2..4"),
    ],
    "scientific_notation": [
        ("evaluate", "{a}*10^{n}", None, 1, "a=2..9 n=2..6"),
        ("evaluate", "{a}*10^(-{n})", None, 2, "a=2..9 n=1..4"),
        ("evaluate", "{a}*10^4{b:+d}*10^3", None, 2, "a=2..9 b=2..9"),
        ("evaluate", "({a}*10^{m})*({b}*10^{n})", None, 2, "a=2..5 b=2..5 m=2..4 n=2..4"),
        ("evaluate", "({a}*10^{m})/({b}*10^{n})", None, 3, "a=2..9 b=2,4,5 m=5..7 n=1..3"),
    ],
    "radicals": [
        ("evaluate", "sqrt({n})", None, 1, "n=8,12,18,20,24,27,32,45,48,50,72"),
        ("evaluate", "sqrt({s}) + sqrt({t})", None, 1, "s=4,9,16,25,36 t=4,9,16,25,36"),
        ("evaluate", "{a}*sqrt({n}){b:+d}*sqrt({n})", None, 2, "a=1..6 b=1..6 n=2,3,5,7"),
        ("evaluate", "sqrt({a})*sqrt({b})", None, 2, "k=2..6 a=2,3,5 b:=a*k*k"),
        ("evaluate", "sqrt({n})/sqrt({m})", None, 3, "m=2,3,5 k=2..5 n:=m*k*k"),
    ],
    "rational_exponents": [
        ("evaluate", "{b}^(3/2)", None, 2, "b=4,9,16,25"),
        ("evaluate", "{b}^(1/3)", None, 1, "b=8,27,64,125"),
        ("evaluate", "{b}^(2/3)", None, 2, "b=8,27,64"),
        ("evaluate", "{b}^(-1/2)", None, 2, "b=4,9,16,25"),
        ("evaluate", "{a}*{b}^(1/2)", None, 1, "a=2..9 b=4,9,16,25,36"),
    ],
    # ------------------------------------------------------------------ algebra
    "polynomials": [
        ("expand", "(x{a:+d})*(x{b:+d})", None, 2, "a=-6..6!0 b=-6..6!0"),
        ("expand", "({a}*x{b:+d})*(x{c:+d})", None, 2, "a=2..4 b=-6..6!0 c=-6..6!0"),
        ("expand", "(x{a:+d})^2", None, 1, "a=-8..8!0"),
        ("expand", "(x{a:+d})*(x^2{b:+d}*x{c:+d})", None, 3, "a=-4..4!0 b=-4..4!0 c=-5..5!0"),
        ("simplify", "(x^2{a:+d}*x{b:+d}) + ({c}*x^2{d:+d}*x{e:+d})", None, 2,
         "a=1..5 b=-6..6!0 c=1..5 d=-6..6!0 e=-6..6!0 ?b+d!=0"),
        ("simplify", "({a}*x^2 + {b}*x) - ({c}*x^2 + {d}*x)", None, 2, "a=3..6 b=2..9 c=1..2 d=1..5"),
    ],
    "factoring": FACTOR_QUADRATICS,
    "rational_expressions": [
        ("simplify", "(x^2{s:+d}*x{p:+d})/(x{r:+d})", None, 2, _ROOTS),
        ("simplify", "(x^2 - {q})/(x - {a})", None, 2, "a=2..9 q:=a*a"),
        ("simplify", "({a}*x^2{m:+d}*x)/x", None, 1, "a=2..6 k=1..5 m:=a*k"),
        ("simplify", "(x^2 - {q})/(x^2{s:+d}*x{p:+d})", None, 3, "a=1..5 t=-6..6!0 q:=a*a s:=a+t p:=a*t ?s!=0 ?t!=-a"),
    ],
    "linear_equations": [
        ("solve", "{a}*x{b:+d} = {c}", None, 1, "a=2..9 b=-9..9!0 x0=-6..9!0 c:=a*x0+b"),
        ("solve", "{a}*(x{b:+d}) = {c}", None, 2, "a=2..6 b=-5..5!0 x0=-6..9!0 c:=a*(x0+b)"),
        ("solve", "{a}*x{b:+d} = {c}*x{d:+d}", None, 2, "a=3..9 c=1..2 b=-9..9!0 x0=-6..9!0 d:=a*x0+b-c*x0 ?d!=0"),
        ("solve", "x/{a}{b:+d} = {c}", None, 2, "a=2..6 k=-5..8 b=-9..9!0 c:=k+b"),
        ("solve", "{a} - {b}*x = {c}", None, 1, "b=2..9 x0=-6..9!0 a=1..20 c:=a-b*x0"),
    ],
    "formula_rearrangement": [
        ("solve", "{a}*x = {c}", None, 1, "a=2..9 x0=-6..9!0 c:=a*x0"),
        ("solve", "x/{a} = {b}", None, 1, "a=2..9 b=-6..9!0"),
        ("solve", "x{a:+d} = {b}*{c}", None, 1, "a=-9..9!0 b=2..9 c=2..9"),
        ("evaluate", "9*x/5 + 32", "{p}", 2, "k=-4..8 p:=5*k"),
    ],
    "quadratic_equations": FACTOR_QUADRATICS[:4],
    "rational_equations": [
        ("solve", "{a}/x = {c}", None, 1, "c=1..5 x0=1..8 a:=c*x0"),
        ("solve", "{a}/(x{b:+d}) = {c}", None, 2, "c=1..4 b=-5..5!0 x0=-4..8 a:=c*(x0+b) ?x0+b!=0"),
        ("solve", "1/x = {a}/{b}", None, 2, "a=2..5 b=1..9"),
    ],
    "radical_equations": [
        ("solve", "sqrt(x{a:+d}) = {b}", None, 1, "a=-6..6!0 b=1..6"),
        ("solve", "sqrt({a}*x) = {b}", None, 2, "a=2..5 k=1..4 b:=a*k"),
        ("solve", "sqrt(x{a:+d}){b:+d} = {c}", None, 3, "a=-6..6!0 s=1..6 b=-9..9!0 c:=s+b"),
    ],
    "absolute_value": [
        ("evaluate", "abs({a}{b:+d})", None, 1, "a=-9..9 b=-9..9!0"),
        ("evaluate", "abs({a}) - abs({b})", None, 1, "a=-9..9!0 b=-9..9!0"),
        ("evaluate", "{a}*abs({b}){c:+d}", None, 2, "a=2..5 b=-9..9!0 c=-9..9!0"),
        ("evaluate", "abs(x{a:+d})", "{p}", 2, "a=-6..6!0 p=-8..8"),
        ("evaluate", "abs({a}*x{b:+d})", "{p}", 2, "a=2..5 b=-9..9!0 p=-5..5"),
    ],
    # ------------------------------------------------------------------ functions
    "coordinate_plane": [
        ("evaluate", "{m}*x{b:+d}", "{p}", 1, "m=2..5 b=-9..9!0 p=-5..5",
         {"text": "A line has the equation $y = {m}x{b:+d}$. Find $y$ when $x = {p}$."}),
        ("evaluate", "({a}{b:+d})/2", None, 1, "a=-9..9!0 b=-9..9!0",
         {"text": "Two points have x-coordinates ${a}$ and ${b}$. Find the x-coordinate of their midpoint."}),
        _DIST,
        _SLOPE,
    ],
    "functions": [
        ("evaluate", "{a}*x{b:+d}", "{p}", 1, "a=2..9 b=-9..9!0 p=-5..6"),
        ("evaluate", "x^2{b:+d}*x{c:+d}", "{p}", 2, "b=-6..6!0 c=-6..6!0 p=-4..5"),
        ("evaluate", "{a}*x^2 - {b}", "{p}", 2, "a=2..4 b=1..9 p=-4..5"),
        ("evaluate", "sqrt(x{a:+d})", "{p}", 2, "s=1..6 a=1..6 p:=s*s-a"),
        ("evaluate", "{a}/(x{b:+d})", "{p}", 2, "a=1..12 b=-5..5!0 p=-4..6 ?p+b!=0"),
        ("evaluate", "x^3 - {a}*x", "{p}", 3, "a=1..6 p=-3..4"),
    ],
    "domain_range": [
        ("evaluate", "sqrt(x{a:+d})", "{p}", 2, "s=1..6 a=1..6 p:=s*s-a"),
        ("evaluate", "1/(x{a:+d})", "{p}", 2, "a=-6..6!0 p=-4..6 ?p+a!=0"),
        ("evaluate", "sqrt({a} - x)", "{p}", 2, "s=1..5 a=2..9 p:=a-s*s"),
        ("evaluate", "x^2{a:+d}", "{p}", 1, "a=-9..9!0 p=-4..5"),
    ],
    "function_graphs": [
        ("evaluate", "x^2{b:+d}*x", "{p}", 2, "b=-6..6!0 p=-4..5"),
        ("evaluate", "{a}*x{b:+d}", "{p}", 1, "a=-5..5!0 b=-9..9!0 p=-4..5"),
        ("evaluate", "x^3 - {a}*x", "{p}", 3, "a=1..6 p=-3..4"),
        ("evaluate", "({b}^2 - {a}^2)/({b} - {a})", None, 2, "a=0..4 b=1..6 ?a<b"),
    ],
    "average_rate": [
        ("evaluate", "({b}^2 - {a}^2)/({b} - {a})", None, 2, "a=0..4 b=1..6 ?a<b",
         {"text": "Find the average rate of change of $f(x) = x^2$ between $x = {a}$ and $x = {b}$."}),
        ("evaluate", "({b}^3 - {a}^3)/({b} - {a})", None, 3, "a=0..3 b=1..5 ?a<b",
         {"text": "Find the average rate of change of $f(x) = x^3$ between $x = {a}$ and $x = {b}$."}),
        ("evaluate", "((2*{b}^2 + {c}) - (2*{a}^2 + {c}))/({b} - {a})", None, 2, "a=0..3 b=1..5 c=1..9 ?a<b",
         {"text": "Find the average rate of change of $f(x) = 2x^2 + {c}$ between $x = {a}$ and $x = {b}$."}),
        ("evaluate", "(sqrt({b}) - sqrt({a}))/({b} - {a})", None, 3, "a=1,4,9,16 b=4,9,16,25 ?a<b",
         {"text": r"Find the average rate of change of $f(x) = \sqrt x$ between $x = {a}$ and $x = {b}$."}),
    ],
    "linear_functions": [
        ("evaluate", "{m}*x{b:+d}", "{p}", 1, "m=-5..5!0 b=-9..9!0 p=-5..6"),
        _SLOPE,
        ("solve", "{m}*x{b:+d} = 0", None, 2, "m=2..6 x0=-6..9!0 b:=-m*x0"),
        ("solve", "{m}*x{b:+d} = {c}", None, 2, "m=2..6 b=-9..9!0 x0=-6..9!0 c:=m*x0+b"),
    ],
    "line_equations": [
        ("evaluate", "{m}*(x{na:+d}){b:+d}", "{p}", 2, "m=-4..4!0 a=-5..5!0 na:=-a b=-9..9!0 p=-5..6"),
        _SLOPE,
        ("solve", "{m}*x{b:+d} = {c}", None, 2, "m=2..6 b=-9..9!0 x0=-6..9!0 c:=m*x0+b"),
        ("evaluate", "{m}*x{b:+d}", "{p}", 1, "m=-5..5!0 b=-9..9!0 p=-5..6"),
    ],
    "quadratic_functions": [
        ("evaluate", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 2, "a=1..3 b=-6..6!0 c=-9..9!0 p=-4..5"),
        ("evaluate", "(x{h:+d})^2{k:+d}", "{p}", 2, "h=-5..5!0 k=-9..9!0 p=-4..6"),
        ("factor", "x^2{s:+d}*x{p:+d}", None, 2, _ROOTS),
        ("factor", "x^2 - {q}", None, 1, "a=2..9 q:=a*a"),
    ],
    "power_functions": [
        ("evaluate", "x^{n}", "{p}", 1, "n=2..5 p=-3..4"),
        ("evaluate", "{a}*x^{n}", "{p}", 2, "a=2..5 n=2..4 p=-3..3"),
        ("evaluate", "x^(3/2)", "{p}", 2, "p=4,9,16,25"),
        ("evaluate", "x^(-2)", "{p}", 2, "p=1..5"),
        ("evaluate", "x^(1/3)", "{p}", 2, "p=8,27,64,125"),
    ],
    "polynomial_graphs": FACTOR_QUADRATICS + [
        ("evaluate", "x^3{b:+d}*x^2{c:+d}*x", "{p}", 2, "b=-5..5!0 c=-6..6!0 p=-3..4"),
    ],
    "rational_functions": [
        ("evaluate", "({a}*x{b:+d})/(x{c:+d})", "{p}", 2, "a=2..5 b=-6..6!0 c=-5..5!0 p=-4..6 ?p+c!=0"),
        ("simplify", "(x^2 - {q})/(x - {a})", None, 2, "a=2..9 q:=a*a"),
        ("simplify", "(x^2{s:+d}*x{p:+d})/(x{r:+d})", None, 2, _ROOTS),
        ("evaluate", "{a}/(x{b:+d})", "{p}", 2, "a=1..12 b=-5..5!0 p=-4..6 ?p+b!=0"),
    ],
    "function_composition": [
        ("evaluate", "({a}*x{b:+d})^2{c:+d}", "{p}", 2, "a=2..4 b=-5..5!0 c=-6..6!0 p=-3..4"),
        ("expand", "({a}*x{b:+d})^2", None, 2, "a=2..4 b=-5..5!0"),
        ("simplify", "{a}*({b}*x{c:+d}){d:+d}", None, 2, "a=2..5 b=2..4 c=-5..5!0 d=-9..9!0"),
        ("evaluate", "{a}*({b}*x{c:+d}){d:+d}", "{p}", 1, "a=2..5 b=2..4 c=-5..5!0 d=-9..9!0 p=-3..4"),
    ],
    "inverse_functions": [
        ("solve", "{a}*x{b:+d} = {c}", None, 1, "a=2..6 b=-9..9!0 x0=-6..9!0 c:=a*x0+b"),
        ("solve", "x^3{a:+d} = {c}", None, 2, "a=-9..9!0 s=-3..4 c:=s*s*s+a"),
        ("solve", "x/{a}{b:+d} = {c}", None, 2, "a=2..6 b=-9..9!0 k=-5..8 c:=k+b"),
    ],
    # ------------------------------------------------------------------ exp / log
    "exponential_functions": [
        ("evaluate", "{a}*2^x", "{p}", 1, "a=1..9 p=0..6"),
        ("evaluate", "{a}*3^x", "{p}", 1, "a=1..5 p=0..4"),
        ("evaluate", "{a}*(1/2)^x", "{p}", 2, "a=8,16,32,64,100,200 p=0..5"),
        ("evaluate", "2^(x{b:+d})", "{p}", 2, "b=-3..3!0 p=0..6"),
    ],
    "logarithms": [
        ("evaluate", "log({b}^{n})/log({b})", None, 1, "b=2,3,5,7 n=2..5"),
        ("evaluate", "ln(exp({a}))", None, 1, "a=2..9"),
        ("evaluate", "exp(ln({a}))", None, 1, "a=2..9"),
        ("evaluate", "log({b}^{n})/log({b}){c:+d}", None, 2, "b=2,3,5 n=2..4 c=1..9"),
        ("evaluate", "ln(exp({a})*exp({b}))", None, 2, "a=1..6 b=1..6"),
    ],
    "log_rules": [
        ("evaluate", "log({b}^{n})/log({b}) - log({e}^{m})/log({e})", None, 3, "b=2,3 e=5,7 n=3..5 m=2..3"),
        ("evaluate", "ln(exp({a})*exp({b}))", None, 2, "a=1..6 b=1..6"),
        ("evaluate", "ln(exp({a})/exp({b}))", None, 2, "a=3..9 b=1..2"),
        ("evaluate", "log({b}^{n})/log({b}) + log({c}^{m})/log({c})", None, 2, "b=2,3 c=5,7 n=2..4 m=2..3"),
    ],
    "exp_log_equations": [
        ("solve", "2^x = {c}", None, 1, "k=1..8 c:=2**k"),
        ("solve", "3^x = {c}", None, 1, "k=1..5 c:=3**k"),
        ("solve", "2^(x{a:+d}) = {c}", None, 2, "a=-3..3!0 k=1..7 c:=2**k"),
        ("solve", "5^(x{a:+d}) = {c}", None, 2, "a=-2..2!0 k=1..4 c:=5**k"),
        ("solve", "ln(x{a:+d}) = 0", None, 2, "a=-6..6!0"),
    ],
    # ------------------------------------------------------------------ trigonometry
    "angles_radians": [
        ("evaluate", "{d}*pi/180", None, 1, "d=30,45,60,90,120,135,150,180,210,240,270,300,360"),
        ("evaluate", "{d}*pi/180", None, 2, "d=15,36,72,225,315"),
    ],
    "unit_circle": [
        ("evaluate", "sin(pi/{n})", None, 1, "n=2,3,4,6"),
        ("evaluate", "cos(pi/{n})", None, 1, "n=2,3,4,6"),
        ("evaluate", "sin({k}*pi/6)", None, 2, "k=2,3,4,5,7,8,9,10,11"),
        ("evaluate", "cos({k}*pi/4)", None, 2, "k=2,3,5,6,7"),
    ],
    "sin_cos": [
        ("evaluate", "{a}*sin(pi/{n}){b:+d}*cos(pi/{m})", None, 2, "a=2..4 n=2,3,6 b=1..3 m=3,4"),
        ("evaluate", "2*sin(pi/{n})*cos(pi/{n})", None, 2, "n=3,4,6"),
        ("evaluate", "sin({k}*pi/3)", None, 2, "k=2,4,5"),
        ("evaluate", "cos({k}*pi/3)", None, 2, "k=2,4,5"),
        ("evaluate", "{a}*sin(pi/2) - {b}*cos(pi)", None, 1, "a=1..5 b=1..5"),
    ],
    "tan_reciprocal": [
        ("evaluate", "tan(pi/{n})", None, 1, "n=3,4,6"),
        ("evaluate", "1/sin(pi/{n})", None, 2, "n=2,3,4,6"),
        ("evaluate", "1/cos(pi/{n})", None, 2, "n=3,4,6"),
        ("evaluate", "1/tan(pi/{n})", None, 2, "n=3,4,6"),
    ],
    "right_triangle": [
        ("evaluate", "{dy}/sqrt({dx}^2 + {dy}^2)", None, 2, _TRIPLE,
         {"text": "A right triangle has legs ${dx}$ and ${dy}$. Find the sine of the angle opposite the leg of length ${dy}$."}),
        ("evaluate", "{dx}/sqrt({dx}^2 + {dy}^2)", None, 2, _TRIPLE,
         {"text": "A right triangle has legs ${dx}$ and ${dy}$. Find the cosine of the angle next to the leg of length ${dx}$."}),
        ("evaluate", "sqrt({h}^2 - {dx}^2)", None, 2, _TRIPLE,
         {"text": "A right triangle has hypotenuse ${h}$ and one leg ${dx}$. Find the length of the other leg."}),
    ],
    "trig_graphs": [
        ("evaluate", "{a}*sin(pi*x/2)", "{p}", 2, "a=2..5 p=0..5"),
        ("evaluate", "{a}*cos(pi*x)", "{p}", 2, "a=2..5 p=0..5"),
        ("evaluate", "{a}*cos(pi*x/3){b:+d}", "{p}", 3, "a=2..5 b=-5..5!0 p=0..6"),
    ],
    "tangent_graph": [
        ("evaluate", "tan(pi*x/4)", "{p}", 2, "p=-1,0,1"),
        ("evaluate", "{a}*tan(pi*x/4)", "{p}", 2, "a=2..5 p=-1,0,1"),
        ("evaluate", "tan(pi*x/6)", "{p}", 2, "p=-1,0,1,2"),
    ],
    "inverse_trig": [
        ("evaluate", "asin({v})", None, 2, "t=0..5 v:=['0','1/2','1','-1/2','sqrt(2)/2','sqrt(3)/2'][t]"),
        ("evaluate", "acos({v})", None, 2, "t=0..5 v:=['0','1/2','1','-1/2','sqrt(2)/2','sqrt(3)/2'][t]"),
        ("evaluate", "atan({v})", None, 2, "t=0..3 v:=['0','1','-1','sqrt(3)'][t]"),
    ],
    "trig_identities": [
        ("simplify", "sin(x)^2 + cos(x)^2", None, 1, ""),
        ("simplify", "1 - sin(x)^2", None, 2, ""),
        ("simplify", "tan(x)*cos(x)", None, 2, ""),
        ("simplify", "sin(x)/cos(x)", None, 1, ""),
        ("simplify", "(1 - cos(x)^2)/sin(x)", None, 3, ""),
        ("simplify", "{a}*sin(x)^2 + {a}*cos(x)^2", None, 2, "a=2..9"),
    ],
    "angle_sum": [
        ("evaluate", "sin(pi/{a} + pi/{b})", None, 3, "a=3,4,6 b=3,4,6 ?a!=b"),
        ("evaluate", "cos(pi/{a} - pi/{b})", None, 3, "a=3,4,6 b=3,4,6 ?a!=b"),
        ("evaluate", "sin(pi/3 + pi/6)", None, 2, ""),
        ("evaluate", "cos(pi/2 - pi/6)", None, 2, ""),
    ],
    "double_angle": [
        ("evaluate", "2*sin(pi/{n})*cos(pi/{n})", None, 2, "n=3,4,6"),
        ("evaluate", "cos(pi/{n})^2 - sin(pi/{n})^2", None, 2, "n=3,4,6,12"),
        ("evaluate", "1 - 2*sin(pi/{n})^2", None, 2, "n=3,4,6"),
    ],
    # ------------------------------------------------------------------ limits
    "limits": LIMIT_FACTOR[:3] + LIMIT_DIRECT[:2],
    "one_sided_limits": LIMIT_FACTOR[:3] + LIMIT_DIRECT[:2],
    "limit_laws": LIMIT_DIRECT,
    "limit_simplification": LIMIT_FACTOR,
    "continuity": LIMIT_DIRECT[:3] + LIMIT_FACTOR[:2],
    # ------------------------------------------------------------------ derivatives
    "derivative_definition": POLY_DERIVS,
    "derivative_function": POLY_DERIVS,
    "power_rule": [
        ("differentiate", "x^{n}", None, 1, "n=2..9"),
        ("differentiate", "{a}*x^{n}", None, 1, "a=2..9 n=2..7"),
        ("differentiate", "sqrt(x)", None, 2, ""),
        ("differentiate", "x^(-{n})", None, 2, "n=1..4"),
        ("differentiate", "{a}*x^{n}{b:+d}*x", None, 1, "a=2..9 n=3..6 b=-9..9!0"),
    ],
    "derivative_rules": POLY_DERIVS,
    "product_rule": [
        ("differentiate", "(x^2{a:+d})*(x^3{b:+d}*x)", None, 2, "a=-5..5!0 b=-5..5!0"),
        ("differentiate", "x*sin(x)", None, 2, ""),
        ("differentiate", "x^2*cos(x)", None, 2, ""),
        ("differentiate", "x^{n}*exp(x)", None, 2, "n=2..4"),
        ("differentiate", "{a}*x*ln(x)", None, 3, "a=2..5"),
    ],
    "quotient_rule": [
        ("differentiate", "x/(x{a:+d})", None, 2, "a=-6..6!0"),
        ("differentiate", "(x^2{a:+d})/(x{b:+d})", None, 2, "a=-6..6!0 b=-5..5!0"),
        ("differentiate", "x^2/(x^2{a:+d})", None, 3, "a=1..6"),
        ("differentiate", "sin(x)/x", None, 3, ""),
        ("differentiate", "exp(x)/x^2", None, 3, ""),
    ],
    "trig_derivatives": [
        ("differentiate", "sin(x)", None, 1, ""),
        ("differentiate", "{a}*cos(x)", None, 1, "a=2..9"),
        ("differentiate", "tan(x)", None, 2, ""),
        ("differentiate", "{a}*sin(x){b:+d}*cos(x)", None, 2, "a=2..6 b=-6..6!0"),
        ("differentiate", "x*sin(x)", None, 3, ""),
    ],
    "chain_rule": [
        ("differentiate", "({a}*x{b:+d})^{n}", None, 2, "a=2..5 b=-5..5!0 n=3..6"),
        ("differentiate", "sin({a}*x)", None, 2, "a=2..6"),
        ("differentiate", "cos(x^{n})", None, 2, "n=2..4"),
        ("differentiate", "exp({a}*x)", None, 2, "a=2..6"),
        ("differentiate", "sqrt({a}*x{b:+d})", None, 3, "a=2..5 b=1..6"),
        ("differentiate", "ln({a}*x{b:+d})", None, 3, "a=2..5 b=1..6"),
    ],
    "nested_chain_rule": [
        ("differentiate", "sin(({a}*x{b:+d})^2)", None, 3, "a=2..4 b=-4..4!0"),
        ("differentiate", "exp(sin(x))", None, 3, ""),
        ("differentiate", "sin({a}*x)^{n}", None, 3, "a=2..4 n=2..4"),
        ("differentiate", "ln(cos(x))", None, 3, ""),
        ("differentiate", "sqrt(x^2{a:+d})", None, 3, "a=1..6"),
        ("differentiate", "cos(exp({a}*x))", None, 3, "a=2..4"),
    ],
    "exp_log_derivatives": [
        ("differentiate", "exp({a}*x)", None, 1, "a=2..6"),
        ("differentiate", "ln(x^{n})", None, 2, "n=2..5"),
        ("differentiate", "x*exp(x)", None, 2, ""),
        ("differentiate", "{a}^x", None, 2, "a=2,3,5"),
        ("differentiate", "exp(x^2)", None, 2, ""),
        ("differentiate", "ln({a}*x{b:+d})", None, 3, "a=2..5 b=1..6"),
        ("differentiate", "x*ln(x)", None, 3, ""),
    ],
    "inverse_derivatives": [
        ("differentiate", "ln(x)", None, 1, ""),
        ("differentiate", "{a}*ln(x)", None, 1, "a=2..9"),
        ("differentiate", "x^(1/3)", None, 2, ""),
        ("differentiate", "sqrt({a}*x)", None, 2, "a=2..9"),
        ("differentiate", "exp({a}*x)", None, 1, "a=2..6"),
    ],
    "inverse_trig_derivatives": [
        ("differentiate", "asin(x)", None, 2, ""),
        ("differentiate", "atan(x)", None, 2, ""),
        ("differentiate", "acos(x)", None, 2, ""),
        ("differentiate", "atan({a}*x)", None, 3, "a=2..5"),
        ("differentiate", "asin({a}*x)", None, 3, "a=2..4"),
        ("differentiate", "x*atan(x)", None, 3, ""),
    ],
    "higher_derivatives": [
        ("differentiate", "{a}*x^4{b:+d}*x^3{c:+d}*x", None, 2, "a=1..4 b=-6..6!0 c=-6..6!0", {"order": 2}),
        ("differentiate", "{a}*x^3{b:+d}*x^2", None, 1, "a=2..6 b=-6..6!0", {"order": 2}),
        ("differentiate", "sin({a}*x)", None, 2, "a=2..4", {"order": 2}),
        ("differentiate", "exp({a}*x)", None, 2, "a=2..4", {"order": 2}),
        ("differentiate", "ln(x)", None, 2, "", {"order": 2}),
        ("differentiate", "x^{n}", None, 1, "n=4..8", {"order": 3}),
    ],
    "tangent_line": [
        ("differentiate", "{a}*x^2{b:+d}*x", "{p}", 1, "a=1..4 b=-6..6!0 p=-3..4"),
        ("differentiate", "x^3 - {a}*x", "{p}", 2, "a=1..6 p=-3..3"),
        ("differentiate", "x^3{b:+d}*x^2{c:+d}", "{p}", 2, "b=-5..5!0 c=-6..6!0 p=-2..3"),
        ("differentiate", "x^2*({a}*x{b:+d})", "{p}", 3, "a=2..3 b=-4..4!0 p=-2..3"),
    ],
    "rates_of_change": [
        ("differentiate", "{a}*x^2{b:+d}*x", "{p}", 1, "a=1..4 b=-6..6!0 p=-3..4"),
        ("differentiate", "x^3 - {a}*x", "{p}", 2, "a=1..6 p=-3..3"),
        ("differentiate", "{a}*x^3{b:+d}*x^2", "{p}", 2, "a=1..3 b=-5..5!0 p=-2..3"),
        ("differentiate", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 2, "a=1..4 b=-6..6!0 c=-9..9!0 p=-3..4"),
    ],
}


# ----------------------------------------------------------------------------------------
# More templates (own wording for many of them). Merged into TEMPLATES at the bottom.
# ----------------------------------------------------------------------------------------

MORE = {}


MORE.update({
    "real_numbers": [
        ("evaluate", "{a} - {b}*({c} - {d})", None, 2, "a=1..20 b=2..6 c=5..12 d=1..4"),
        ("evaluate", "abs({a} - {b}) + abs({c})", None, 1, "a=1..9 b=10..20 c=-9..-1"),
        ("evaluate", "sqrt({s}^2) - abs({a})", None, 1, "s=3..12 a=-9..-1"),
        ("evaluate", "({a} - {b})*({c} + {d})", None, 1, "a=1..9 b=1..9 c=1..9 d=1..9 ?a!=b"),
        ("evaluate", "{a}*abs({b} - {c})", None, 2, "a=2..6 b=-9..9 c=-9..9 ?b!=c"),
    ],
    "arithmetic": [
        ("evaluate", "{a}*{b} + {c}*{d}", None, 1, "a=2..9 b=2..9 c=2..9 d=2..9"),
        ("evaluate", "({a} + {b})^2", None, 2, "a=1..9 b=1..9"),
        ("evaluate", "{a}^2 - {b}^2", None, 2, "a=6..12 b=2..5"),
        ("evaluate", "({a} - {b})*({c} - {d})", None, 2, "a=5..15 b=1..4 c=6..12 d=1..5"),
        ("evaluate", "{a}*({b} + {c}) - {d}*{e}", None, 2, "a=2..6 b=1..9 c=1..9 d=2..6 e=2..6"),
        ("evaluate", "{a}^3 - {b}", None, 2, "a=2..5 b=1..9"),
    ],
    "fractions": [
        ("evaluate", "{a}/{b} + {c}", None, 1, "a=1..5 b=2..9 c=2..9"),
        ("evaluate", "({a}/{b})*{c}", None, 1, "a=1..5 b=2..9 c=2..9"),
        ("evaluate", "1/{a} + 1/{b}", None, 2, "a=2..6 b=3..9 ?a!=b"),
        ("evaluate", "1/{a} - 1/{b}", None, 2, "a=2..6 b=3..9 ?a<b"),
        ("evaluate", "({a} + {b}/{c})/{d}", None, 2, "a=1..4 b=1..5 c=2..6 d=2..5"),
        ("evaluate", "{a}/{b} + {c}/{d} + {e}/12", None, 3, "a=1..3 b=2,3,4 c=1..3 d=3,4,6 e=1..5"),
    ],
    "expressions": [
        ("evaluate", "{a}*x^2 - {b}*x", "{p}", 2, "a=1..4 b=1..6 p=-4..5"),
        ("evaluate", "({a}*x{b:+d})^2", "{p}", 2, "a=2..4 b=-4..4!0 p=-3..3"),
        ("evaluate", "{a}*(x{b:+d})^2{c:+d}", "{p}", 3, "a=2..4 b=-4..4!0 c=-9..9!0 p=-3..3"),
        ("simplify", "{a}*(x{b:+d}) + {c}*(x{d:+d})", None, 2, "a=2..4 b=-5..5!0 c=2..4 d=-5..5!0 ?a*b+c*d!=0"),
        ("evaluate", "{a}*x + {b}*x^2", "{p}", 1, "a=2..6 b=1..4 p=-4..5"),
    ],
    "exponent_rules": [
        ("simplify", "x^{m}*x^{n}/x^{k}", None, 2, "m=3..7 n=2..5 k=1..4"),
        ("simplify", "({a}*x^{m})*({b}*x^{n})", None, 2, "a=2..5 b=2..5 m=2..4 n=2..4"),
        ("simplify", "({a}*x^{m})/({b}*x^{n})", None, 3, "b=2..4 k=2..4 a:=b*k m=5..8 n=1..4"),
        ("simplify", "(x^{m})^{n}*x", None, 2, "m=2..4 n=2..3"),
        ("evaluate", "{a}^{m}*{b}^{m}", None, 2, "a=2,3 b=5 m=2..3"),
    ],
    "scientific_notation": [
        ("evaluate", "{a}*10^{m} + {b}*10^{m}", None, 2, "a=1..5 b=1..4 m=2..5"),
        ("evaluate", "{a}*10^{n}*{b}", None, 1, "a=2..9 b=2..9 n=2..4"),
        ("evaluate", "({a}*10^{m})^2", None, 3, "a=2..4 m=2..3"),
        ("evaluate", "{a}*10^(-{m})*10^{n}", None, 2, "a=2..9 m=1..3 n=4..6"),
        ("evaluate", "({a}*10^{m})/10^{n}", None, 2, "a=2..9 m=5..7 n=1..3"),
    ],
    "radicals": [
        ("evaluate", "sqrt({a}) + sqrt({n})", None, 2, "k=2..4 n=2,3,5 a:=k*k*n"),
        ("evaluate", "sqrt({a}) - sqrt({n})", None, 2, "k=2..4 n=2,3,5 a:=k*k*n"),
        ("evaluate", "({a} + sqrt({n}))*({a} - sqrt({n}))", None, 3, "a=3..9 n=2,3,5,7"),
        ("evaluate", "(sqrt({a}) + {b})^2", None, 3, "a=2,3,5 b=1..4"),
        ("evaluate", "{a}/sqrt({n})", None, 3, "n=2,3,5 a=2..9"),
    ],
    "rational_exponents": [
        ("evaluate", "{b}^(1/2) + {c}^(1/3)", None, 2, "b=4,9,16,25 c=8,27,64"),
        ("evaluate", "{b}^(5/2)", None, 3, "b=4,9"),
        ("evaluate", "{b}^(4/3)", None, 3, "b=8,27"),
        ("evaluate", "({b}^(1/2))^3", None, 2, "b=4,9,16"),
        ("evaluate", "{b}^(-3/2)", None, 3, "b=4,9"),
        ("evaluate", "{b}^(1/4)", None, 2, "b=16,81"),
    ],
    "polynomials": [
        ("expand", "({a}*x{b:+d})^2", None, 2, "a=2..4 b=-5..5!0"),
        ("expand", "(x{a:+d})*(x{b:+d})*(x{c:+d})", None, 3, "a=-3..3!0 b=-3..3!0 c=-3..3!0"),
        ("expand", "(x{a:+d})*(x{na:+d})", None, 1, "a=1..9 na:=-a"),
        ("expand", "{a}*x*(x{b:+d})", None, 1, "a=2..6 b=-6..6!0"),
        ("expand", "(x^2{a:+d})*(x{b:+d})", None, 2, "a=-4..4!0 b=-4..4!0"),
        ("simplify", "({a}*x^2{b:+d}) - ({c}*x^2{d:+d})", None, 2, "a=3..8 b=-5..5!0 c=1..2 d=-5..5!0"),
    ],
    "factoring": [
        ("factor", "{a}*x^2 - {q}", None, 3, "k=2..4 a=2..3 q:=a*k*k"),
        ("factor", "x^2{s:+d}*x", None, 1, "s=-9..9!0"),
        ("factor", "x^3{s:+d}*x^2", None, 2, "s=-9..9!0"),
        ("factor", "x^4 - {q}", None, 3, "a=2..4 q:=a*a*a*a"),
        ("factor", "x^2{s:+d}*x{p:+d}", None, 2, "r=1..8 t=1..8 s:=r+t p:=r*t"),
    ],
    "rational_expressions": [
        ("simplify", "({a}*x^2)/({b}*x)", None, 1, "b=2..4 k=2..4 a:=b*k"),
        ("simplify", "(x^2 - {q})/(x{a:+d})", None, 2, "a=2..9 q:=a*a"),
        ("simplify", "(x{a:+d})^2/(x{a:+d})", None, 1, "a=-9..9!0"),
        ("simplify", "(x^3 - {q}*x)/x", None, 2, "a=2..6 q:=a*a"),
        ("simplify", "({a}*x{b:+d})/({a})", None, 1, "k=-5..5!0 a=2..5 b:=a*k"),
        ("simplify", "(x^2{s:+d}*x)/(x{a:+d})", None, 2, "a=-9..9!0 s:=-a"),
    ],
    "linear_equations": [
        ("solve", "x{a:+d} = {b}*x{c:+d}", None, 2, "b=2..4 x0=-6..9!0 c=-9..9!0 a:=c+(b-1)*x0 ?a!=0"),
        ("solve", "{a}*(x{b:+d}) - {c} = {d}", None, 2, "a=2..5 b=-5..5!0 x0=-6..9 c=1..9 d:=a*(x0+b)-c"),
        ("solve", "{a}*(x{b:+d}){c:+d}*(x{d:+d}) = {e}", None, 3, "a=2..4 c=2..4 b=-4..4!0 d=-4..4!0 x0=-5..6 e:=a*(x0+b)+c*(x0+d)"),
        ("solve", "x/2 + x/3 = {c}", None, 3, "k=1..6 c:=5*k"),
        ("solve", "x/2 - x/4 = {c}", None, 2, "c=1..8"),
        ("solve", "x/3 + x/6 = {c}", None, 2, "c=1..8"),
    ],
    "formula_rearrangement": [
        ("evaluate", "(5/9)*(x - 32)", "{p}", 2, "k=-4..8 p:=32+9*k",
         {"text": "Convert ${p}$ degrees Fahrenheit to Celsius using $C = (5/9)(F - 32)$."}),
        ("evaluate", "({a}/2)*x^2", "{p}", 2, "a=2,4,6,8,10 p=1..6",
         {"text": "The distance fallen is $d = {a}t^2/2$. Find $d$ when $t = {p}$."}),
        ("solve", "2*x + 2*{w} = {p}", None, 1, "w=2..9 l=2..15 p:=2*(w+l)",
         {"text": "A rectangle has width ${w}$ and perimeter ${p}$. Find its length."}),
        ("solve", "x*{h}/2 = {A}", None, 2, "h=2,4,6,8 b=2..9 A:=b*h//2",
         {"text": "A triangle has area ${A}$ and height ${h}$. Find its base."}),
        ("evaluate", "{a} + {b}*x", "{p}", 1, "a=5..40 b=2..9 p=1..12",
         {"text": "A taxi charges a ${a}$ fee plus ${b}$ per kilometre. Find the cost of a ${p}$ km trip."}),
    ],
})

MORE.update({
    "quadratic_equations": [
        ("solve", "(x{a:+d})^2 = 0", None, 2, "a=-9..9!0"),
        ("evaluate", "{b}^2 - 4*{a}*{c}", None, 2, "a=2..3 b=-6..6!0,1,-1 c=-5..5!0",
         {"text": "Find the discriminant $b^2 - 4ac$ of $ {a}x^2{b:+d}x{c:+d} = 0$."}),
        ("evaluate", "(-({b}) + sqrt(({b})^2 - 4*{a}*({c})))/(2*{a})", None, 3,
         "a=2..3 r=-4..4 t=-4..4 ?r>t ?r+t!=0 ?r*t!=0 b:=-a*(r+t) c:=a*r*t",
         {"text": "Find the larger root of ${a}x^2{b:+d}x{c:+d} = 0$."}),
        ("evaluate", "(-({b}) - sqrt(({b})^2 - 4*{a}*({c})))/(2*{a})", None, 3,
         "a=2..3 r=-4..4 t=-4..4 ?r>t ?r+t!=0 ?r*t!=0 b:=-a*(r+t) c:=a*r*t",
         {"text": "Find the smaller root of ${a}x^2{b:+d}x{c:+d} = 0$."}),
        ("factor", "x^2{s:+d}*x", None, 1, "s=-9..9!0"),
    ],
    "rational_equations": [
        ("solve", "{a}/x + {b}/x = {c}", None, 2, "c=1..4 x0=2..6 a=1..4 b:=c*x0-a ?b>0"),
        ("solve", "x/{a} = {b}/{c}", None, 2, "a=2..6 c=2..4 k=1..4 b:=c*k"),
        ("solve", "1/x + 1/{a} = 1/{b}", None, 3, "t=0..4 a:=[6,6,4,12,6][t] b:=[3,2,2,4,4][t]"),
        ("solve", "{a}/x = {b}/{c}", None, 2, "b=2..5 c=2..4 k=1..6 a:=b*k"),
        ("solve", "({a}*x{b:+d})/x = {c}", None, 3, "a=2..5 d=1..4 c:=a+d x0=1..6 b:=d*x0"),
        ("solve", "{a}/(2*x{b:+d}) = {c}", None, 3, "c=1..3 x0=1..5 b=-4..4!0 a:=c*(2*x0+b) ?a>0"),
    ],
    "radical_equations": [
        ("solve", "sqrt({a}*x{b:+d}) = {c}", None, 2, "a=2..4 c=2..6 x0=1..9 b:=c*c-a*x0 ?b!=0"),
        ("solve", "sqrt(x) = {a}", None, 1, "a=2..12"),
        ("solve", "{a}*sqrt(x) = {b}", None, 2, "a=2..4 k=2..6 b:=a*k"),
        ("solve", "sqrt({a} - x) = {b}", None, 2, "b=1..5 a=6..20"),
        ("solve", "sqrt(2*x{a:+d}) = {b}", None, 2, "b=2..6 a=-9..9!0 ?(b*b-a)%2==0"),
    ],
    "absolute_value": [
        ("evaluate", "abs({a}) * abs({b})", None, 1, "a=-9..9!0 b=-9..9!0"),
        ("evaluate", "abs(x - {a}) + abs(x + {b})", "{p}", 2, "a=1..6 b=1..6 p=-8..8"),
        ("evaluate", "abs({a}*{b} - {c})", None, 2, "a=2..6 b=2..6 c=5..40"),
        ("evaluate", "abs(x^2 - {a})", "{p}", 2, "a=1..9 p=-4..4"),
        ("evaluate", "abs({a}) - abs({b}) + abs({c})", None, 1, "a=-9..9!0 b=-9..9!0 c=-9..9!0"),
    ],
    "coordinate_plane": [
        ("evaluate", "({a}{b:+d})/2", None, 1, "a=-9..9 b=-9..9!0 y1=-5..5 y2=-5..5 ?a!=b",
         {"text": "Find the x-coordinate of the midpoint of $({a}, {y1})$ and $({b}, {y2})$."}),
        ("evaluate", "sqrt({a}^2 + {b}^2)", None, 2, "t=0..3 a:=[3,5,8,6][t] b:=[4,12,15,8][t]",
         {"text": "Find the distance from the origin to the point $({a}, {b})$."}),
        ("solve", "{m}*x{b:+d} = 0", None, 2, "m=2..6 x0=-6..9!0 b:=-m*x0",
         {"text": "Find the $x$-coordinate where the line $y = {m}x{b:+d}$ crosses the $x$-axis."}),
        ("evaluate", "({x2} - {x1})*({y2} - {y1})", None, 2, "x1=-4..0 x2=1..5 y1=-4..0 y2=1..5",
         {"text": "A rectangle has opposite corners at $({x1}, {y1})$ and $({x2}, {y2})$. Find its area."}),
        ("evaluate", "2*({m}) - ({a})", None, 2, "a=-9..9 m=-9..9 ?a!=m",
         {"text": "The midpoint of a segment has x-coordinate ${m}$ and one end has x-coordinate ${a}$. Find the x-coordinate of the other end."}),
        ("evaluate", "({a}{b:+d})/2", None, 1, "a=-9..9 b=-9..9!0 x1=-5..5 x2=-5..5 ?a!=b",
         {"text": "Find the y-coordinate of the midpoint of $({x1}, {a})$ and $({x2}, {b})$."}),
    ],
    "functions": [
        ("evaluate", "{a}*x^2{b:+d}*x", "{p}", 2, "a=2..4 b=-6..6!0,1,-1 p=-4..5",
         {"text": "Let $f(x) = {a}x^2{b:+d}x$. Find $f({p})$."}),
        ("evaluate", "{a}*x{b:+d}", "{p}", 1, "a=2..9 b=-9..9!0 p=-5..6",
         {"text": "Let $f(x) = {a}x{b:+d}$. Find $f({p})$."}),
        ("evaluate", "sqrt({a}*x{b:+d})", "{p}", 2, "s=1..6 a=2..4 p=1..6 b:=s*s-a*p ?b!=0",
         {"text": r"Let $f(x) = \sqrt{{{a}x{b:+d}}}$. Find $f({p})$."}),
        ("evaluate", "{a}/(x{b:+d})", "{p}", 2, "a=1..12 b=-5..5!0 p=-4..6 ?p+b!=0",
         {"text": r"Let $f(x) = \frac{{{a}}}{{x{b:+d}}}$. Find $f({p})$."}),
        ("evaluate", "2*x^2 - {a}*x + {b}", "{p}", 2, "a=2..6 b=1..9 p=-3..4",
         {"text": "Let $f(x) = 2x^2 - {a}x + {b}$. Find $f({p})$."}),
    ],
    "domain_range": [
        ("solve", "x{a:+d} = 0", None, 1, "a=-9..9!0",
         {"text": r"The function $f(x) = \frac{{1}}{{x{a:+d}}}$ is undefined at exactly one value of $x$. Find it."}),
        ("solve", "{a} - x = 0", None, 1, "a=2..12",
         {"text": r"Find the largest value of $x$ for which $\sqrt{{{a} - x}}$ is defined."}),
        ("solve", "x{a:+d} = 0", None, 1, "a=-9..9!0",
         {"text": r"Find the smallest value of $x$ for which $\sqrt{{x{a:+d}}}$ is defined."}),
        ("solve", "{a}*x{b:+d} = 0", None, 2, "a=2..5 k=-5..5!0 b:=a*k",
         {"text": r"The function $f(x) = \frac{{1}}{{{a}x{b:+d}}}$ is undefined at exactly one value of $x$. Find it."}),
    ],
    "function_graphs": [
        ("evaluate", "{m}*x{b:+d}", "{p}", 1, "m=2..5 b=-9..9!0 p=-5..6",
         {"text": "The graph of $y = {m}x{b:+d}$ passes through the point with $x = {p}$. Find its $y$-coordinate."}),
        ("evaluate", "(x{a:+d})^2", "{p}", 2, "a=-5..5!0 p=-4..4",
         {"text": "The graph of $y = (x{a:+d})^2$ is a parabola. Find $y$ when $x = {p}$."}),
        ("evaluate", "-x^2 + {a}*x", "{p}", 2, "a=2..8 p=0..6",
         {"text": "A ball's height is $h = -t^2 + {a}t$. Find $h$ when $t = {p}$."}),
        ("evaluate", "abs(x{a:+d})", "{p}", 2, "a=-6..6!0 p=-8..8",
         {"text": r"The graph of $y = |x{a:+d}|$ is V-shaped. Find $y$ when $x = {p}$."}),
        ("solve", "{m}*x{b:+d} = 0", None, 2, "m=2..6 x0=-6..9!0 b:=-m*x0",
         {"text": "Find the $x$-value where the graph of $y = {m}x{b:+d}$ crosses the $x$-axis."}),
    ],
    "linear_functions": [
        ("evaluate", "{m}*x{b:+d}", "{p}", 1, "m=2..5 b=-9..9!0 p=-5..6",
         {"text": "A linear function is $f(x) = {m}x{b:+d}$. Find $f({p})$."}),
        ("solve", "{m}*x{b:+d} = {c}", None, 2, "m=2..6 b=-9..9!0 x0=-6..9!0 c:=m*x0+b",
         {"text": "For $f(x) = {m}x{b:+d}$, find the value of $x$ with $f(x) = {c}$."}),
        ("evaluate", "({f2} - ({f1}))/({x2} - {x1})", None, 2,
         "x1=0..3 x2=4..8 m=-4..5!0 b=-5..5 f1:=m*x1+b f2:=m*x2+b",
         {"text": "A linear function has $f({x1}) = {f1}$ and $f({x2}) = {f2}$. Find its slope."}),
        ("evaluate", "{f1} - {m}*{x1}", None, 2, "m=2..5 x1=1..5 b=-9..9!0 f1:=m*x1+b",
         {"text": "A line has slope ${m}$ and passes through $({x1}, {f1})$. Find its $y$-intercept."}),
        ("evaluate", "{b} + {m}*x", "{p}", 1, "b=10..60 m=5..30 p=1..8",
         {"text": "A plumber charges ${b}$ for the call-out plus ${m}$ per hour. Find the cost of ${p}$ hours."}),
    ],
    "line_equations": [
        ("evaluate", "{f1} - {m}*{x1}", None, 2, "m=-4..4!0 x1=-5..5!0 b=-9..9!0 f1:=m*x1+b",
         {"text": "A line has slope ${m}$ and passes through $({x1}, {f1})$. Find the $y$-value where it crosses the $y$-axis."}),
        ("evaluate", "({y1}) + {m}*(x - ({x1}))", "{p}", 2, "m=-4..4!0 x1=-4..4 y1=-5..5 p=-5..5 ?p!=x1",
         {"text": "A line with slope ${m}$ passes through $({x1}, {y1})$. Find its $y$-value when $x = {p}$."}),
        ("evaluate", "-1/({m})", None, 2, "m=-6..6!0",
         {"text": "A line has slope ${m}$. Find the slope of a line perpendicular to it."}),
        ("solve", "{m}*x{b:+d} = 0", None, 2, "m=2..6 x0=-6..9!0 b:=-m*x0",
         {"text": "Find the $x$-intercept of the line $y = {m}x{b:+d}$."}),
    ],
    "quadratic_functions": [
        ("evaluate", "-({b})/2", None, 2, "k=-6..6!0 b:=2*k c=-9..9!0",
         {"text": "Find the $x$-coordinate of the vertex of $y = x^2{b:+d}x{c:+d}$."}),
        ("evaluate", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 2, "a=2..3 b=-6..6!0,1,-1 c=-9..9!0 p=-4..5",
         {"text": "A parabola is $y = {a}x^2{b:+d}x{c:+d}$. Find $y$ when $x = {p}$."}),
        ("evaluate", "{b}^2 - 4*{a}*{c}", None, 2, "a=2..3 b=-6..6!0,1,-1 c=-5..5!0",
         {"text": "Find the discriminant of $y = {a}x^2{b:+d}x{c:+d}$."}),
        ("evaluate", "{a}^2", None, 2, "a=2..8 b:=2*a",
         {"text": "The height of a ball is $h = -t^2 + {b}t$. Find its maximum height."}),
        ("factor", "{a}*x^2{b:+d}*x", None, 1, "a=2..5 b=-9..9!0,1,-1"),
    ],
    "power_functions": [
        ("evaluate", "x^(1/2)", "{p}", 1, "p=4,9,16,25,36"),
        ("evaluate", "{a}*x^(1/2)", "{p}", 2, "a=2..6 p=4,9,16,25"),
        ("evaluate", "x^(-1)", "{p}", 1, "p=2..8"),
        ("evaluate", "x^(-3)", "{p}", 2, "p=2..4"),
        ("evaluate", "x^(2/3)", "{p}", 2, "p=8,27,64"),
    ],
    "polynomial_graphs": [
        ("evaluate", "x^3 - {a}*x^2", "{p}", 2, "a=1..4 p=-3..4"),
        ("evaluate", "(x{a:+d})*(x{b:+d})*(x{c:+d})", "{p}", 3, "a=-3..3!0 b=-3..3!0 c=-3..3!0 p=-3..3"),
        ("evaluate", "x^4 - {a}*x^2", "{p}", 3, "a=1..6 p=-3..3"),
        ("factor", "x^3{s:+d}*x^2{p:+d}*x", None, 3, "r=-4..4!0 t=-4..4!0 s:=r+t p:=r*t ?s!=0"),
        ("evaluate", "{a}*x^3 - {b}*x", "{p}", 3, "a=2..4 b=1..6 p=-3..3"),
    ],
    "rational_functions": [
        ("solve", "x{c:+d} = 0", None, 1, "a=1..9 c=-6..6!0",
         {"text": r"Find the vertical asymptote of $f(x) = \frac{{{a}}}{{x{c:+d}}}$ (the value of $x$)."}),
        ("solve", "x - {a} = 0", None, 1, "a=2..9 b=-6..6!0 c=-6..6!0",
         {"text": r"The graph of $f(x) = \frac{{{a}x{b:+d}}}{{x{c:+d}}}$ has a horizontal asymptote $y = k$. Find $k$."}),
        ("evaluate", "1/(x^2{a:+d})", "{p}", 2, "a=1..9 p=-3..3"),
        ("evaluate", "x/(x^2{a:+d})", "{p}", 2, "a=1..9 p=-3..3"),
        ("evaluate", "({a}*x^2)/(x^2{b:+d})", "{p}", 3, "a=2..5 b=1..6 p=-3..3"),
    ],
    "function_composition": [
        ("evaluate", "({b}*({p}){c:+d})^2", None, 2, "b=2..4 p=-3..4 c=-5..5!0",
         {"text": "Let $f(x) = x^2$ and $g(x) = {b}x{c:+d}$. Find $f(g({p}))$."}),
        ("evaluate", "{b}*({p})^2{c:+d}", None, 2, "b=2..4 p=-3..4 c=-5..5!0",
         {"text": "Let $f(x) = x^2$ and $g(x) = {b}x{c:+d}$. Find $g(f({p}))$."}),
        ("expand", "({a}*x{b:+d})^2{c:+d}", None, 3, "a=2..3 b=-4..4!0 c=-5..5!0",
         {"text": "Let $f(x) = x^2{c:+d}$ and $g(x) = {a}x{b:+d}$. Expand $f(g(x))$."}),
        ("evaluate", "sqrt({a}*({p}){b:+d})", None, 3, "s=2..6 a=2..4 p=1..6 b:=s*s-a*p ?b!=0",
         {"text": r"Let $f(x) = \sqrt x$ and $g(x) = {a}x{b:+d}$. Find $f(g({p}))$."}),
        ("evaluate", "{a}*({b}*({p}){c:+d})", None, 2, "a=2..4 b=2..4 p=-3..4 c=-5..5!0",
         {"text": "Let $f(x) = {a}x$ and $g(x) = {b}x{c:+d}$. Find $f(g({p}))$."}),
    ],
    "inverse_functions": [
        ("solve", "{a}*x{b:+d} = {c}", None, 1, "a=2..6 b=-9..9!0 x0=-6..9!0 c:=a*x0+b",
         {"text": r"Let $f(x) = {a}x{b:+d}$. Find $f^{{-1}}({c})$."}),
        ("solve", "x^3{a:+d} = {c}", None, 2, "a=-9..9!0 s=-3..4 c:=s*s*s+a",
         {"text": r"Let $f(x) = x^3{a:+d}$. Find $f^{{-1}}({c})$."}),
        ("solve", "(x{a:+d})/{b} = {c}", None, 2, "b=2..5 c=-5..8 a=-9..9!0",
         {"text": r"Let $f(x) = \frac{{x{a:+d}}}{{{b}}}$. Find $f^{{-1}}({c})$."}),
        ("solve", "sqrt(x) = {a}", None, 1, "a=2..9",
         {"text": r"Let $f(x) = \sqrt x$. Find $f^{{-1}}({a})$."}),
        ("solve", "x/{a}{b:+d} = {c}", None, 2, "a=2..6 b=-9..9!0 k=-5..8 c:=k+b",
         {"text": r"Let $f(x) = \frac{{x}}{{{a}}}{b:+d}$. Find $f^{{-1}}({c})$."}),
    ],
    "exponential_functions": [
        ("evaluate", "{a}*2^x", "{p}", 2, "a=100,200,500 p=1..5",
         {"text": "A population of ${a}$ bacteria doubles every hour. How many are there after ${p}$ hours?"}),
        ("evaluate", "{a}*(1/2)^x", "{p}", 2, "a=80,160,320 p=1..4",
         {"text": "A sample of ${a}$ grams halves every year. How much remains after ${p}$ years?"}),
        ("evaluate", "{b}^x", "{p}", 1, "b=2..5 p=0..4"),
        ("evaluate", "{b}^(-x)", "{p}", 2, "b=2..3 p=1..4"),
        ("evaluate", "{a}*2^(x/2)", "{p}", 2, "a=1..9 k=1..5 p:=2*k"),
    ],
    "logarithms": [
        ("evaluate", "log({v})/log({b})", None, 1, "b=2,3,5,10 n=2..4 v:=b**n",
         {"text": r"Evaluate $\log_{{{b}}} {v}$."}),
        ("evaluate", "log(2)/log({b})", None, 3, "b=4,8,16",
         {"text": r"Evaluate $\log_{{{b}}} 2$."}),
        ("evaluate", "log(1/{v})/log({b})", None, 2, "b=2,3,5 n=1..3 v:=b**n",
         {"text": r"Evaluate $\log_{{{b}}} \frac{{1}}{{{v}}}$."}),
        ("evaluate", "exp(2*ln({a}))", None, 2, "a=2..6"),
        ("evaluate", "exp(3*ln({a}))", None, 3, "a=2..4"),
    ],
    "log_rules": [
        ("evaluate", "log({x})/log(2) + log({y})/log(2)", None, 2, "i=1..4 j=1..4 x:=2**i y:=2**j",
         {"text": r"Evaluate $\log_2 {x} + \log_2 {y}$."}),
        ("evaluate", "log({x})/log(2) - log({y})/log(2)", None, 2, "i=2..6 j=1..4 x:=2**i y:=2**j ?i>j",
         {"text": r"Evaluate $\log_2 {x} - \log_2 {y}$."}),
        ("evaluate", "log({x})/log(10) + log({y})/log(10)", None, 2,
         "t=0..4 x:=[2,4,8,5,25][t] y:=[5,25,125,20,40][t]",
         {"text": r"Evaluate $\log_{{10}} {x} + \log_{{10}} {y}$."}),
        ("evaluate", "log({x})/log(3) + log({y})/log(3)", None, 2, "i=1..3 j=1..3 x:=3**i y:=3**j",
         {"text": r"Evaluate $\log_3 {x} + \log_3 {y}$."}),
        ("evaluate", "{n}*log({b})/log({b})", None, 2, "b=2,3,5 n=2..6",
         {"text": r"Evaluate $\log_{{{b}}} ({b}^{n})$."}),
    ],
    "exp_log_equations": [
        ("solve", "4^x = {c}", None, 2, "k=1..4 c:=4**k"),
        ("solve", "{a}*2^x = {c}", None, 3, "a=2..5 k=1..5 c:=a*2**k"),
        ("solve", "log(x)/log(2) = {a}", None, 2, "a=1..6"),
        ("solve", "log(x)/log(10) = {a}", None, 2, "a=1..4"),
        ("solve", "2^(2*x) = {c}", None, 3, "k=1..4 c:=4**k"),
        ("solve", "10^x = {c}", None, 1, "k=1..5 c:=10**k"),
    ],
})

_TRIPLE = "t=0..3 dx:=[3,5,8,6][t] dy:=[4,12,15,8][t] h:=[5,13,17,10][t]"

_LIM_EXTRA = [
    ("limit", "(x^2 - {q})/(x + {a})", "-{a}", 2, "a=2..9 q:=a*a"),
    ("limit", "(x^2 - {a}*x)/(x - {a})", "{a}", 2, "a=2..9"),
    ("limit", "(2*x^2 - {a}*x)/x", "0", 2, "a=1..9"),
    ("limit", "(x - {a})/(x^2 - {q})", "{a}", 3, "a=2..9 q:=a*a"),
    ("limit", "sqrt(x{a:+d})", "{p}", 1, "s=1..5 a=1..6 p:=s*s-a"),
    ("limit", "({a}*x^2 - {b})/(x{c:+d})", "{p}", 2, "a=1..3 b=1..9 c=-5..5!0 p=-4..4 ?p+c!=0"),
    ("limit", "x^3{b:+d}*x", "{p}", 1, "b=-6..6!0 p=-3..3"),
    ("limit", "({a}*x{b:+d})/({c}*x{d:+d})", "{p}", 2, "a=2..4 b=-5..5!0 c=2..4 d=-5..5!0 p=-3..4 ?c*p+d!=0"),
]

MORE.update({
    "angles_radians": [
        ("evaluate", "{k}*180/{n}", None, 2, "t=0..9 k:=[2,3,5,7,3,5,4,7,5,11][t] n:=[3,4,6,6,2,4,3,4,3,6][t]",
         {"text": r"Convert $\frac{{{k}\pi}}{{{n}}}$ radians to degrees."}),
        ("evaluate", "180/{n}", None, 1, "n=2,3,4,5,6,9,10,12,15,18",
         {"text": r"Convert $\frac{{\pi}}{{{n}}}$ radians to degrees."}),
        ("evaluate", "{d}*pi/180", None, 1, "d=10,20,40,50,70,80,100,110,140,160",
         {"text": "Convert ${d}$ degrees to radians."}),
        ("evaluate", "{r}*pi/{n}", None, 2, "r=2..12 n=2,3,4,6",
         {"text": r"A sector has radius ${r}$ and angle $\frac{{\pi}}{{{n}}}$ radians. Find its arc length."}),
        ("evaluate", "{d}*pi/180", None, 2, "d=15,36,72,225,315,330,150,120",
         {"text": "Convert ${d}$ degrees to radians."}),
    ],
    "unit_circle": [
        ("evaluate", "sin(pi/6) + cos(pi/3)", None, 2, ""),
        ("evaluate", "sin(pi/4)*cos(pi/4)", None, 2, ""),
        ("evaluate", "sin({k}*pi/4)", None, 2, "k=1,3,5,7"),
        ("evaluate", "cos({k}*pi/6)", None, 2, "k=1,2,4,5,7,8,10,11"),
        ("evaluate", "tan({k}*pi/4)", None, 2, "k=1,3,5,7"),
        ("evaluate", "sin({k}*pi) + cos({k}*pi)", None, 2, "k=1..4"),
    ],
    "sin_cos": [
        ("evaluate", "sin(pi/{n})^2", None, 1, "n=2,3,4,6"),
        ("evaluate", "cos(pi/{n})^2 + {a}", None, 2, "n=3,4,6 a=1..5"),
        ("evaluate", "{a}*sin(pi/{n})", None, 1, "a=2..8 n=2,6"),
        ("evaluate", "{a}*cos(pi/{n})", None, 1, "a=2..8 n=3,4"),
        ("evaluate", "sin(pi/{n})*cos(pi/{m})", None, 3, "n=3,6 m=3,6"),
    ],
    "tan_reciprocal": [
        ("evaluate", "tan(pi/{n})^2", None, 2, "n=3,4,6"),
        ("evaluate", "{a}*tan(pi/{n})", None, 2, "n=3,6 a=2..6"),
        ("evaluate", "1/sin(pi/{n})^2", None, 3, "n=3,4,6"),
        ("evaluate", "tan(pi/3)*tan(pi/6)", None, 2, ""),
        ("evaluate", "sin(pi/{n})/cos(pi/{n})", None, 2, "n=3,4,6"),
    ],
    "right_triangle": [
        ("evaluate", "sqrt({dx}^2 + {dy}^2)", None, 1, _TRIPLE,
         {"text": "A right triangle has legs ${dx}$ and ${dy}$. Find the hypotenuse."}),
        ("evaluate", "{dy}/{dx}", None, 2, _TRIPLE,
         {"text": "A right triangle has legs ${dx}$ and ${dy}$. Find the tangent of the angle opposite the leg of length ${dy}$."}),
        ("evaluate", "{h}*sin(pi/6)", None, 2, "h=2..12",
         {"text": "A right triangle has hypotenuse ${h}$ and an angle of 30 degrees. Find the side opposite that angle."}),
        ("evaluate", "{h}*cos(pi/3)", None, 2, "h=2..12",
         {"text": "A right triangle has hypotenuse ${h}$ and an angle of 60 degrees. Find the side next to that angle."}),
        ("evaluate", "{h}*sin(pi/3)", None, 3, "h=2..12",
         {"text": "A right triangle has hypotenuse ${h}$ and an angle of 60 degrees. Find the side opposite that angle."}),
    ],
    "trig_graphs": [
        ("evaluate", "2*pi/{b}", None, 2, "b=2..6", {"text": r"Find the period of $y = \sin({b}x)$."}),
        ("evaluate", "{a}*sin(x)", "{k}*pi/2", 2, "a=2..6 k=1,3,5"),
        ("evaluate", "{a}*cos(x)", "{k}*pi", 2, "a=2..6 k=0..3"),
        ("evaluate", "{a}*sin(2*x)", "pi/4", 2, "a=2..6"),
        ("evaluate", "2*pi/{b}", None, 2, "b=3..8", {"text": r"Find the period of $y = \cos({b}x)$."}),
    ],
    "tangent_graph": [
        ("evaluate", "tan(x)", "pi/{n}", 2, "n=3,4,6"),
        ("evaluate", "{a}*tan(x)", "pi/{n}", 2, "a=2..5 n=3,4,6"),
        ("evaluate", "tan(2*x)", "pi/{n}", 3, "n=6,8,12"),
        ("evaluate", "tan(x) - {a}", "pi/4", 2, "a=2..6"),
        ("evaluate", "pi/{b}", None, 3, "b=2..6", {"text": r"Find the period of $y = \tan({b}x)$."}),
    ],
    "inverse_trig": [
        ("evaluate", "asin(sin(pi/{n}))", None, 2, "n=3,4,6"),
        ("evaluate", "acos(cos(pi/{n}))", None, 2, "n=3,4,6"),
        ("evaluate", "atan(tan(pi/{n}))", None, 2, "n=3,4,6"),
        ("evaluate", "cos(asin({v}))", None, 3, "t=0..3 v:=['0','1/2','sqrt(2)/2','1'][t]"),
        ("evaluate", "{a}*acos(0)", None, 2, "a=2..6"),
    ],
    "trig_identities": [
        ("simplify", "1 - cos(x)^2", None, 2, ""),
        ("simplify", "sin(x)^2 + cos(x)^2 + {a}", None, 2, "a=1..9"),
        ("simplify", "1/cos(x)^2 - tan(x)^2", None, 3, ""),
        ("simplify", "(1 + tan(x)^2)*cos(x)^2", None, 3, ""),
        ("simplify", "(1 - sin(x)^2)/cos(x)", None, 2, ""),
        ("simplify", "cos(x)/sin(x)*tan(x)", None, 2, ""),
    ],
    "angle_sum": [
        ("evaluate", "cos(pi/{a} + pi/{b})", None, 3, "a=3,4,6 b=3,4,6 ?a!=b"),
        ("evaluate", "sin(pi/{a} - pi/{b})", None, 3, "a=3,4 b=4,6 ?a!=b"),
        ("evaluate", "sin(pi/{a})*cos(pi/{b}) + cos(pi/{a})*sin(pi/{b})", None, 3, "a=3,4,6 b=3,4,6 ?a!=b"),
        ("evaluate", "cos(pi/{a})*cos(pi/{b}) - sin(pi/{a})*sin(pi/{b})", None, 3, "a=3,4,6 b=3,4,6 ?a!=b"),
        ("evaluate", "sin(pi/2 + pi/{n})", None, 2, "n=3,4,6"),
    ],
    "double_angle": [
        ("evaluate", "sin(2*pi/{n})", None, 2, "n=3,4,6,12"),
        ("evaluate", "cos(2*pi/{n})", None, 2, "n=3,4,6,8"),
        ("evaluate", "2*cos(pi/{n})^2 - 1", None, 2, "n=3,4,6,12"),
        ("evaluate", "sin(pi/{n})*cos(pi/{n})", None, 2, "n=3,4,6"),
        ("evaluate", "2*sin(pi/12)*cos(pi/12)", None, 2, ""),
        ("evaluate", "tan(2*pi/{n})", None, 3, "n=6,12"),
    ],
    "limits": _LIM_EXTRA[:6],
    "one_sided_limits": _LIM_EXTRA[2:8],
    "limit_laws": _LIM_EXTRA[4:8] + [
        ("limit", "({a}*x{b:+d})*({c}*x{d:+d})", "{p}", 2, "a=2..4 b=-5..5!0 c=2..4 d=-5..5!0 p=-3..4"),
        ("limit", "{a}*sqrt(x{b:+d}) + {c}*x", "{p}", 2, "s=1..5 a=2..4 b=1..6 c=1..4 p:=s*s-b"),
    ],
    "limit_simplification": _LIM_EXTRA[:4] + [
        ("limit", "(x^2{s:+d}*x{p:+d})/(x{r:+d})", "{nr}", 2, "r=1..6 t=1..6 s:=r+t p:=r*t nr:=-r"),
        ("limit", "(x^2 - {q})/(x - {a})", "{a}", 2, "a=-9..-2 q:=a*a"),
    ],
    "continuity": _LIM_EXTRA[3:8] + [
        ("limit", "({a}*x^2{b:+d})", "{p}", 1, "a=2..4 b=-9..9!0 p=-3..4"),
        ("limit", "x^2*({a}*x{b:+d})", "{p}", 2, "a=2..4 b=-5..5!0 p=-3..4"),
    ],
    "derivative_definition": [
        ("differentiate", "{a}*x^2{b:+d}", "{p}", 1, "a=1..4 b=-9..9!0 p=-4..5"),
        ("differentiate", "{a}*x^3", "{p}", 2, "a=1..4 p=-3..3"),
        ("differentiate", "{a}*x^2 - {b}*x + {c}", "{p}", 2, "a=1..4 b=1..6 c=1..9 p=-3..4"),
        ("differentiate", "1/x", None, 2, ""),
        ("differentiate", "x^2", None, 1, ""),
        ("differentiate", "x^3 - {a}", None, 1, "a=1..9"),
    ],
    "derivative_function": [
        ("differentiate", "{a}*x^5{b:+d}*x^3", None, 2, "a=1..4 b=-6..6!0"),
        ("differentiate", "x^{n}/{n}", None, 2, "n=2..6"),
        ("differentiate", "{a}*x^2 + {b}*x^3", None, 2, "a=2..6 b=1..4"),
        ("differentiate", "{a}/x^2", None, 2, "a=1..6"),
        ("differentiate", "{a}*sqrt(x)", None, 2, "a=2..8"),
        ("differentiate", "{a} - {b}*x^2", None, 1, "a=1..9 b=2..6"),
    ],
    "derivative_rules": [
        ("differentiate", "sin(x){a:+d}*x^2", None, 2, "a=-5..5!0"),
        ("differentiate", "exp(x){a:+d}*x", None, 2, "a=-6..6!0"),
        ("differentiate", "ln(x){a:+d}*x^3", None, 2, "a=-5..5!0"),
        ("differentiate", "{a}*sin(x) - {b}*cos(x)", None, 2, "a=1..6 b=1..6"),
        ("differentiate", "{a}*exp(x) + {b}*x^2", None, 2, "a=2..6 b=1..6"),
    ],
    "product_rule": [
        ("differentiate", "x^{n}*sin(x)", None, 2, "n=2..4"),
        ("differentiate", "{a}*x*exp(x)", None, 2, "a=2..5"),
        ("differentiate", "(x{a:+d})*(x^2{b:+d})", None, 2, "a=-4..4!0 b=-4..4!0"),
        ("differentiate", "x*cos(x)", None, 2, ""),
        ("differentiate", "exp(x)*sin(x)", None, 3, ""),
        ("differentiate", "x^2*ln(x)", None, 3, ""),
        ("differentiate", "(x^2{a:+d})*exp(x)", None, 3, "a=-4..4!0"),
    ],
    "quotient_rule": [
        ("differentiate", "(x{a:+d})/(x{b:+d})", None, 2, "a=-5..5!0 b=-5..5!0 ?a!=b"),
        ("differentiate", "1/(x{a:+d})", None, 2, "a=-6..6!0"),
        ("differentiate", "x/(x^2{a:+d})", None, 3, "a=1..6"),
        ("differentiate", "(x^2{a:+d})/x", None, 2, "a=-6..6!0"),
        ("differentiate", "exp(x)/(x{a:+d})", None, 3, "a=-5..5!0"),
        ("differentiate", "cos(x)/x", None, 3, ""),
    ],
    "trig_derivatives": [
        ("differentiate", "{a}*sin(x) + {b}*cos(x)", None, 1, "a=2..6 b=2..6"),
        ("differentiate", "sin(x){a:+d}*x", None, 1, "a=-6..6!0"),
        ("differentiate", "cos(x)", None, 1, ""),
        ("differentiate", "{a}*tan(x)", None, 2, "a=2..6"),
        ("differentiate", "sin(x)^2", None, 3, ""),
        ("differentiate", "1/cos(x)", None, 3, ""),
    ],
    "chain_rule": [
        ("differentiate", "(x^2{a:+d})^{n}", None, 2, "a=-5..5!0 n=3..5"),
        ("differentiate", "sin({a}*x{b:+d})", None, 2, "a=2..5 b=-4..4!0"),
        ("differentiate", "exp({a}*x^2)", None, 3, "a=1..4"),
        ("differentiate", "cos({a}*x)", None, 2, "a=2..6"),
        ("differentiate", "(x{a:+d})^{n}", None, 1, "a=-6..6!0 n=3..7"),
        ("differentiate", "ln(x^2{a:+d})", None, 3, "a=1..6"),
    ],
    "nested_chain_rule": [
        ("differentiate", "exp(cos(x))", None, 3, ""),
        ("differentiate", "sin(exp(x))", None, 3, ""),
        ("differentiate", "ln(sin(x))", None, 3, ""),
        ("differentiate", "cos(sin(x))", None, 3, ""),
        ("differentiate", "(sin(x){a:+d})^{n}", None, 3, "a=1..5 n=2..4"),
    ],
    "exp_log_derivatives": [
        ("differentiate", "{a}*exp(x)", None, 1, "a=2..9"),
        ("differentiate", "exp(-x)", None, 2, ""),
        ("differentiate", "x^2*exp(x)", None, 3, ""),
        ("differentiate", "exp(x) + ln(x)", None, 2, ""),
        ("differentiate", "{a}*ln(x) + x^2", None, 2, "a=2..8"),
        ("differentiate", "exp({a}*x) + {b}*x", None, 2, "a=2..5 b=2..9"),
    ],
    "inverse_derivatives": [
        ("differentiate", "x^(1/2)", None, 2, ""),
        ("differentiate", "x^(2/3)", None, 2, ""),
        ("differentiate", "x^(-1/2)", None, 2, ""),
        ("differentiate", "{a}*x^(1/3)", None, 2, "a=2..9"),
        ("differentiate", "1/x^3", None, 2, ""),
    ],
    "inverse_trig_derivatives": [
        ("differentiate", "{a}*asin(x)", None, 2, "a=2..6"),
        ("differentiate", "atan(x^2)", None, 3, ""),
        ("differentiate", "{a}*atan(x)", None, 2, "a=2..6"),
        ("differentiate", "atan(x) + x", None, 2, ""),
        ("differentiate", "acos({a}*x)", None, 3, "a=2..4"),
        ("differentiate", "asin(x^2)", None, 3, ""),
    ],
    "higher_derivatives": [
        ("differentiate", "{a}*x^5{b:+d}*x^2", None, 2, "a=1..3 b=-6..6!0", {"order": 3}),
        ("differentiate", "cos({a}*x)", None, 2, "a=2..4", {"order": 2}),
        ("differentiate", "x^{n}", None, 1, "n=3..7", {"order": 2}),
        ("differentiate", "x*exp(x)", None, 3, "", {"order": 2}),
        ("differentiate", "sin(x)", None, 2, "", {"order": 3}),
        ("differentiate", "{a}*x^3{b:+d}*x", None, 2, "a=1..4 b=-6..6!0", {"order": 3}),
    ],
    "tangent_line": [
        ("differentiate", "{a}*x^2{b:+d}*x{c:+d}", "{p}", 2, "a=2..4 b=-6..6!0,1,-1 c=-9..9!0 p=-3..4",
         {"text": "Find the slope of the tangent line to $y = {a}x^2{b:+d}x{c:+d}$ at $x = {p}$."}),
        ("differentiate", "x^3{b:+d}*x", "{p}", 2, "b=-9..9!0,1,-1 p=-3..3",
         {"text": "Find the slope of the tangent line to $y = x^3{b:+d}x$ at $x = {p}$."}),
        ("differentiate", "sqrt(x)", "{p}", 2, "p=1,4,9,16",
         {"text": r"Find the slope of the tangent line to $y = \sqrt x$ at $x = {p}$."}),
        ("differentiate", "1/x", "{p}", 2, "p=1..5",
         {"text": r"Find the slope of the tangent line to $y = \frac{{1}}{{x}}$ at $x = {p}$."}),
        ("differentiate", "x^4 - {a}*x", "{p}", 2, "a=1..8 p=-2..3"),
        ("differentiate", "{a}*x^2", "{p}", 1, "a=2..5 p=-4..5",
         {"text": "Find the slope of the tangent line to $y = {a}x^2$ at $x = {p}$."}),
    ],
    "rates_of_change": [
        ("differentiate", "{a}*x^2", "{p}", 1, "a=2..6 p=1..8",
         {"text": "The distance travelled is $s = {a}t^2$ metres after $t$ seconds. Find the speed $s'(t)$ at $t = {p}$."}),
        ("differentiate", "-x^2 + {a}*x", "{p}", 2, "a=4..12 p=0..6",
         {"text": "A ball's height is $h = -t^2 + {a}t$. Find its vertical speed $h'(t)$ at $t = {p}$."}),
        ("differentiate", "{a}*x^3", "{p}", 2, "a=1..4 p=1..4",
         {"text": "The volume of a growing tank is $V = {a}t^3$. Find $V'(t)$, how fast it changes, at $t = {p}$."}),
        ("differentiate", "x^2{b:+d}*x", "{p}", 2, "b=-9..9!0,1,-1 p=1..6",
         {"text": "A population is $P(t) = t^2{b:+d}t$. Find the rate of change $P'(t)$ at $t = {p}$."}),
        ("differentiate", "100 - {a}*x^2", "{p}", 2, "a=2..6 p=1..5",
         {"text": "The amount of water in a tank is $W = 100 - {a}t^2$. Find $W'(t)$ at $t = {p}$."}),
        ("differentiate", "{a}*x^2 + {b}*x + {c}", "{p}", 2, "a=1..4 b=2..9 c=10..50 p=1..8",
         {"text": "The cost of making $x$ items is $C = {a}x^2 + {b}x + {c}$. Find the marginal cost $C'(x)$ at $x = {p}$."}),
    ],
})


for _topic, _extra in MORE.items():
    TEMPLATES[_topic] = list(TEMPLATES.get(_topic, [])) + list(_extra)
