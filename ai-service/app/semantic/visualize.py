"""Deterministic equation classification and visualization specs.

Turns a hand-typed math/physics/quantum/statistics expression into a
``VisualizationSpec`` that the frontend HUD can render (2D plots, 3D
surfaces, Bloch spheres, circuits, bell curves, ...).

Pipeline: normalize unicode -> detect category (quantum / physics law /
statistics / sphere / circle / cone / surface / plane) -> build spec with
variables, interactive parameters, ranges and animation flags.
"""

import re

import sympy as sp

from ..schemas import ParamSpec, VisualizationSpec

FUNCTION_RE = re.compile(
    r"\b(sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|log|ln|exp|sqrt|abs|min|max|floor|ceil|round|sign|sec|csc|cot|sum|integral|derivative|diff|lim)\b",
    re.I,
)
GREEK_RE = re.compile(r"[α-ωΑ-Ωπ∂∑∫√∞θλμϕφψΨΔ]")

_FUNCTIONS = {
    "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
    "log", "ln", "exp", "sqrt", "abs", "min", "max", "floor", "ceil",
    "round", "sign", "sec", "csc", "cot", "sum", "integral", "derivative",
    "diff", "lim", "mod", "log2", "log10",
}
_CONSTANTS = {"e", "i", "pi", "tau", "inf", "Infinity", "nan", "true", "false", "phi"}
_NAMED_PARAMS = {
    "alpha", "beta", "gamma", "lambda", "sigma", "mu", "theta", "omega",
    "phi", "psi", "Psi", "Delta", "delta", "nabla", "partial",
}

_SUPERSCRIPT_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_UNICODE_MAP = {
    "√": "sqrt",
    "π": "pi",
    "τ": "tau",
    "×": "*",
    "⋅": "*",
    "∙": "*",
    "÷": "/",
    "−": "-",
    "∞": "Infinity",
    "θ": "theta",
    "ω": "w",
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "λ": "lambda",
    "σ": "sigma",
    "μ": "mu",
    "φ": "phi",
    "ϕ": "phi",
    "ψ": "psi",
    "Ψ": "Psi",
    "Δ": "Delta",
    "∇": "nabla",
    "∂": "partial",
    "½": "0.5",
    "⅓": "1/3",
    "⅔": "2/3",
    "¼": "0.25",
    "¾": "0.75",
}

_KET_RE = re.compile(r"\|[^|]*[⟩>]")
_ENTANGLE_RE = re.compile(r"\|\s*[01][01]\s*[⟩>]")
_GATE_RE = re.compile(r"\b[Hh]\s*\|\s*0\s*[⟩>]|\bhadamard\b")
_SUPER_RE = re.compile(r"\|\s*[01]\s*[⟩>]\s*\+")
_BLOCH_RE = re.compile(r"[ψΨ]|[αβ]\s*\||\bbloch\b", re.I)

_NORMAL_RE = re.compile(
    r"\b(?:normal|gaussian|bell\s*curve)\b|gaussian|normal distribution|N\s*\([^)]*\s*,\s*[^)]*\)",
    re.I,
)
_PROB_RE = re.compile(r"\bP\s*\(\s*[^)]*\|\s*[^)]*\)")

_PHYSICS_LAWS = {
    "v=ir": (
        "circuit",
        "Circuit · Ohm's law",
        [ParamSpec(name="V", default=12.0, min=1.0, max=24.0, step=0.5),
         ParamSpec(name="R", default=6.0, min=0.5, max=24.0, step=0.5)],
    ),
    "f=ma": (
        "dynamics",
        "Dynamics · Newton's second law",
        [ParamSpec(name="F", default=10.0, min=1.0, max=100.0, step=1.0),
         ParamSpec(name="m", default=2.0, min=0.5, max=20.0, step=0.5)],
    ),
    "e=mc2": (
        "energy",
        "Energy · E = mc²",
        [ParamSpec(name="m", default=1.0, min=0.1, max=10.0, step=0.1)],
    ),
    "p=mv": (
        "momentum",
        "Momentum · p = mv",
        [ParamSpec(name="m", default=2.0, min=0.5, max=10.0, step=0.5),
         ParamSpec(name="v", default=3.0, min=1.0, max=30.0, step=0.5)],
    ),
}

