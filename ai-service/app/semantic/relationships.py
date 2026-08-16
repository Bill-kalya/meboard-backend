import re

from ..schemas import AnalyzeResponse, NodeBrief, RelationshipEdge

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "while", "with", "by",
    "of", "in", "on", "at", "to", "from", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "its", "it", "as", "not", "can", "will", "would", "into",
    "over", "under", "about", "between", "via", "using", "use",
}

MIN_WEIGHT = 0.3
MAX_EDGES = 200


def _tokenize(content: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-zA-Z0-9_]{2,}", (content or "").lower())
        if t not in STOPWORDS and not t.isdigit()
    }


def compute_relationships(nodes: list[NodeBrief], profiles: dict[str, AnalyzeResponse]) -> list[RelationshipEdge]:
    merged: dict[frozenset[str], RelationshipEdge] = {}

    def add(a: str, b: str, relationship_type: str, weight: float, label: str) -> None:
        if a == b:
            return
        key = frozenset((a, b))
        existing = merged.get(key)
        if existing is None:
            merged[key] = RelationshipEdge(source=a, target=b, relationship_type=relationship_type, weight=weight, label=label)
        else:
            existing.weight = min(1.0, existing.weight + weight * 0.5)
            if label and label not in existing.label:
                existing.label = f"{existing.label}, {label}"[:80]

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            pa, pb = profiles.get(a.id), profiles.get(b.id)

            entity_a = {e.text.lower() for e in pa.entities} if pa else set()
            entity_b = {e.text.lower() for e in pb.entities} if pb else set()
            shared = entity_a & entity_b
            if shared:
                jaccard = len(shared) / max(1, len(entity_a | entity_b))
                add(a.id, b.id, "shares_concepts", 0.4 + 0.6 * jaccard, ", ".join(sorted(shared)[:3]))

            if (
                pa and pb and pa.domain and pb.domain
                and pa.domain == pb.domain
                and pa.domain != "unknown"
            ):
                add(a.id, b.id, "same_domain", 0.45, pa.domain)

            token_a = _tokenize(a.content)
            token_b = _tokenize(b.content)
            if token_a and token_b:
                overlap = token_a & token_b
                jaccard = len(overlap) / max(1, len(token_a | token_b))
                if len(overlap) >= 2 and jaccard > 0.2:
                    add(a.id, b.id, "shared_content", jaccard, ", ".join(sorted(overlap)[:3]))

            for current, other, other_entities in ((pa, pb, entity_b), (pb, pa, entity_a)):
                if current and current.is_math:
                    symbols = {e.text.lower() for e in current.entities if e.type == "math_symbol"}
                    hits = symbols & other_entities
                    if hits:
                        add(a.id, b.id, "math_to_concept", 0.5, ", ".join(sorted(hits)[:3]))

            if pa and pb and pa.domain and pb.domain and pa.domain != pb.domain:
                token_shared = token_a & token_b
                if token_shared and len(token_a) > 0 and len(token_b) > 0:
                    cross = len(token_shared) / min(len(token_a), len(token_b))
                    if cross > 0.4:
                        add(a.id, b.id, "bridges_domains", 0.35, ", ".join(sorted(token_shared)[:3]))

    edges = [e for e in merged.values() if e.weight >= MIN_WEIGHT]
    edges.sort(key=lambda e: e.weight, reverse=True)
    return edges[:MAX_EDGES]
