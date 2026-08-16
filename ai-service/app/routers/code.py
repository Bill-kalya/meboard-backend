from fastapi import APIRouter

from ..schemas import CodeRequest, CodeResponse
from ..semantic.detectors import analyze_code, detect_language, extract_code_entities

router = APIRouter()


@router.post("/code", response_model=CodeResponse)
async def code_endpoint(request: CodeRequest) -> CodeResponse:
    language = detect_language(request.code, request.language_hint)
    syntax_issues, stats = analyze_code(request.code, language)
    entities = extract_code_entities(request.code, language)

    insights = [f"Language detected: {language}."]
    insights.extend(issue.message for issue in syntax_issues[:5])
    if stats.functions or stats.classes:
        insights.append(f"{stats.functions} function(s), {stats.classes} class(es).")
    if stats.imports:
        insights.append(f"Imports/dependencies: {', '.join(stats.imports[:6])}.")

    return CodeResponse(
        language=language,
        syntax_issues=syntax_issues,
        stats=stats,
        entities=entities,
        insights=insights,
    )
