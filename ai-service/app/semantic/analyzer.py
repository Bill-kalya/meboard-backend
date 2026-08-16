import json

from ..schemas import AnalyzeRequest, AnalyzeResponse, Entity, Insight, SyntaxIssue, VisualizationSpec
from . import detectors
from .visualize import build_visualization


def analyze_node(node_id: str, node_type: str, content, style: dict) -> AnalyzeResponse:
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False)
    content = str(content or "").strip()
    node_type = (node_type or "text").lower()

    entities: list[Entity] = []
    insights: list[Insight] = []
    syntax_issues: list[SyntaxIssue] = []
    domain: str | None = None
    domain_confidence = 0.0
    language: str | None = None
    code_stats = None
    is_math = False
    math_expression: str | None = None
    symbols: set[str] = set()
    visualization: VisualizationSpec | None = None

    if node_type == "code":
        hint = (style or {}).get("language")
        language = detectors.detect_language(content, hint)
        syntax_issues, code_stats = detectors.analyze_code(content, language)
        entities = detectors.extract_code_entities(content, language)
        domain, domain_confidence = "programming", 0.9
        insights.append(Insight(text=f"Detected as {language}.", type="observation"))
        for issue in syntax_issues[:3]:
            if issue.severity == "error":
                insights.append(Insight(text=issue.message, type="issue"))
        if code_stats and code_stats.functions:
            insights.append(
                Insight(
                    text=f"Contains {code_stats.functions} function(s) and {code_stats.classes} class(es).",
                    type="observation",
                )
            )
        if code_stats and code_stats.imports:
            insights.append(Insight(text=f"Depends on: {', '.join(code_stats.imports[:4])}.", type="observation"))
    elif node_type == "formula":
        is_math, math_expression, symbols = detectors.detect_math(content)
        domain, domain_confidence = detectors.detect_domain(content, is_math=True, symbols=symbols)
        entities = detectors.extract_entities(content)
        visualization = build_visualization(content)
        for symbol in sorted(symbols)[:6]:
            entities.append(Entity(text=symbol, type="math_symbol", confidence=0.8))
        insights.append(Insight(text="Recognized as a mathematical expression.", type="observation"))
        if domain:
            insights.append(Insight(text=f"Formula classified as {domain}.", type="category"))
    else:
        is_math, math_expression, symbols = detectors.detect_math(content)
        domain, domain_confidence = detectors.detect_domain(content, is_math=is_math, symbols=symbols)
        entities = detectors.extract_entities(content)
        visualization = build_visualization(content)
        if is_math and domain:
            insights.append(Insight(text=f"Contains math, classified as {domain}.", type="category"))
        elif domain:
            insights.append(Insight(text=f"Belongs to {domain}.", type="category"))
        if entities:
            top = [e.text for e in entities[:3]]
            insights.append(Insight(text=f"Key concepts: {', '.join(top)}.", type="entity"))
        if not domain and not entities:
            insights.append(Insight(text="No clear domain or entities detected yet.", type="observation"))

    tags = build_tags(node_type, domain, language, entities, is_math)
    entities = dedupe_entities(entities)
    insights = dedupe_insights(insights)

    return AnalyzeResponse(
        node_id=node_id,
        node_type=node_type,
        domain=domain,
        domain_confidence=domain_confidence,
        entities=entities,
        tags=tags,
        language=language,
        syntax_issues=syntax_issues,
        code_stats=code_stats,
        is_math=is_math,
        math_expression=math_expression,
        insights=insights,
        visualization=visualization,
    )


def build_tags(node_type: str, domain: str | None, language: str | None, entities: list[Entity], is_math: bool) -> list[str]:
    tags: list[str] = []
    if domain:
        tags.append(domain)
    if node_type == "code":
        tags.append("code")
        if language and language != "unknown":
            tags.append(language)
    if is_math:
        tags.append("math")
    for entity in entities[:4]:
        tag = entity.text.lower()
        if tag not in tags:
            tags.append(tag)
    return tags[:10]


def dedupe_entities(entities: list[Entity]) -> list[Entity]:
    best: dict[str, Entity] = {}
    for entity in entities:
        key = entity.text.lower()
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity
    return list(best.values())


def dedupe_insights(insights: list[Insight]) -> list[Insight]:
    seen: set[str] = set()
    result: list[Insight] = []
    for insight in insights:
        key = insight.text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(insight)
    return result[:8]
