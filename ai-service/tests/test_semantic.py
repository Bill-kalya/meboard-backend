from app.semantic.analyzer import analyze_node
from app.semantic.relationships import compute_relationships
from app.schemas import NodeBrief


def test_text_node_detects_physics_domain():
    profile = analyze_node("n1", "text", "Quantum Computing relies on qubits and entanglement.", {})
    assert profile.domain == "physics"
    assert any(e.text.lower() == "quantum computing" for e in profile.entities)
    assert any(e.text.lower() == "entanglement" for e in profile.entities)
    assert "physics" in profile.tags


def test_code_node_detects_language_and_syntax_error():
    code = "def add(a, b):\n    return a + b\n\nfor i in range(5\n    print(add(i, 2))"
    profile = analyze_node("n2", "code", code, {})
    assert profile.language == "python"
    assert profile.domain == "programming"
    assert any(i.severity == "error" for i in profile.syntax_issues)
    assert profile.code_stats is not None
    assert profile.code_stats.functions >= 1


def test_formula_node_is_math_and_physics():
    profile = analyze_node("n3", "formula", "E = mc^2", {})
    assert profile.is_math
    assert profile.domain == "physics"
    assert any(e.type == "math_symbol" and e.text == "e" for e in profile.entities)


def test_relationships_between_related_nodes():
    nodes = [
        NodeBrief(id="a", type="text", content="Quantum Computing uses qubits."),
        NodeBrief(id="b", type="text", content="Qubits and entanglement are core quantum ideas."),
        NodeBrief(id="c", type="text", content="Banana bread recipe."),
    ]
    profiles = {n.id: analyze_node(n.id, n.type, n.content, n.style) for n in nodes}
    edges = compute_relationships(nodes, profiles)
    has_ab = any(
        {e.source, e.target} == {"a", "b"} for e in edges
    )
    has_ac = any(
        {e.source, e.target} == {"a", "c"} for e in edges
    )
    assert has_ab
    assert not has_ac


def test_solve_math():
    from app.routers.math import _run
    from app.schemas import MathRequest

    response = _run(MathRequest(expression="x^2 - 4", mode="solve"))
    assert response.ok
    assert "2" in response.result


def test_code_endpoint_detects_javascript():
    from app.routers.code import code_endpoint
    from app.schemas import CodeRequest
    import asyncio

    async def run():
        return await code_endpoint(CodeRequest(code="function add(a, b) {\n  return a + b;\n}"))

    result = asyncio.run(run())
    assert result.language == "javascript"
    assert result.stats.functions >= 1
