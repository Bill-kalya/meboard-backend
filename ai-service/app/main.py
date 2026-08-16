from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import code, llm, math, semantic, visualize

app = FastAPI(
    title="MeBoard AI Service",
    version="0.1.0",
    description="Semantic engine for MeBoard: the board that understands what is on it.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(semantic.router)
app.include_router(math.router)
app.include_router(code.router)
app.include_router(llm.router)
app.include_router(visualize.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "healthy", "service": "meboard-ai", "mode": settings.semantic_mode}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