_SPHERE_RE = re.compile(r"x2\s*\+\s*y2\s*\+\s*z2\s*=\s*(?:r2|[0-9.]+)")
_CIRCLE_RE = re.compile(r"(?:x2\s*\+\s*y2\s*=\s*(?:r2|[0-9.]+|[a-zA-Z][a-zA-Z0-9]*)\s*$)")
_CONE_RE = re.compile(r"z\^2\s*=\s*x\^2\s*\+\s*y\^2")
_EULER_RE = re.compile(r"\+\s*1\s*=\s*0")
_SURFACE_RE = re.compile(r"^\s*[zZ]\s*=\s*(.+)$")


def normalize_math(text: str) -> str:
    text = re.sub(
        rf"[{_SUPERSCRIPT_CHARS}]+",
        lambda m: "^" + "".join(str(_SUPERSCRIPT_CHARS.index(c)) for c in m.group(0)),
        text,
    )
    text = "".join(_UNICODE_MAP.get(ch, ch) for ch in text)
    text = text.replace("**", "^")
    return re.sub(r"\s+", " ", text).strip()


def _looks_math(text: str) -> bool:
    if "=" in text:
        return True
    if FUNCTION_RE.search(text):
        return True
    if any(ch in text for ch in "+-*/^∫∑√π×÷∂"):
        return True
    return bool(GREEK_RE.search(text))


def _free_vars(fn: str) -> set[str]:
    vars_: set[str] = set()
    for token in re.findall(r"[A-Za-z][A-Za-z0-9]*", fn):
        if token in _FUNCTIONS or token in _CONSTANTS:
            continue
        if token in _NAMED_PARAMS or len(token) == 1:
            vars_.add(token)
        else:
            vars_.update(token)
    return vars_


def _implicit_mult(fn: str) -> str:
    """Turn 'ax^2 + 2x' into 'a*x^2 + 2*x' so sympy/mathjs can parse it."""
    parts: list[str] = []
    for token in re.split(r"([^a-zA-Z]+)", fn):
        if token.isalpha() and len(token) > 1:
            if token in _FUNCTIONS or token in _CONSTANTS or token in _NAMED_PARAMS:
                parts.append(token)
            else:
                parts.append("*".join(token))
        else:
            parts.append(token)
    return "".join(parts)


def _param_specs(fn: str, vars_: set[str], exclude_t: bool = True) -> list[ParamSpec]:
    excluded = {"x", "y", "z"}
    if exclude_t:
        excluded.add("t")
    params = sorted(vars_ - excluded)
    return [ParamSpec(name=p, default=1.0, min=-5.0, max=5.0, step=0.1) for p in params]


def _quantum_spec(raw: str) -> VisualizationSpec | None:
    has_psi = "ψ" in raw or "Ψ" in raw
    has_ket = bool(_KET_RE.search(raw))
    if not (has_psi or has_ket):
        return None

    if _ENTANGLE_RE.search(raw):
        return VisualizationSpec(
            category="entanglement",
            plot_type="special",
            expression=raw,
            animated=True,
            level=3,
            title="Entangled qubits",
            subtitle="|00⟩ + |11⟩ · non-separable state",
            extra={"mode": "entanglement"},
        )
    if has_psi or _BLOCH_RE.search(raw):
        return VisualizationSpec(
            category="bloch",
            plot_type="special",
            expression=raw,
            parameters=[
                ParamSpec(name="alpha", default=0.707, min=0.0, max=1.0, step=0.05),
                ParamSpec(name="beta", default=0.707, min=0.0, max=1.0, step=0.05),
            ],
            animated=True,
            level=3,
            title="Bloch sphere",
            subtitle="|ψ⟩ = α|0⟩ + β|1⟩",
            extra={"mode": "bloch"},
        )
    if _GATE_RE.search(raw):
        return VisualizationSpec(
            category="gate",
            plot_type="special",
            expression=raw,
            animated=True,
            level=3,
            title="Quantum gate",
            subtitle="H|0⟩ → |+⟩",
            extra={"mode": "gate", "gate": "H"},
        )
    if _SUPER_RE.search(raw):
        return VisualizationSpec(
            category="bloch",
            plot_type="special",
            expression=raw,
            parameters=[
                ParamSpec(name="alpha", default=0.707, min=0.0, max=1.0, step=0.05),
                ParamSpec(name="beta", default=0.707, min=0.0, max=1.0, step=0.05),
            ],
            animated=True,
            level=3,
            title="Superposition state",
            subtitle="|0⟩ + |1⟩",
            extra={"mode": "bloch"},
        )
    return None


