from app.semantic.analyzer import analyze_node
from app.semantic.visualize import build_visualization


def _cat(content: str) -> str | None:
    spec = build_visualization(content)
    return spec.category if spec else None


def test_polynomial_2d():
    spec = build_visualization("y = x^2")
    assert spec is not None
    assert spec.category == "polynomial"
    assert spec.plot_type == "2d"
    assert spec.function == "x^2"
    assert "x" in spec.variables


def test_polynomial_with_parameter():
    spec = build_visualization("y = ax^2 + bx + c")
    assert spec is not None
    assert spec.category == "polynomial"
    names = {p.name for p in spec.parameters}
    assert names == {"a", "b", "c"}
    assert spec.level == 2


def test_wave_animated():
    spec = build_visualization("y = sin(omega*t)")
    assert spec is not None
    assert spec.category == "wave"
    assert spec.animated
    assert spec.animation == "t"
    assert spec.level == 3


def test_unicode_superscript_normalized():
    spec = build_visualization("y = x² + 2x + 1")
    assert spec is not None
    assert spec.function == "x^2 + 2*x + 1" or "x^2" in spec.function


def test_surface_3d():
    spec = build_visualization("z = x^2 + y^2")
    assert spec is not None
    assert spec.category == "surface"
    assert spec.plot_type == "3d"
    assert set(spec.variables) == {"x", "y"}


def test_sphere_3d():
    spec = build_visualization("x^2 + y^2 + z^2 = r^2")
    assert spec is not None
    assert spec.category == "sphere"
    assert spec.plot_type == "3d"
    assert spec.animated


def test_circle_2d():
    spec = build_visualization("x^2 + y^2 = r^2")
    assert spec is not None
    assert spec.category == "circle"


def test_bloch_sphere():
    spec = build_visualization("|ψ⟩ = α|0⟩ + β|1⟩")
    assert spec is not None
    assert spec.category == "bloch"
    assert spec.animated


def test_hadamard_gate():
    spec = build_visualization("H|0⟩")
    assert spec is not None
    assert spec.category == "gate"


def test_entanglement():
    spec = build_visualization("|00⟩ + |11⟩")
    assert spec is not None
    assert spec.category == "entanglement"


def test_ohm_circuit():
    spec = build_visualization("V = IR")
    assert spec is not None
    assert spec.category == "circuit"
    assert spec.extra.get("mode") == "circuit"


def test_newton_dynamics():
    spec = build_visualization("F = ma")
    assert spec is not None
    assert spec.category == "dynamics"
    assert spec.level == 4


def test_energy():
    spec = build_visualization("E = mc^2")
    assert spec is not None
    assert spec.category == "energy"


def test_normal_distribution():
    spec = build_visualization("Normal(0, 1)")
    assert spec is not None
    assert spec.category == "normal"
    assert {p.name for p in spec.parameters} == {"mean", "sigma"}


def test_probability_tree():
    spec = build_visualization("P(A|B)")
    assert spec is not None
    assert spec.category == "probability"


def test_euler_identity():
    spec = build_visualization("e^(iπ)+1=0")
    assert spec is not None
    assert spec.category == "euler"


def test_generic_formula():
    spec = build_visualization("v = u + at")
    assert spec is not None
    assert spec.category == "physics"
    assert spec.extra.get("mode") == "formula"
    assert spec.extra.get("output") == "v"


def test_algebra_equation():
    spec = build_visualization("x^2 = 4")
    assert spec is not None
    assert spec.category == "algebra"


def test_plain_prose_yields_no_viz():
    assert build_visualization("Quantum Computing relies on qubits and entanglement.") is None
    assert build_visualization("A qubit can be in a superposition of |0⟩ and |1⟩.") is None
    assert build_visualization("Hello world.") is None


def test_analyze_response_embeds_visualization():
    profile = analyze_node("n1", "formula", "y = x^2", {})
    assert profile.visualization is not None
    assert profile.visualization.category == "polynomial"

    profile = analyze_node("n2", "text", "Just some notes about the weather.", {})
    assert profile.visualization is None
