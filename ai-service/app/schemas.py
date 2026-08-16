from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Entity(BaseModel):
    text: str
    type: str
    confidence: float


class Insight(BaseModel):
    text: str
    type: str


class SyntaxIssue(BaseModel):
    line: Optional[int] = None
    message: str
    severity: str


class CodeStats(BaseModel):
    language: str
    lines: int = 0
    functions: int = 0
    classes: int = 0
    imports: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    node_id: str
    node_type: str = "text"
    content: str = ""
    style: dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    node_id: str
    node_type: str
    domain: Optional[str] = None
    domain_confidence: float = 0.0
    entities: list[Entity] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: Optional[str] = None
    syntax_issues: list[SyntaxIssue] = Field(default_factory=list)
    code_stats: Optional[CodeStats] = None
    is_math: bool = False
    math_expression: Optional[str] = None
    insights: list[Insight] = Field(default_factory=list)


class NodeBrief(BaseModel):
    id: str
    type: str = "text"
    content: str = ""
    style: dict[str, Any] = Field(default_factory=dict)


class RelationshipRequest(BaseModel):
    nodes: list[NodeBrief]


class RelationshipEdge(BaseModel):
    source: str
    target: str
    relationship_type: str
    weight: float
    label: str


class RelationshipResponse(BaseModel):
    edges: list[RelationshipEdge]


class MathRequest(BaseModel):
    expression: str
    mode: Literal["solve", "simplify", "derivative", "integral", "evaluate"] = "solve"
    variable: Optional[str] = None


class MathResponse(BaseModel):
    expression: str
    result: str
    steps: list[str] = Field(default_factory=list)
    ok: bool = True
    error: Optional[str] = None


class CodeRequest(BaseModel):
    code: str
    language_hint: Optional[str] = None


class CodeResponse(BaseModel):
    language: str
    syntax_issues: list[SyntaxIssue] = Field(default_factory=list)
    stats: CodeStats
    entities: list[Entity] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    used_llm: bool