def _physics_law(text: str) -> VisualizationSpec | None:
    compact = re.sub(r"[\s*^_]", "", text.lower())
    law = _PHYSICS_LAWS.get(compact)
    if not law:
        return None
    category, title, params = law
    levels = {"circuit": 2, "dynamics": 4, "energy": 2, "momentum": 2}
    return VisualizationSpec(
        category=category,
        plot_type="special",
        expression=text,
        variables=["V"] if category == "circuit" else [],
        parameters=params,
        animated=category == "dynamics",
        level=levels.get(category, 2),
        title=title,
        extra={"mode": category},
    )


def _normal_spec(text: str) -> VisualizationSpec | None:
    m = re.search(r"(?:normal|gaussian|N)\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)", text, re.I)
    mean = 0.0
    sigma = 1.0
    if m:
        try:
            mean = float(m.group(1).strip())
        except ValueError:
            pass
        try:
            sigma = float(m.group(2).strip())
        except ValueError:
            pass
    sigma = max(0.05, sigma)
    return VisualizationSpec(
        category="normal",
        plot_type="2d",
        expression=text,
        function="1/(sigma*sqrt(2*pi))*exp(-0.5*((x-mean)/sigma)^2)",
        variables=["x"],
        parameters=[
            ParamSpec(name="mean", default=mean, min=-10.0, max=10.0, step=0.1),
            ParamSpec(name="sigma", default=sigma, min=0.05, max=5.0, step=0.05),
        ],
        ranges={"x": [mean - 4 * sigma, mean + 4 * sigma], "y": [0.0, 0.5]},
        level=2,
        title="Normal distribution",
        subtitle=f"μ = {mean:g}, σ = {sigma:g}",
    )


def _probability_spec(text: str) -> VisualizationSpec:
    return VisualizationSpec(
        category="probability",
        plot_type="special",
        expression=text,
        parameters=[ParamSpec(name="P_B_given_A", default=0.7, min=0.0, max=1.0, step=0.05)],
        level=2,
        title="Probability tree",
        subtitle="P(A|B) via Bayes' rule",
        extra={"mode": "tree"},
    )


def _sphere_spec(text: str) -> VisualizationSpec:
    return VisualizationSpec(
        category="sphere",
        plot_type="3d",
        expression=text,
        variables=["x", "y", "z"],
        parameters=[ParamSpec(name="r", default=1.0, min=0.1, max=5.0, step=0.1)],
        ranges={"x": [-3, 3], "y": [-3, 3], "z": [-3, 3]},
        animated=True,
        level=2,
        title="3D sphere",
        subtitle="x² + y² + z² = r²",
        extra={"mode": "sphere"},
    )


def _circle_spec(text: str) -> VisualizationSpec:
    return VisualizationSpec(
        category="circle",
        plot_type="2d",
        expression=text,
        function="x^2 + y^2 - r^2",
        variables=["x", "y"],
        parameters=[ParamSpec(name="r", default=1.0, min=0.1, max=5.0, step=0.1)],
        ranges={"x": [-5, 5], "y": [-5, 5]},
        level=2,
        title="Circle",
        subtitle="x² + y² = r²",
    )


def _cone_spec(text: str) -> VisualizationSpec:
    return VisualizationSpec(
        category="cone",
        plot_type="3d",
        expression=text,
        variables=["x", "y", "z"],
        parameters=[ParamSpec(name="r", default=1.0, min=0.1, max=5.0, step=0.1)],
        ranges={"x": [-3, 3], "y": [-3, 3], "z": [-3, 3]},
        animated=True,
        level=2,
        title="Cone",
        subtitle="z² = x² + y²",
        extra={"mode": "cone"},
    )


def _surface_spec(expression: str, fn: str) -> VisualizationSpec | None:
    fn = _implicit_mult(fn.strip())
    vars_ = _free_vars(fn)
    if not (vars_ & {"x", "y"}):
        return None
    params = _param_specs(fn, vars_)
    return VisualizationSpec(
        category="surface",
        plot_type="3d",
        expression=expression,
        function=fn,
        variables=sorted(vars_ & {"x", "y"}),
        parameters=params,
        ranges={"x": [-5, 5], "y": [-5, 5], "z": [-5, 5]},
        level=2 if params else 1,
        title="3D surface",
        subtitle=f"z = {fn[:40]}",
    )


