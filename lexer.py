"""Tokenization for the EMU8086-oriented assembly source viewer."""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence

from models import Diagnostic, LexResult, Token


REGISTERS = frozenset(
    "al ah bl bh cl ch dl dh ax bx cx dx si di bp sp ip cs ds es ss".split()
)

MNEMONICS = frozenset(
    "aaa aad aam aas adc add and call cbw clc cld cli cmc cmp cmps cmpsb cmpsw cwd "
    "daa das dec div hlt idiv imul in inc int into iret ja jae jb jbe jc jcxz je "
    "jg jge jl jle jna jnae jnb jnbe jnc jne jng jnge jnl jnle jno jnp jns jnz jo "
    "jp jpe jpo js jz jmp lahf lds lea les lods lodsb lodsw loop loope loopne loopnz "
    "loopz mov movs movsb movsw mul neg nop not or out pop popf push pushf rcl rcr "
    "rep repe repne repnz repz ret retf retn rol ror sahf sal sar sbb scas scasb lock "
    "scasw shl shr stc std sti stos stosb stosw sub test wait xchg xlat xlatb xor"
    .split()
)

DIRECTIVES = frozenset(
    "assume db dw dd dup end endm endp equ include label macro model org proc segment ends "
    "stack startup exit code data byte word ptr short near far offset type length size"
    .split()
)

PUNCTUATION = frozenset(":[]()+-*/%&|^~=<>")
_WORD = re.compile(r"[A-Za-z_.$@][A-Za-z0-9_.$@]*")


def _numeric_value(lexeme: str) -> int | None:
    lower = lexeme.lower()
    try:
        if lower.startswith("0x"):
            return int(lower[2:], 16)
        if lower.endswith("h"):
            digits = lower[:-1]
            if not digits or not re.fullmatch(r"[0-9a-f]+", digits):
                return None
            return int(digits, 16)
        if lower.endswith("b"):
            digits = lower[:-1]
            if not digits or not re.fullmatch(r"[01]+", digits):
                return None
            return int(digits, 2)
        if lower.endswith("d") and lower[:-1].isdigit():
            return int(lower[:-1], 10)
        if lower.isdigit():
            return int(lower, 10)
    except ValueError:
        return None
    return None


def _string_value(lexeme: str) -> str:
    try:
        value = ast.literal_eval(lexeme)
        return value if isinstance(value, str) else str(value)
    except (SyntaxError, ValueError):
        return lexeme[1:-1]


def _category(word: str) -> str:
    lower = word.lower()
    directive_name = lower.lstrip(".")
    if lower in REGISTERS:
        return "register"
    if lower in MNEMONICS:
        return "mnemonic"
    if directive_name in DIRECTIVES or lower.startswith("#make_"):
        return "directive"
    return "identifier"


def lex(source: str, line_map: Sequence[int] | None = None) -> LexResult:
    """Return tokens and lexical diagnostics, preserving one-based source positions."""
    tokens: list[Token] = []
    diagnostics: list[Diagnostic] = []
    for local_line, text in enumerate(source.splitlines(), start=1):
        source_line = line_map[local_line - 1] if line_map and local_line <= len(line_map) else local_line
        index = 0
        while index < len(text):
            char = text[index]
            if char.isspace():
                index += 1
                continue
            if char == ",":
                tokens.append(Token(source_line, index + 1, char, "separator", char, local_line))
                index += 1
                continue
            if char == ";":
                lexeme = text[index:]
                tokens.append(Token(source_line, index + 1, lexeme, "comment", lexeme[1:].strip(), local_line))
                break
            if char in "'\"":
                quote = char
                end = index + 1
                escaped = False
                while end < len(text):
                    if text[end] == quote and not escaped:
                        break
                    escaped = text[end] == "\\" and not escaped
                    if text[end] != "\\":
                        escaped = False
                    end += 1
                if end >= len(text):
                    diagnostics.append(
                        Diagnostic(source_line, "lexical", "LEX001", "Cadena sin comilla de cierre.")
                    )
                    tokens.append(Token(source_line, index + 1, text[index:], "invalid", None, local_line))
                    break
                lexeme = text[index : end + 1]
                value = _string_value(lexeme)
                category = "character" if quote == "'" and len(value) == 1 else "string"
                tokens.append(Token(source_line, index + 1, lexeme, category, value, local_line))
                index = end + 1
                continue
            if text.startswith("#", index):
                match = re.match(r"#[A-Za-z_][A-Za-z0-9_]*(?:=[^#]*)?#", text[index:])
                if match:
                    lexeme = match.group(0)
                    tokens.append(Token(source_line, index + 1, lexeme, "directive", lexeme.lower(), local_line))
                    index += len(lexeme)
                    continue
            if char.isdigit():
                match = re.match(r"[A-Za-z0-9_]+", text[index:])
                lexeme = match.group(0) if match else char
                value = _numeric_value(lexeme)
                if value is None:
                    diagnostics.append(
                        Diagnostic(
                            source_line,
                            "lexical",
                            "LEX002",
                            f"Constante numérica no válida: {lexeme}.",
                        )
                    )
                    tokens.append(Token(source_line, index + 1, lexeme, "invalid", None, local_line))
                else:
                    tokens.append(Token(source_line, index + 1, lexeme, "number", value, local_line))
                index += len(lexeme)
                continue
            if char == "$":
                tokens.append(Token(source_line, index + 1, char, "location", char, local_line))
                index += 1
                continue
            word_match = _WORD.match(text, index)
            if word_match:
                lexeme = word_match.group(0)
                tokens.append(Token(source_line, index + 1, lexeme, _category(lexeme), lexeme, local_line))
                index = word_match.end()
                continue
            if char == "?":
                tokens.append(Token(source_line, index + 1, char, "uninitialized", None, local_line))
                index += 1
                continue
            if char in PUNCTUATION:
                tokens.append(Token(source_line, index + 1, char, "punctuation", char, local_line))
                index += 1
                continue
            diagnostics.append(
                Diagnostic(source_line, "lexical", "LEX003", f"Carácter no reconocido: {char!r}.")
            )
            tokens.append(Token(source_line, index + 1, char, "invalid", None, local_line))
            index += 1
    return LexResult(tokens, diagnostics)
