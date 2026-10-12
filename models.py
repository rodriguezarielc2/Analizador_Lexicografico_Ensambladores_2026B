from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Token:
    line: int
    column: int
    lexeme: str
    category: str
    value: object | None = None
    local_line: int | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    line: int | None
    phase: str
    code: str
    message: str
    severity: str = "error"


@dataclass(slots=True)
class LexResult:
    tokens: list[Token]
    diagnostics: list[Diagnostic]