def _function_spec(expression: str, fn: str, vars_: set[str], algebra: bool = False) -> VisualizationSpec | None:
    fn = _implicit_mult(fn)
    primary = "x" if "x" in vars_ else ("t" if "t" in vars_ else None)
    if primary is None and len(vars_) != 1:
        return None
    if primary is None:
        primary = sorted(vars_)[0]
    if primary not in ("x", "t"):
        return None

    is_trig = bool(re.search(r"\b(sin|cos|tan)\b", fn, re.I))
    animated = is_trig and ("t" in vars_ or "x" in vars_)
    params = _param_specs(fn, vars_)

    category = "algebra" if algebra else "general"
    if not algebra and primary == "x":
        try:
            x = sp.Symbol("x")
            poly = sp.Poly(sp.sympify(fn), x)
            if poly.degree() >= 1:
                category = "polynomial"
                degree = poly.degree()
        except Exception:
            pass
    if is_trig and not algebra:
        category = "wave"

    level = 3 if animated else (2 if params else 1)
    title = {
        "polynomial": "Polynomial plot",
        "wave": "Wave plot",
        "algebra": "Algebra equation",
        "general": "2D function",
    }.get(category, "2D plot")

    return VisualizationSpec(
        category=category,
        plot_type="2d",
        expression=expression,
        function=fn,
        variables=sorted(vars_),
        parameters=params,
        ranges={"x": [-10, 10], "y": [-10, 10]},
        animated=animated,
        animation="t" if animated else None,
        level=level,
        title=title,
        subtitle=f"y = {fn[:40]}" if not algebra else fn[:40],
    )


def _plane_spec(text: str) -> VisualizationSpec | None:
    if "=" in text:
        lhs, _, rhs = text.partition("=")
        lhs = lhs.strip()
        rhs = rhs.strip()
        if not lhs or not rhs:
            return None
        if re.fullmatch(r"[yY]", lhs):
            fn = rhs
            vars_ = _free_vars(fn)
            if not vars_:
                return None
            return _function_spec(text, fn, vars_)
        if re.fullmatch(r"[fF]\s*\([^)]*\)", lhs):
            fn = rhs
            vars_ = _free_vars(fn)
            if not vars_:
                return None
            return _function_spec(text, fn, vars_)
        vars_ = _free_vars(text)
        if vars_ and vars_ <= {"x", "t"}:
            return _function_spec(text, f"({lhs}) - ({rhs})", vars_, algebra=True)
        return None

    fn = text
    vars_ = _free_vars(fn)
    if not vars_:
        return None
    if "x" not in vars_ and "t" not in vars_ and len(vars_) != 1:
        return None
    return _function_spec(text, fn, vars_)


def _generic_formula(text: str) -> VisualizationSpec | None:
    if "=" not in text:
        return None
    lhs, _, rhs = text.partition("=")
    lhs = lhs.strip()
    rhs = rhs.strip()
    if not re.fullmatch(r"[A-Za-z]", lhs):
        return None
    if lhs in ("x", "y", "z", "t"):
        return None
    rhs = _implicit_mult(rhs)
    rhs_vars = _free_vars(rhs)
    if not rhs_vars:
        return None
    params = _param_specs(rhs, rhs_vars, exclude_t=False)
    if not params:
        return None
    return VisualizationSpec(
        category="physics",
        plot_type="special",
        expression=text,
        function=rhs,
        variables=sorted(rhs_vars),
        parameters=params,
        level=2,
        title="Interactive formula",
        subtitle=f"{lhs} = {rhs[:40]}",
        extra={"mode": "formula", "output": lhs},
    )


def build_visualization(content) -> VisualizationSpec | None:
    if content is None:
        return None
    raw = str(content).strip()
    if not raw:
        return None

    qspec = _quantum_spec(raw)
    if qspec:
        return qspec

    text = normalize_math(raw)
    if not text:
        return None

    law = _physics_law(text)
    if law:
        return law

    if _NORMAL_RE.search(raw) or _NORMAL_RE.search(text):
        return _normal_spec(text)
    if _PROB_RE.search(raw):
        return _probability_spec(text)

    if _EULER_RE.search(text) and "pi" in text:
        return VisualizationSpec(
            category="euler",
            plot_type="special",
            expression=text,
            animated=True,
            level=3,
            title="Euler's identity",
            subtitle="e^(iπ) + 1 = 0",
            extra={"mode": "euler"},
        )

    if not _looks_math(text):
        return None

    compact = re.sub(r"[\s*^_]", "", text.lower())
    if _SPHERE_RE.search(compact):
        return _sphere_spec(text)
    if _CIRCLE_RE.search(compact):
        return _circle_spec(text)
    if _CONE_RE.search(text):
        return _cone_spec(text)

    m = _SURFACE_RE.match(text)
    if m:
        spec = _surface_spec(text, m.group(1).strip())
        if spec:
            return spec

    spec = _plane_spec(text)
    if spec:
        return spec

    spec = _generic_formula(text)
    if spec:
        return spec

    return None
