import re
from collections import Counter

from ..schemas import CodeStats, Entity, SyntaxIssue
from .lexicon import DOMAINS, KNOWN_TERMS, STOP_CAPS

LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    "python": ["def ", "import ", "from ", "print(", "class ", "elif ", "lambda ", "self.", "range(", "yield", "async def", "None", "True", "False", " if ", " else:"],
    "javascript": ["function", "const ", "let ", "var ", "=>", "console.", "document.", "addEventListener", "export default", "import {", "typeof", "undefined"],
    "typescript": ["interface ", "type ", "enum ", "implements", "readonly", "satisfies", ": string", ": number", ": void", "unknown"],
    "rust": ["fn ", "let mut", "fn main", "struct ", "impl ", "pub fn", "use std", "match ", "&mut", "unwrap", "cargo", "vec!", "println!("],
    "java": ["public class", "private ", "System.out", "import java", "@Override", "void main", "new ArrayList", "extends ", "static void"],
    "c": ["#include", "printf(", "int main", "malloc", "return 0;", "struct ", "#define"],
    "cpp": ["#include <iostream>", "std::", "cout <<", "vector<int>", "template", "namespace", "std::vector"],
    "csharp": ["using System", "public class", "Console.WriteLine", "namespace ", "void Main", "async Task", "StringBuilder"],
    "go": ["package main", "func main", "fmt.Println", ":= ", "golang", "import (", "go func", "defer", "chan "],
    "sql": ["SELECT", "FROM", "WHERE", "INSERT INTO", "CREATE TABLE", "JOIN", "GROUP BY", "UPDATE ", "DELETE FROM", "SELECT *"],
    "bash": ["#!/bin/bash", "echo ", "sudo ", "export ", "if [", "for i in", "curl ", "grep ", "awk ", "chmod"],
    "html": ["<!DOCTYPE html>", "<html", "<div", "<body", "<head", "<script", "<link", "class=\"", "<p>"],
    "css": [":hover", "margin:", "padding:", "display:", "font-size:", "background-color", "flex", "@media"],
    "json": ['"name"', '"id"', '{ "', '": ', '"}'],
    "ruby": ["def ", "end\n", "puts ", "attr_accessor", "rails", "do |", "gem "],
    "php": ["<?php", "echo ", "function ", "->", "isset", "array("],
}

SHEBANG_LANG = {"python": ("python", "python3"), "bash": ("bash", "sh")}


def _strong_signal(content: str) -> str | None:
    if re.search(r"\bdef\s+\w+\s*\(", content):
        return "python"
    if re.search(r"\bfunction\s+\w+\s*\(", content) or re.search(r"=>", content):
        return "javascript"
    if re.search(r"\bfn\s+\w+\s*\(", content):
        return "rust"
    if re.search(r"\b(?:interface|type)\s+\w+\s*[{=]", content) and re.search(r"\b(?:string|number|boolean|unknown)\b", content):
        return "typescript"
    if re.search(r"#include\s*<", content):
        return "cpp"
    if re.search(r"#include\s*\"", content):
        return "c"
    if re.search(r"\busing\s+System\b", content):
        return "csharp"
    if re.search(r"\bpackage\s+main\b", content):
        return "go"
    if re.search(r"<\?php", content):
        return "php"
    if re.search(r"public\s+class\s+\w+", content):
        return "java"
    return None


def detect_language(content: str, hint: str | None) -> str:
    if hint:
        lang = hint.lower()
        if lang in ("js", "javascript"):
            return "javascript"
        if lang in ("ts", "typescript"):
            return "typescript"
        if lang in ("c++", "cpp", "cplusplus"):
            return "cpp"
        if lang in ("cs", "csharp", "c#"):
            return "csharp"
        if lang in ("py",):
            return "python"
        if lang in ("go", "golang"):
            return "go"
        if lang in ("rs", "rust"):
            return "rust"
        if lang in ("sh", "shell", "zsh", "bash"):
            return "bash"
        if lang in ("kt", "kotlin"):
            return "kotlin"
        if lang in ("swift",):
            return "swift"
        return lang if lang in LANGUAGE_KEYWORDS else "unknown"

    first_line = (content or "").splitlines()[0].strip() if content else ""
    if first_line.startswith("#!"):
        for lang, markers in SHEBANG_LANG.items():
            if any(m in first_line for m in markers):
                return lang

    strong = _strong_signal(content)
    if strong:
        return strong

    scores: Counter[str] = Counter()
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in content:
                scores[lang] += 1

    if scores:
        top, count = scores.most_common(1)[0]
        if count >= 2:
            return top
        if count == 1:
            second = scores.most_common(2)
            if len(second) > 1 and second[1][1] == count:
                return "unknown"
            return top

    if re.search(r"\bdef\s+\w+\s*\(", content):
        return "python"
    if re.search(r"\bfunction\s+\w+|=>", content):
        return "javascript"
    if re.search(r"\bfn\s+\w+\s*\(", content):
        return "rust"
    if re.search(r"\b(?:SELECT|INSERT INTO|CREATE TABLE)\b", content, re.I):
        return "sql"
    return "unknown"


