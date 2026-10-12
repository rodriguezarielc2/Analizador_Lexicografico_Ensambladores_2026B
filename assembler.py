"""End-to-end source analysis and second-pass machine-code listing."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from encoding import EncodingError, encode_statement
from instruction_set import instruction_size
from layout import Symbol, evaluate_expression, layout
from lexer import lex
from models import Diagnostic, Token
from parser import Statement, parse
from preprocessor import preprocess


@dataclass(frozen=True, slots=True)
class MachineRow:
    line: int
    address: int
    source: str
    data: bytes
    known: tuple[bool, ...] = ()
    kind: str = "instruction"
    segment: str = "default"

    @property
    def display_hex(self) -> str:
        mask = self.known or (True,) * len(self.data)
        return " ".join(f"{byte:02X}" if is_known else "??" for byte, is_known in zip(self.data, mask))


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    tokens: list[Token]
    diagnostics: list[Diagnostic]
    symbols: list[Symbol]
    machine_rows: list[MachineRow]


_DATA_WIDTH = {"db": 1, "dw": 2, "dd": 4}
_DUP = re.compile(r"(?is)^(.+?)\s+dup\s*\((.*)\)$")


def _split_initializer_list(text: str) -> list[str]:
    result: list[str] = []
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
            part = text[start:index].strip()
            if part:
                result.append(part)
            start = index + 1
    final = text[start:].strip()
    if final:
        result.append(final)
    return result


def _quoted_value(item: str) -> tuple[str, str] | None:
    if len(item) < 2 or item[0] not in {"'", '"'} or item[-1] != item[0]:
        return None
    try:
        value = ast.literal_eval(item)
    except (SyntaxError, ValueError):
        return None
    return (item[0], value) if isinstance(value, str) else None


def _data_values(statement: Statement, address: int, symbols: dict[str, Symbol]) -> list[int | None]:
    width = _DATA_WIDTH[statement.operation.lower()]
    bits = width * 8
    minimum = -(1 << (bits - 1))
    maximum = (1 << bits) - 1
    result: list[int | None] = []

    def emit_item(item: str) -> None:
        item = item.strip()
        duplicate = _DUP.fullmatch(item)
        if duplicate:
            try:
                count = evaluate_expression(duplicate.group(1), symbols, address)
            except ValueError as exc:
                raise EncodingError("ENC005", str(exc)) from exc
            if not 0 <= count <= 65535:
                raise EncodingError("ENC004", "El contador de DUP debe estar entre 0 y 65535.")
            subitems = _split_initializer_list(duplicate.group(2))
            for _ in range(count):
                for subitem in subitems:
                    emit_item(subitem)
            return

        if item == "?":
            result.extend([None] * width)
            return

        quoted = _quoted_value(item)
        if quoted is not None:
            quote, value = quoted
            if quote == "'" and len(value) == 1:
                try:
                    number = evaluate_expression(item, symbols, address)
                except ValueError as exc:
                    raise EncodingError("ENC005", str(exc)) from exc
                append_number(number)
                return
            try:
                result.extend(value.encode("latin-1"))
            except UnicodeEncodeError:
                result.extend(value.encode("utf-8"))
            return

        try:
            number = evaluate_expression(item, symbols, address)
        except ValueError as exc:
            raise EncodingError("ENC005", str(exc)) from exc
        append_number(number)

    def append_number(number: int) -> None:
        if not minimum <= number <= maximum:
            raise EncodingError("ENC004", f"El valor {number} no cabe en {bits} bits.")
        result.extend((number & ((1 << bits) - 1)).to_bytes(width, "little"))

    for operand in statement.operands:
        emit_item(operand)
    return result


def _has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(diagnostic.severity == "error" for diagnostic in diagnostics)


def _source_for_line(lines: list[str], line: int) -> str:
    return lines[line - 1].strip() if 1 <= line <= len(lines) else ""


def assemble(source: str, base_dir: Path | None = None) -> AnalysisResult:
    """Run preprocessing, lexing, syntax/semantic checks, layout, and encoding."""
    expanded = preprocess(source, base_dir)
    lexical = lex(expanded.source, expanded.line_map)
    parsed = parse(lexical.tokens)
    diagnostics = [*expanded.diagnostics, *lexical.diagnostics, *parsed.diagnostics]
    if _has_errors(diagnostics):
        return AnalysisResult(lexical.tokens, diagnostics, [], [])

    laid_out = layout(parsed, instruction_size)
    diagnostics.extend(laid_out.diagnostics[len(parsed.diagnostics):])
    if _has_errors(diagnostics):
        return AnalysisResult(lexical.tokens, diagnostics, list(laid_out.symbols.values()), [])

    original_lines = source.splitlines()
    rows: list[MachineRow] = []
    for index, statement in enumerate(parsed.statements):
        operation = statement.operation.lower().lstrip(".")
        address = laid_out.statement_addresses[index]
        expected_size = laid_out.statement_sizes[index]
        line_source = _source_for_line(original_lines, statement.line)
        if operation in _DATA_WIDTH:
            try:
                values = _data_values(statement, address, laid_out.symbols)
                if len(values) != expected_size:
                    raise EncodingError("ENC006", "El tamaño de los datos no coincide con la primera pasada.")
                data = bytes(value if value is not None else 0 for value in values)
                known = tuple(value is not None for value in values)
                rows.append(MachineRow(statement.line, address, line_source, data, known, "data", laid_out.statement_segments[index]))
            except EncodingError as exc:
                diagnostics.append(Diagnostic(statement.line, "encoding", exc.code, exc.message))
            continue

        if operation in {"startup", "exit"}:
            diagnostics.append(
                Diagnostic(statement.line, "encoding", "ENC002", f"La directiva .{operation} no tiene una expansión de bytes implementada.")
            )
            continue

        if not operation or operation in {
            "equ", "org", "end", "proc", "endp", "segment", "ends", "assume", "model", "stack", "data", "code", "include", "macro", "endm",
        } or operation.startswith("#"):
            continue

        try:
            data = encode_statement(statement, address, laid_out.symbols, laid_out.statement_segments[index])
            if len(data) != expected_size:
                raise EncodingError(
                    "ENC006",
                    f"Tamaño inconsistente: la primera pasada reservó {expected_size} byte(s) y la codificación produjo {len(data)}.",
                )
            if data:
                rows.append(MachineRow(statement.line, address, line_source, data, (True,) * len(data), "instruction", laid_out.statement_segments[index]))
        except EncodingError as exc:
            diagnostics.append(Diagnostic(statement.line, "encoding", exc.code, exc.message))

    if _has_errors(diagnostics):
        return AnalysisResult(lexical.tokens, diagnostics, list(laid_out.symbols.values()), [])
    return AnalysisResult(lexical.tokens, diagnostics, list(laid_out.symbols.values()), rows)
