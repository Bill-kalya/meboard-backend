import json
import re

import httpx
from fastapi import APIRouter

from ..config import settings
from ..schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Entity,
    Insight,
    NodeBrief,
    RelationshipRequest,
    RelationshipResponse,
)
from ..semantic.analyzer import analyze_node, dedupe_insights
from ..semantic.relationships import compute_relationships
from ..services.ollama import generate, is_available

router = APIRouter()

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def _strip_fences(raw: str) -> str:
    return _FENCE_RE.sub("", raw).strip()


async def _augment_with_llm(client: httpx.AsyncClient, request: AnalyzeRequest, profile: AnalyzeResponse) -> AnalyzeResponse:
    if not settings.llm_enabled or settings.semantic_mode not in ("hybrid", "llm"):
        return profile
    if not request.content.strip():
        return profile
    try:
        if not await is_available(client):
            return profile
        prompt = (
            f"Node type: {request.node_type}\n"
            f"Content:\n\"\"\"\n{request.content[: settings.max_content]}\n\"\"\"\n\n"
            "Given the content, reply with STRICT JSON only (no prose, no fences):\n"
            "{\"domain\": \"physics|mathematics|programming|chemistry|biology|economics|philosophy|history|computer-science|design|music|other\", "
            "\"entities\": [{\"text\": \"...\", \"type\": \"topic|concept|term|person|technology\", \"confidence\": 0.0}], "
            "\"insights\": [\"...\", \"...\"]}"
        )
        system = "You classify text and extract knowledge entities for a semantic whiteboard. Return strict JSON only."
        raw = await generate(client, prompt, system=system, temperature=0.1, max_tokens=500)
        data = json.loads(_strip_fences(raw))

        domain = str(data.get("domain", "")).strip()
        if domain and domain != "other":
            profile.domain = domain
            profile.domain_confidence = max(profile.domain_confidence, 0.6)

        for entry in data.get("entities", [])[:8]:
            text = str(entry.get("text", "")).strip()
            if not text:
                continue
            try:
                confidence = float(entry.get("confidence", 0.7))
            except (TypeError, ValueError):
                confidence = 0.7
            profile.entities.append(Entity(text=text, type=str(entry.get("type", "concept")), confidence=min(1.0, max(0.0, confidence))))

        for text in data.get("insights", [])[:5]:
            if isinstance(text, str) and text.strip():
                profile.insights.append(Insight(text=text.strip(), type="llm"))

        profile.entities = _dedupe_entities(profile.entities)
        profile.insights = dedupe_insights(profile.insights)
    except Exception:
        pass
    return profile


def _dedupe_entities(entities: list[Entity]) -> list[Entity]:
    best: dict[str, Entity] = {}
    for entity in entities:
        key = entity.text.lower()
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity
    return list(best.values())[:20]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    profile = analyze_node(request.node_id, request.node_type, request.content, request.style)
    async with httpx.AsyncClient(timeout=60.0) as client:
        profile = await _augment_with_llm(client, request, profile)
    return profile


@router.post("/relationships", response_model=RelationshipResponse)
async def relationships(request: RelationshipRequest) -> RelationshipResponse:
    profiles = {
        node.id: analyze_node(node.id, node.type, node.content, node.style)
        for node in request.nodes
    }
    edges = compute_relationships(request.nodes, profiles)
    return RelationshipResponse(edges=edges)
