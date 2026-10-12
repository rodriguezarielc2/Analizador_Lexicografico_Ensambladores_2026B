"""Line-oriented syntax and local semantic checks for 8086 assembly."""

from __future__ import annotations

from dataclasses import dataclass

from models import Diagnostic, Token


@dataclass(frozen=True, slots=True)
class Statement:
    line: int
    label: str | None
    operation: str
    operands: list[str]


@dataclass(slots=True)
class ParseResult:
    statements: list[Statement]
    diagnostics: list[Diagnostic]


_NO_OPERANDS = frozenset(
    "aaa aas cbw clc cld cli cmc cwd daa das hlt into iret lahf nop popf pushf sahf "
    "stc std sti wait xlat xlatb movsb movsw cmpsb cmpsw lodsb lodsw stosb stosw "
    "scasb scasw".split()
)
_ONE_OPERAND = frozenset(
    "call dec div idiv imul inc int jmp mul neg not pop push loop loope loopne loopnz "
    "loopz ja jae jb jbe jc jcxz je jg jge jl jle jna jnae jnb jnbe jnc jne jng "
    "jnge jnl jnle jno jnp jns jnz jo jp jpe jpo js jz".split()
)
_TWO_OPERANDS = frozenset(
    "mov add adc sub sbb and or xor cmp test xchg lea lds les in out rcl rcr rol ror "
    "sal sar shl shr".split()
)
_OPTIONAL_ONE_OPERAND = frozenset("ret retf retn aam aad".split())
_REPEAT_PREFIXES = frozenset("rep repe repz repne repnz".split())
_STRING_INSTRUCTIONS = frozenset("movsb movsw cmpsb cmpsw lodsb lodsw stosb stosw scasb scasw".split())
_LOCKABLE_INSTRUCTIONS = frozenset("add adc and or xor sub sbb inc dec neg not".split())
_DIRECTIVE_ARITY: dict[str, tuple[int, int | None]] = {
    "db": (1, None),
    "dw": (1, None),
    "dd": (1, None),
    "equ": (1, 1),
    "org": (1, 1),
    "include": (1, 1),
    "end": (0, 1),
    "proc": (0, 1),
    "endp": (0, 1),
    "segment": (0, None),
    "ends": (0, 1),
    "macro": (0, None),
    "endm": (0, 0),
    "assume": (1, None),
    "model": (1, 1),
    "stack": (1, 1),
    "data": (0, 0),
    "code": (0, 0),
    "startup": (0, 0),
    "exit": (0, 0),
}


def _operand_text(tokens: list[Token]) -> str:
    result = ""
    previous_word = False
    for token in tokens:
        if token.category == "separator":
            result += ", "
            previous_word = False
            continue
        word = token.category in {"register", "identifier", "number", "directive", "string", "character"}
        if result and previous_word and word:
            result += " "
        result += token.lexeme
        previous_word = word
    return result.strip()


def _split_operands(tokens: list[Token]) -> tuple[list[str], bool]:
    if not tokens:
        return [], False
    operands: list[str] = []
    current: list[Token] = []
    empty_operand = False
    nesting = 0
    for token in tokens:
        if token.lexeme in {"(", "["}:
            nesting += 1
            current.append(token)
        elif token.lexeme in {")", "]"}:
            nesting = max(0, nesting - 1)
            current.append(token)
        elif token.category == "separator" and nesting == 0:
            text = _operand_text(current)
            if text:
                operands.append(text)
            else:
                empty_operand = True
            current = []
        else:
            current.append(token)
    final_text = _operand_text(current)
    if final_text:
        operands.append(final_text)
    elif tokens and tokens[-1].category == "separator":
        empty_operand = True
    return operands, empty_operand


def _expected_arity(operation: str) -> tuple[int, int | None] | None:
    if operation in _NO_OPERANDS:
        return (0, 0)
    if operation in _ONE_OPERAND:
        return (1, 1)
    if operation in _TWO_OPERANDS:
        return (2, 2)
    if operation in _OPTIONAL_ONE_OPERAND:
        return (0, 1)
    directive_name = operation.lstrip(".")
    if directive_name in _DIRECTIVE_ARITY:
        return _DIRECTIVE_ARITY[directive_name]
    if operation.startswith("#") and operation.endswith("#"):
        return (0, 0)
    return None


