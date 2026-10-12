"""First assembly pass: location counters, symbols, and unresolved references."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field, replace
from typing import Callable

from models import Diagnostic
from parser import ParseResult, Statement


@dataclass(frozen=True, slots=True)
class Symbol:
    name: str
    kind: str
    value: int | str | None
    address: int | None
    width: int | None = None
    segment: str | None = None


@dataclass(slots=True)
class LayoutResult:
    symbols: dict[str, Symbol]
    statement_addresses: list[int]
    statement_sizes: list[int]
    diagnostics: list[Diagnostic]
    statement_segments: list[str] = field(default_factory=list)


class _ExpressionError(ValueError):
    pass


_EXPR_TOKEN = re.compile(
    r"\s*(?:(?P<number>0[xX][0-9a-fA-F]+|0[bB][01]+|[0-9][0-9a-fA-F]*[hH]|[01]+[bB]|[0-7]+[oOqQ]|[0-9]+)"
    r"|(?P<quoted>'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
    r"|(?P<identifier>[A-Za-z_.$?@][A-Za-z0-9_.$?@]*)"
    r"|(?P<operator><<|>>|[()+\-*/%~]))"
)


def _number_value(text: str) -> int:
    lower = text.lower()
    if lower.startswith("0x"):
        return int(lower[2:], 16)
    if lower.startswith("0b"):
        return int(lower[2:], 2)
    if lower.endswith("h"):
        return int(lower[:-1], 16)
    if lower.endswith("b"):
        return int(lower[:-1], 2)
    if lower.endswith(("o", "q")):
        return int(lower[:-1], 8)
    return int(lower, 10)


class _ExpressionParser:
    _precedence = {
        "or": 1,
        "xor": 2,
        "and": 3,
        "shl": 4,
        "shr": 4,
        "+": 5,
        "-": 5,
        "*": 6,
        "/": 6,
        "mod": 6,
        "%": 6,
    }

    def __init__(self, expression: str, symbols: dict[str, Symbol], current: int, segment_base: int = 0):
        expression = expression.strip()
        self.tokens: list[tuple[str, str]] = []
        position = 0
        while position < len(expression):
            match = _EXPR_TOKEN.match(expression, position)
            if not match:
                raise _ExpressionError(f"Expresión no compatible: {expression}.")
            position = match.end()
            kind = next(key for key, value in match.groupdict().items() if value is not None)
            self.tokens.append((kind, match.group(kind)))
        self.index = 0
        self.symbols = symbols
        self.current = current
        self.segment_base = segment_base

    def _peek(self) -> tuple[str, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _take(self) -> tuple[str, str]:
        token = self._peek()
        if token is None:
            raise _ExpressionError("Expresión incompleta.")
        self.index += 1
        return token

    def parse(self) -> int:
        value = self._parse_binary(1)
        if self._peek() is not None:
            raise _ExpressionError("Hay elementos no válidos al final de la expresión.")
        return value

    def _parse_binary(self, minimum: int) -> int:
        left = self._parse_unary()
        while (token := self._peek()) is not None:
            _, operator = token
            operator = operator.lower()
            precedence = self._precedence.get(operator)
            if precedence is None or precedence < minimum:
                break
            self._take()
            right = self._parse_binary(precedence + 1)
            if operator == "+":
                left += right
            elif operator == "-":
                left -= right
            elif operator == "*":
                left *= right
            elif operator in {"/", "mod", "%"}:
                if right == 0:
                    raise _ExpressionError("División entre cero.")
                left = left // right if operator == "/" else left % right
            elif operator == "and":
                left &= right
            elif operator == "or":
                left |= right
            elif operator == "xor":
                left ^= right
            elif operator == "shl":
                left <<= right
            elif operator == "shr":
                left >>= right
        return left

    def _parse_unary(self) -> int:
        token = self._peek()
        if token is None:
            raise _ExpressionError("Expresión incompleta.")
        kind, text = token
        lowered = text.lower()
        if text in {"+", "-", "~"} or lowered == "not":
            self._take()
            value = self._parse_unary()
            if text == "-":
                return -value
            if text in {"~"} or lowered == "not":
                return ~value
            return value
        if text == "(":
            self._take()
            value = self._parse_binary(1)
            if self._take()[1] != ")":
                raise _ExpressionError("Falta un paréntesis de cierre.")
            return value
        self._take()
        if kind == "number":
            return _number_value(text)
        if kind == "quoted":
            try:
                value = ast.literal_eval(text)
            except (SyntaxError, ValueError) as exc:
                raise _ExpressionError("Literal entre comillas inválido.") from exc
            if isinstance(value, str) and len(value) == 1:
                return ord(value)
            raise _ExpressionError("Se esperaba un carácter, no una cadena.")
        if kind == "identifier":
            key = text.casefold()
            if text == "$":
                return self.current
            if text == "$$":
                return self.segment_base
            if key not in self.symbols:
                raise _ExpressionError(f"Símbolo sin definir: {text}.")
            symbol = self.symbols[key]
            if symbol.kind == "constant" and isinstance(symbol.value, int):
                return symbol.value
            if symbol.address is not None:
                return symbol.address
            if isinstance(symbol.value, int):
                return symbol.value
            raise _ExpressionError(f"El símbolo {text} no tiene valor numérico.")
        raise _ExpressionError(f"Elemento no permitido: {text}.")


def _evaluate(expression: str, symbols: dict[str, Symbol], current: int, segment_base: int = 0) -> int:
    return _ExpressionParser(expression, symbols, current, segment_base).parse()


def evaluate_expression(expression: str, symbols: dict[str, Symbol], current: int = 0, segment_base: int = 0) -> int:
    """Evaluate an assembler integer expression against the current symbol table."""
    try:
        return _evaluate(expression, symbols, current, segment_base)
    except _ExpressionError as exc:
        raise ValueError(str(exc)) from exc


def _split_nested_commas(text: str) -> list[str]:
    pieces: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            pieces.append(text[start:index].strip())
            start = index + 1
    pieces.append(text[start:].strip())
    return [piece for piece in pieces if piece]


def _string_value(operand: str) -> str | None:
    if len(operand) < 2 or operand[0] not in {"'", '"'} or operand[-1] != operand[0]:
        return None
    try:
        value = ast.literal_eval(operand)
    except (SyntaxError, ValueError):
        return None
    return value if isinstance(value, str) else None


def _data_size(operation: str, operands: list[str], symbols: dict[str, Symbol], current: int, segment_base: int = 0) -> int:
    element_size = {"db": 1, "dw": 2, "dd": 4}[operation]

    def size_of_item(item: str) -> int:
        item = item.strip()
        duplicate = re.fullmatch(r"(.+?)\s+dup\s*\((.*)\)", item, flags=re.IGNORECASE)
        if duplicate:
            count = _evaluate(duplicate.group(1), symbols, current, segment_base)
            if count < 0:
                raise _ExpressionError("El contador de DUP no puede ser negativo.")
            inner = _split_nested_commas(duplicate.group(2))
            return count * sum(size_of_item(value) for value in inner)
        string = _string_value(item)
        if string is not None:
            try:
                return len(string.encode("latin-1"))
            except UnicodeEncodeError:
                return len(string.encode("utf-8"))
        if item != "?":
            # Validate expressions here so malformed constants are reported during layout.
            _evaluate(item, symbols, current, segment_base)
        return element_size

    return sum(size_of_item(operand) for operand in operands)


_RESERVED_WORDS = frozenset(
    "aam aad byte word dword ptr short near far offset seg type length size high low "
    "not mod and or xor shl shr dup cs ds es ss ax bx cx dx si di bp sp ip al ah bl bh "
    "cl ch dl dh st assume segment ends proc endp equ db dw dd org end model stack data "
    "code startup exit include macro endm ?".split()
)
_IDENTIFIER = re.compile(r"[A-Za-z_.$?@][A-Za-z0-9_.$?@]*")
_QUOTED_TEXT = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
_NUMBER_TEXT = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:0x[0-9a-f]+|0b[01]+|[0-9][0-9a-f]*h|[01]+b|[0-7]+[oq]|[0-9]+)(?![A-Za-z0-9_])"
)


def _references(expression: str) -> set[str]:
    cleaned = _QUOTED_TEXT.sub(" ", expression)
    cleaned = _NUMBER_TEXT.sub(" ", cleaned)
    return {match.group(0).casefold() for match in _IDENTIFIER.finditer(cleaned)}


def layout(program: ParseResult, size_of: Callable[[Statement], int], origin: int = 0) -> LayoutResult:
    """Assign offsets and symbols using the instruction sizes from the second-pass encoder."""
    symbols: dict[str, Symbol] = {}
    addresses: list[int] = []
    sizes: list[int] = []
    statement_segments: list[str] = []
    diagnostics = list(program.diagnostics)
    current_segment = "default"
    locations = {current_segment: origin}
    segment_bases = {current_segment: 0}
    pending_equ: list[tuple[str, str, int, int, int]] = []
    definition_lines: dict[str, int] = {}

    for statement in program.statements:
        operation = statement.operation.lower().lstrip(".")
        if operation in {"data", "code", "stack"}:
            current_segment = operation
            locations.setdefault(current_segment, 0)
            segment_bases.setdefault(current_segment, 0)
        elif operation == "segment" and statement.label:
            current_segment = statement.label.casefold()
            locations.setdefault(current_segment, 0)
            segment_bases.setdefault(current_segment, 0)

        location = locations[current_segment]
        segment_base = segment_bases[current_segment]
        statement_segments.append(current_segment)
        addresses.append(location)
        size = 0
        created_symbol: str | None = None

        if statement.label and operation not in {"endp", "ends"}:
            key = statement.label.casefold()
            if key in definition_lines:
                diagnostics.append(
                    Diagnostic(statement.line, "semantic", "LAYOUT002", f"Símbolo duplicado: {statement.label}.")
                )
            else:
                definition_lines[key] = statement.line
                created_symbol = key
                if operation == "equ":
                    symbols[key] = Symbol(statement.label, "constant", None, None, None, current_segment)
                    if statement.operands:
                        pending_equ.append((key, statement.operands[0], statement.line, location, segment_base))
                else:
                    kind = "data" if operation in {"db", "dw", "dd"} else "procedure" if operation == "proc" else "segment" if operation == "segment" else "label"
                    width = {"db": 1, "dw": 2, "dd": 4}.get(operation)
                    symbols[key] = Symbol(statement.label, kind, None, location, width, current_segment)

        if operation in {"db", "dw", "dd"}:
            try:
                size = _data_size(operation, statement.operands, symbols, location, segment_base)
                if created_symbol and symbols[created_symbol].kind == "data":
                    symbols[created_symbol] = replace(symbols[created_symbol], value=size)
            except _ExpressionError as exc:
                diagnostics.append(Diagnostic(statement.line, "semantic", "LAYOUT005", str(exc)))
        elif operation == "org":
            if statement.operands:
                try:
                    location = _evaluate(statement.operands[0], symbols, location, segment_base)
                except _ExpressionError as exc:
                    diagnostics.append(Diagnostic(statement.line, "semantic", "LAYOUT005", str(exc)))
        elif operation and operation not in {
            "equ", "end", "proc", "endp", "segment", "ends", "assume", "model", "stack", "data", "code", "startup", "exit", "include", "macro", "endm",
        } and not operation.startswith("#"):
            try:
                size = size_of(statement)
                if not isinstance(size, int) or size < 0:
                    raise ValueError(f"Tamaño de instrucción inválido: {size!r}.")
            except Exception as exc:
                error_code = getattr(exc, "code", None)
                error_message = getattr(exc, "message", None)
                if error_code and error_message:
                    diagnostics.append(Diagnostic(statement.line, "encoding", error_code, error_message))
                else:
                    diagnostics.append(Diagnostic(statement.line, "semantic", "LAYOUT004", f"No se pudo calcular el tamaño de {operation}: {exc}"))

        sizes.append(size)
        if size:
            if location < 0 or location > 0xFFFF or location + size > 0x10000:
                diagnostics.append(Diagnostic(statement.line, "semantic", "LAYOUT003", "La dirección excede el espacio de 16 bits."))
            location += size
        locations[current_segment] = location

        if operation == "ends":
            current_segment = "default"
            locations.setdefault(current_segment, origin)
            segment_bases.setdefault(current_segment, 0)

    unresolved = pending_equ[:]
    while unresolved:
        remaining: list[tuple[str, str, int, int, int]] = []
        progress = False
        for key, expression, line, current, segment_base in unresolved:
            try:
                value = _evaluate(expression, symbols, current, segment_base)
            except _ExpressionError:
                remaining.append((key, expression, line, current, segment_base))
                continue
            symbols[key] = replace(symbols[key], value=value)
            progress = True
        if not remaining:
            break
        if not progress:
            for _, expression, line, current, segment_base in remaining:
                try:
                    _evaluate(expression, symbols, current, segment_base)
                except _ExpressionError as exc:
                    diagnostics.append(Diagnostic(line, "semantic", "LAYOUT005", str(exc)))
            break
        unresolved = remaining

    for statement in program.statements:
        operation = statement.operation.lower().lstrip(".")
        if not statement.operands or operation in {"model", "stack", "segment", "ends", "proc", "endp", "include", "macro", "endm", "equ"}:
            continue
        for operand in statement.operands:
            for name in sorted(_references(operand)):
                if name in _RESERVED_WORDS or name in symbols or name in {"$", "$$", "?"}:
                    continue
                diagnostics.append(
                    Diagnostic(statement.line, "semantic", "LAYOUT001", f"Símbolo sin definir: {name}.")
                )

    return LayoutResult(symbols, addresses, sizes, diagnostics, statement_segments)
