"""Macro and INCLUDE expansion for the local assembler pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from models import Diagnostic


@dataclass(slots=True)
class PreprocessResult:
    source: str
    line_map: list[int]
    diagnostics: list[Diagnostic]


@dataclass(frozen=True, slots=True)
class _Macro:
    parameters: tuple[str, ...]
    body: tuple[str, ...]


_INCLUDE = re.compile(
    r"^\s*include\s+(?:\"([^\"]+)\"|'([^']+)'|([^;\s]+))",
    re.IGNORECASE,
)
_MACRO_HEADER = re.compile(
    r"^\s*([A-Za-z_.$@][\w.$@]*)\s+macro(?:\s+(.*?))?\s*(?:;.*)?$",
    re.IGNORECASE,
)
_MACRO_END = re.compile(r"^\s*endm\b", re.IGNORECASE)
_CALL = re.compile(r"^(\s*)([A-Za-z_.$@][\w.$@]*)(?:\s+(.*?))?\s*(?:;.*)?$")
_MAX_MACRO_DEPTH = 32


def _split_args(text: str) -> list[str]:
    if not text.strip():
        return []
    args: list[str] = []
    start = 0
    quote: str | None = None
    bracket_depth = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote and (index == 0 or text[index - 1] != "\\"):
                quote = None
            continue
        if char in "'\"":
            quote = char
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif char == "," and bracket_depth == 0:
            args.append(text[start:index].strip())
            start = index + 1
    args.append(text[start:].strip())
    return args


def _expand_includes(
    lines: list[str],
    origins: list[int],
    base_dir: Path | None,
    include_stack: tuple[Path, ...],
    diagnostics: list[Diagnostic],
) -> tuple[list[str], list[int]]:
    output: list[str] = []
    output_origins: list[int] = []
    for line, origin in zip(lines, origins):
        match = _INCLUDE.match(line)
        if not match:
            output.append(line)
            output_origins.append(origin)
            continue
        filename = next(value for value in match.groups() if value is not None)
        if base_dir is None:
            diagnostics.append(
                Diagnostic(origin, "preprocess", "PP001", f"No se puede resolver INCLUDE sin carpeta base: {filename}.")
            )
            continue
        path = (base_dir / filename).resolve()
        if path in include_stack:
            diagnostics.append(
                Diagnostic(origin, "preprocess", "PP002", f"Ciclo de INCLUDE detectado: {filename}.")
            )
            continue
        try:
            included_lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            diagnostics.append(
                Diagnostic(origin, "preprocess", "PP001", f"No se encontró el archivo INCLUDE: {filename}.")
            )
            continue
        included_origins = [origin] * len(included_lines)
        expanded, expanded_origins = _expand_includes(
            included_lines,
            included_origins,
            path.parent,
            include_stack + (path,),
            diagnostics,
        )
        output.extend(expanded)
        output_origins.extend(expanded_origins)
    return output, output_origins


def _collect_macros(
    lines: list[str], origins: list[int], diagnostics: list[Diagnostic]
) -> tuple[list[str], list[int], dict[str, _Macro]]:
    output: list[str] = []
    output_origins: list[int] = []
    macros: dict[str, _Macro] = {}
    index = 0
    while index < len(lines):
        match = _MACRO_HEADER.match(lines[index])
        if not match:
            output.append(lines[index])
            output_origins.append(origins[index])
            index += 1
            continue
        name = match.group(1).casefold()
        params = tuple(arg.strip() for arg in _split_args(match.group(2) or "") if arg.strip())
        header_line = origins[index]
        index += 1
        body: list[str] = []
        while index < len(lines) and not _MACRO_END.match(lines[index]):
            body.append(lines[index])
            index += 1
        if index >= len(lines):
            diagnostics.append(
                Diagnostic(header_line, "preprocess", "PP004", f"La macro {name} no tiene ENDM.")
            )
            break
        if name in macros:
            diagnostics.append(
                Diagnostic(header_line, "preprocess", "PP005", f"Macro duplicada: {name}.")
            )
        else:
            macros[name] = _Macro(params, tuple(body))
        index += 1
    return output, output_origins, macros


def _substitute(body_line: str, macro: _Macro, arguments: list[str]) -> str:
    result = body_line
    for parameter, argument in zip(macro.parameters, arguments):
        pattern = re.compile(rf"(?<![\w]){re.escape(parameter)}(?![\w])", re.IGNORECASE)
        result = pattern.sub(lambda _match: argument, result)
    return result


def _expand_macros(
    lines: list[str],
    origins: list[int],
    macros: dict[str, _Macro],
    diagnostics: list[Diagnostic],
    stack: tuple[str, ...] = (),
) -> tuple[list[str], list[int]]:
    output: list[str] = []
    output_origins: list[int] = []
    for line, origin in zip(lines, origins):
        match = _CALL.match(line)
        name = match.group(2).casefold() if match else ""
        macro = macros.get(name)
        if macro is None:
            output.append(line)
            output_origins.append(origin)
            continue
        if name in stack or len(stack) >= _MAX_MACRO_DEPTH:
            diagnostics.append(
                Diagnostic(origin, "preprocess", "PP003", f"Expansión recursiva de macro: {name}.")
            )
            continue
        arguments = _split_args(match.group(3) or "")
        if len(arguments) != len(macro.parameters):
            diagnostics.append(
                Diagnostic(
                    origin,
                    "preprocess",
                    "PP006",
                    f"La macro {name} espera {len(macro.parameters)} argumento(s); recibió {len(arguments)}.",
                )
            )
            continue
        expanded_lines = [match.group(1) + _substitute(body, macro, arguments) for body in macro.body]
        expanded_origins = [origin] * len(expanded_lines)
        nested, nested_origins = _expand_macros(
            expanded_lines, expanded_origins, macros, diagnostics, stack + (name,)
        )
        output.extend(nested)
        output_origins.extend(nested_origins)
    return output, output_origins


def preprocess(source: str, base_dir: Path | None = None) -> PreprocessResult:
    """Expand INCLUDE and MACRO constructs, retaining source-line mappings."""
    lines = source.splitlines()
    origins = list(range(1, len(lines) + 1))
    diagnostics: list[Diagnostic] = []
    include_dir = Path(base_dir).resolve() if base_dir is not None else None
    included_lines, included_origins = _expand_includes(
        lines, origins, include_dir, (), diagnostics
    )
    code_lines, code_origins, macros = _collect_macros(
        included_lines, included_origins, diagnostics
    )
    expanded_lines, expanded_origins = _expand_macros(
        code_lines, code_origins, macros, diagnostics
    )
    return PreprocessResult("\n".join(expanded_lines), expanded_origins, diagnostics)