def _register_width(operand: str) -> int | None:
    name = operand.strip().lower()
    if name in {"al", "ah", "bl", "bh", "cl", "ch", "dl", "dh"}:
        return 8
    if name in {"ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "ip", "cs", "ds", "es", "ss"}:
        return 16
    return None


def _validate_statement(statement: Statement, diagnostics: list[Diagnostic]) -> None:
    operation = statement.operation
    if not operation:
        return
    parts = operation.split()
    if len(parts) == 2 and parts[0] in _REPEAT_PREFIXES and parts[1] in _STRING_INSTRUCTIONS:
        return
    if len(parts) == 2 and parts[0] == "lock" and parts[1] in _LOCKABLE_INSTRUCTIONS:
        expected_operands = 1 if parts[1] in {"inc", "dec", "neg", "not"} else 2
        if len(statement.operands) == expected_operands:
            return
        diagnostics.append(
            Diagnostic(statement.line, "syntax", "PARSE002", f"LOCK {parts[1].upper()} espera {expected_operands} operando(s).")
        )
        return
    expected = _expected_arity(operation)
    if expected is None:
        diagnostics.append(
            Diagnostic(statement.line, "syntax", "PARSE001", f"Operación no reconocida: {operation}.")
        )
        return
    minimum, maximum = expected
    count = len(statement.operands)
    if count < minimum or (maximum is not None and count > maximum):
        if maximum == minimum:
            expected_count = str(minimum)
        elif maximum is None:
            expected_count = f"al menos {minimum}"
        else:
            expected_count = f"de {minimum} a {maximum}"
        diagnostics.append(
            Diagnostic(
                statement.line,
                "syntax",
                "PARSE002",
                f"{operation.upper()} espera {expected_count} operando(s); recibió {count}.",
            )
        )
    if operation in _TWO_OPERANDS and operation not in {"in", "out"} and count == 2:
        left_width = _register_width(statement.operands[0])
        right_width = _register_width(statement.operands[1])
        if left_width and right_width and left_width != right_width:
            diagnostics.append(
                Diagnostic(
                    statement.line,
                    "semantic",
                    "SEM002",
                    f"Los registros tienen tamaños incompatibles: {left_width} y {right_width} bits.",
                )
            )


def _line_number(tokens: list[Token]) -> int:
    return tokens[0].line if tokens else 1


def parse(tokens: list[Token]) -> ParseResult:
    """Parse statements, splitting operands on retained internal separators."""
    grouped: dict[int, list[Token]] = {}
    for token in tokens:
        if token.category == "comment":
            continue
        local_line = token.local_line if token.local_line is not None else token.line
        grouped.setdefault(local_line, []).append(token)

    statements: list[Statement] = []
    diagnostics: list[Diagnostic] = []
    defined_labels: dict[str, int] = {}
    for line_tokens in grouped.values():
        tokens_on_line = sorted(line_tokens, key=lambda token: token.column)
        line = _line_number(tokens_on_line)
        if not tokens_on_line:
            continue
        label: str | None = None
        is_uncolonized_end = False
        body = tokens_on_line
        if (
            len(body) >= 2
            and body[0].category == "identifier"
            and body[1].lexeme == ":"
        ):
            label = body[0].lexeme
            body = body[2:]
        elif (
            len(body) >= 2
            and body[0].category == "identifier"
            and body[1].category == "directive"
        ):
            label = body[0].lexeme
            is_uncolonized_end = body[1].lexeme.lower() in {"endp", "ends"}
            body = body[1:]

        if label and not is_uncolonized_end:
            key = label.casefold()
            if key in defined_labels:
                diagnostics.append(
                    Diagnostic(line, "semantic", "SEM001", f"Símbolo duplicado: {label}.")
                )
            else:
                defined_labels[key] = line

        if not body:
            statement = Statement(line, label, "", [])
            statements.append(statement)
            continue

        operation_token = body[0]
        operation = operation_token.lexeme.lower()
        if operation == "lock" and len(body) > 1 and body[1].category == "mnemonic":
            operation = f"lock {body[1].lexeme.lower()}"
            body = [body[0], *body[2:]]
        if operation_token.category not in {"mnemonic", "directive"}:
            diagnostics.append(
                Diagnostic(line, "syntax", "PARSE001", f"Operación no reconocida: {operation_token.lexeme}.")
            )
        operands, empty_operand = _split_operands(body[1:])
        if operation in _REPEAT_PREFIXES:
            if len(operands) == 1 and operands[0].lower() in _STRING_INSTRUCTIONS:
                operation = f"{operation} {operands.pop().lower()}"
            else:
                diagnostics.append(
                    Diagnostic(line, "syntax", "PARSE002", f"{operation.upper()} debe preceder una instrucci\u00f3n de cadena.")
                )
        if empty_operand:
            diagnostics.append(
                Diagnostic(line, "syntax", "PARSE003", "Falta un operando entre separadores.")
            )
        statement = Statement(line, label, operation, operands)
        statements.append(statement)
        if operation_token.category in {"mnemonic", "directive"}:
            _validate_statement(statement, diagnostics)

    return ParseResult(statements, diagnostics)
