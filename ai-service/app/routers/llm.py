import httpx
from fastapi import APIRouter

from ..config import settings
from ..schemas import ChatRequest, ChatResponse
from ..services.ollama import chat, is_available

router = APIRouter()

SYSTEM_PROMPT = (
    "You are MeBoard, the semantic thinking-board assistant. You help the user think through "
    "what is on their board: concepts, code, formulas, and how nodes relate. Be concise and "
    "precise. When the user shares a node, explain what it is, what domain it belongs to, "
    "and how it connects to other ideas."
)


def _fallback_reply(request: ChatRequest) -> str:
    if not request.messages:
        return "MeBoard is listening. Select a node and ask about it."
    last = request.messages[-1].content
    if request.context and request.context.strip():
        return (
            "I'm running in offline mode (no LLM detected), so I can only reason deterministically. "
            f"I can analyze the selected node's math (/api/math), code (/api/code), and knowledge "
            "relationships. For free-form answers, install Ollama and pull a model "
            "(docker compose exec ollama ollama pull llama3). Your message: "
            f"\"{last[:140]}\""
        )
    return (
        "I'm running in offline mode. I can analyze math, inspect code, and extract knowledge "
        "relationships, but natural-language answers need Ollama. Start it, then pull a model "
        "with `ollama pull llama3`, and I'll be fully available."
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    messages = [{"role": m.role, "content": m.content} for m in request.messages[-20:]]
    system = SYSTEM_PROMPT
    if request.context and request.context.strip():
        system += f"\n\nContext from the board (selected node):\n{request.context[: settings.max_content]}"

    async with httpx.AsyncClient(timeout=90.0) as client:
        if settings.llm_enabled and settings.semantic_mode in ("hybrid", "llm"):
            try:
                if await is_available(client):
                    reply = await chat(client, messages, system=system)
                    return ChatResponse(reply=reply, used_llm=True)
            except Exception:
                pass
        return ChatResponse(reply=_fallback_reply(request), used_llm=False)
