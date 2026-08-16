import httpx

from ..config import settings

_availability: bool | None = None


async def is_available(client: httpx.AsyncClient) -> bool:
    global _availability
    if _availability is not None:
        return _availability
    try:
        response = await client.get(f"{settings.ollama_host}/api/tags", timeout=2.0)
        _availability = response.status_code == 200
    except httpx.HTTPError:
        _availability = False
    return _availability


async def generate(
    client: httpx.AsyncClient,
    prompt: str,
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 400,
) -> str:
    payload: dict = {
        "model": settings.llm_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    if system:
        payload["system"] = system
    response = await client.post(f"{settings.ollama_host}/api/generate", json=payload, timeout=60.0)
    response.raise_for_status()
    return response.json().get("response", "")


async def chat(
    client: httpx.AsyncClient,
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.3,
) -> str:
    payload: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    response = await client.post(f"{settings.ollama_host}/api/chat", json=payload, timeout=90.0)
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "")