def analyze_code(code: str, language: str) -> tuple[list[SyntaxIssue], CodeStats]:
    issues: list[SyntaxIssue] = []
    stats = CodeStats(language=language, lines=code.count("\n") + 1)
    lower = code.lower()

    if language == "python":
        try:
            compile(code, "<meboard>", "exec")
        except SyntaxError as e:
            issues.append(SyntaxIssue(line=e.lineno, message=f"SyntaxError: {e.msg}", severity="error"))
        except ValueError as e:
            issues.append(SyntaxIssue(line=None, message=str(e), severity="error"))
        stats.imports = [a or b for a, b in re.findall(r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)", code, re.M)]
        stats.functions = len(re.findall(r"^\s*def\s+\w+", code, re.M))
        stats.classes = len(re.findall(r"^\s*class\s+\w+", code, re.M))
        if "\t" in code and re.search(r"^ {4}", code, re.M):
            issues.append(SyntaxIssue(line=None, message="Mixed tabs and spaces in indentation", severity="warning"))
    elif language in ("javascript", "typescript"):
        for open_c, close_c in (("(", ")"), ("{", "}"), ("[", "]")):
            o, c = code.count(open_c), code.count(close_c)
            if o != c:
                issues.append(SyntaxIssue(line=None, message=f"Unbalanced '{open_c}': {o} open vs {c} close", severity="warning"))
        stats.imports = re.findall(r"(?:import\s+.*?from\s+|require\()['\"]([^'\"]+)['\"]", code)
        stats.functions = len(re.findall(r"\bfunction\s+\w+|\b\w+\s*\([^)]*\)\s*\{|=>", code))
        stats.classes = len(re.findall(r"\bclass\s+\w+", code))
    elif language == "rust":
        stats.functions = len(re.findall(r"\bfn\s+\w+", code))
        stats.classes = len(re.findall(r"\b(?:struct|enum|trait|impl)\s+\w+", code))
        stats.imports = re.findall(r"^\s*use\s+([\w:]+)", code, re.M)
    elif language == "go":
        stats.functions = len(re.findall(r"\bfunc\s+\w+", code))
        stats.imports = re.findall(r'^\s*"([^"]+)"', code, re.M)
    elif language == "java":
        stats.imports = re.findall(r"^\s*import\s+([\w.]+)", code, re.M)
        stats.classes = len(re.findall(r"\bclass\s+\w+", code))
        stats.functions = len(re.findall(r"\b(?:public|private|protected|static)?\s*\w+\s+\w+\s*\(", code))
    elif language == "c" or language == "cpp":
        stats.imports = re.findall(r"^\s*#include\s*[<\"]([\w.]+)[>\"]", code, re.M)
    elif language == "csharp":
        stats.imports = re.findall(r"^\s*using\s+([\w.]+)", code, re.M)
        stats.classes = len(re.findall(r"\bclass\s+\w+", code))
    elif language == "bash":
        stats.functions = len(re.findall(r"^\s*\w+\s*\(\)\s*\{", code, re.M))
    elif language == "sql":
        tables = set(re.findall(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([\w.]+)", code, re.I))
        stats.imports = sorted(tables)
    elif language == "html":
        pass

    if language in ("python", "javascript", "typescript", "java", "c", "cpp", "csharp", "go", "rust"):
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.endswith(("{", "}", "(", ")", "[", "]")) and not stripped.endswith(("(", "{")):
                continue
        if not stats.functions and not stats.classes and not stats.imports and len(code.splitlines()) > 40:
            issues.append(SyntaxIssue(line=None, message="Large code block with no structure detected", severity="info"))

    return issues, stats


def extract_code_entities(code: str, language: str) -> list[Entity]:
    found: list[Entity] = []
    seen: set[str] = set()

    def add(text: str, entity_type: str, confidence: float) -> None:
        if not text or text in seen:
            return
        seen.add(text)
        found.append(Entity(text=text, type=entity_type, confidence=confidence))

    for m in re.finditer(r"\b(?:def|function|class|fn|pub fn|struct|enum)\s+([A-Za-z_]\w*)", code):
        add(m.group(1), "code_identifier", 0.85)
    for m in re.finditer(r"\b(?:import|from|use|require)\s+([A-Za-z_][\w.]*)", code):
        add(m.group(1), "module", 0.8)
    for m in re.finditer(r"\b[A-Za-z_]\w*\b", code):
        name = m.group(0)
        if name in ("print", "len", "range", "str", "int", "return", "if", "else", "for", "while", "import", "from", "def", "class", "function", "const", "let", "var"):
            continue
        if re.fullmatch(r"[a-z]+_[a-z_]+", name) or re.fullmatch(r"[a-z]+[A-Z]\w*", name):
            add(name, "code_identifier", 0.55)
    return found[:20]


def detect_domain(text: str, language: str | None = None, is_math: bool = False, symbols: set[str] | None = None) -> tuple[str | None, float]:
    lower = text.lower()
    scores: Counter[str] = Counter()
    for domain, terms in DOMAINS.items():
        for term in terms:
            if term in lower:
                scores[domain] += 1

    if language and language != "unknown" and language != "sql":
        scores["programming"] += 3
    elif language == "sql":
        scores["programming"] += 2

    if is_math and symbols:
        physics_symbols = {"e", "m", "c", "f", "g", "p", "v", "q", "h", "t", "a", "w", "k"}
        math_symbols = {"x", "y", "z", "n", "f", "u", "v", "i", "a", "b"}
        if symbols & physics_symbols and not symbols & math_symbols:
            scores["physics"] += 1
        if symbols & math_symbols and not symbols & physics_symbols:
            scores["mathematics"] += 1

    if not scores:
        return None, 0.0
    top, count = scores.most_common(1)[0]
    total = sum(scores.values())
    confidence = min(0.95, 0.45 + 0.12 * count)
    if total >= 3:
        confidence *= 0.9
    return top, round(confidence, 2)


MATH_FUNCTION_RE = re.compile(r"\b(sqrt|sin|cos|tan|log|ln|exp|abs|sum|integral|derivative|diff|lim|gcd)\b", re.I)
GREEK_RE = re.compile(r"[α-ωΑ-Ωπ∂∑∫√∞θλμϕφ]")


def detect_math(text: str) -> tuple[bool, str | None, set[str]]:
    if not text:
        return False, None, set()
    has_relation = "=" in text
    has_operator = any(ch in text for ch in "+-*/^∫∑√π×÷∂")
    has_function = bool(MATH_FUNCTION_RE.search(text))
    has_greek = bool(GREEK_RE.search(text))
    if not (has_relation or has_operator or has_function or has_greek):
        return False, None, set()
    expr = text.strip().replace("\n", " ")[:240]
    letters: set[str] = set()
    for token in re.findall(r"[A-Za-z][A-Za-z0-9]*", text):
        if len(token) == 1:
            letters.add(token.lower())
        elif len(token) == 2 and token.lower() in ("mc", "mv", "kg", "nm", "cm", "mm"):
            letters.update(ch.lower() for ch in token)
    return True, expr, letters


def extract_entities(text: str) -> list[Entity]:
    entities: list[Entity] = []
    best: dict[str, Entity] = {}

    def add(entity: Entity) -> None:
        key = entity.text.lower()
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity

    stop_lower = {s.lower() for s in STOP_CAPS}

    for m in re.finditer(r"\b[A-Z][a-zA-Z']*(?:\s+[A-Z][a-zA-Z']*){0,2}\b", text):
        phrase = m.group(0).strip()
        if phrase.lower() in stop_lower:
            continue
        is_multi = " " in phrase
        prev = text[: m.start()].rstrip()
        sentence_start = (not prev) or prev[-1] in ".!?:;"
        if not is_multi and sentence_start:
            confidence = 0.5
        elif is_multi:
            confidence = 0.75
        else:
            confidence = 0.6
        add(Entity(text=phrase, type="topic", confidence=confidence))

    for term in KNOWN_TERMS:
        for m in re.finditer(rf"\b{re.escape(term)}\b", text, re.I):
            add(Entity(text=term.title(), type="concept", confidence=0.9))

    for m in GREEK_RE.finditer(text):
        add(Entity(text=m.group(0), type="math_symbol", confidence=1.0))

    return list(best.values())[:20]
