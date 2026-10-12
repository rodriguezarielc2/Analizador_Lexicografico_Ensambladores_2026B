"""8086 opcode groups and instruction sizing used by the two-pass layout."""

from __future__ import annotations

import re

from layout import Symbol
from parser import Statement


ARITHMETIC = {
    "add": {"rm_reg": 0x00, "immediate_group": 0, "accumulator": 0x04},
    "or": {"rm_reg": 0x08, "immediate_group": 1, "accumulator": 0x0C},
    "adc": {"rm_reg": 0x10, "immediate_group": 2, "accumulator": 0x14},
    "sbb": {"rm_reg": 0x18, "immediate_group": 3, "accumulator": 0x1C},
    "and": {"rm_reg": 0x20, "immediate_group": 4, "accumulator": 0x24},
    "sub": {"rm_reg": 0x28, "immediate_group": 5, "accumulator": 0x2C},
    "xor": {"rm_reg": 0x30, "immediate_group": 6, "accumulator": 0x34},
    "cmp": {"rm_reg": 0x38, "immediate_group": 7, "accumulator": 0x3C},
}

CONDITIONAL_JUMPS = {
    "jo": 0x70, "jno": 0x71,
    "jb": 0x72, "jc": 0x72, "jnae": 0x72,
    "jae": 0x73, "jnb": 0x73, "jnc": 0x73,
    "je": 0x74, "jz": 0x74,
    "jne": 0x75, "jnz": 0x75,
    "jbe": 0x76, "jna": 0x76,
    "ja": 0x77, "jnbe": 0x77,
    "js": 0x78, "jns": 0x79,
    "jp": 0x7A, "jpe": 0x7A,
    "jnp": 0x7B, "jpo": 0x7B,
    "jl": 0x7C, "jnge": 0x7C,
    "jge": 0x7D, "jnl": 0x7D,
    "jle": 0x7E, "jng": 0x7E,
    "jg": 0x7F, "jnle": 0x7F,
}

LOOP_JUMPS = {"loopne": 0xE0, "loopnz": 0xE0, "loope": 0xE1, "loopz": 0xE1, "loop": 0xE2, "jcxz": 0xE3}

_OPERAND_IDENTIFIER = re.compile(r"[A-Za-z_.$?@][A-Za-z0-9_.$?@]*")
_NUMBER_LITERAL = re.compile(r"(?i)(?<![A-Za-z0-9_])(?:0x[0-9a-f]+|0b[01]+|[0-9][0-9a-f]*h|[01]+b|[0-9]+)(?![A-Za-z0-9_])")
_QUOTED_LITERAL = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
_REGISTERS = frozenset("al ah bl bh cl ch dl dh ax bx cx dx si di bp sp cs ds es ss".split())
_KEYWORDS = frozenset("byte word dword ptr offset short near far dup".split())


def instruction_size(statement: Statement) -> int:
    """Estimate exact byte length without needing symbols from the second pass."""
    from encoding import encode_statement

    symbols: dict[str, Symbol] = {}
    is_branch = statement.operation.lower() in CONDITIONAL_JUMPS or statement.operation.lower() in LOOP_JUMPS or statement.operation.lower() in {"jmp", "call"}
    for operand in statement.operands:
        cleaned = _QUOTED_LITERAL.sub(" ", _NUMBER_LITERAL.sub(" ", operand))
        for match in _OPERAND_IDENTIFIER.finditer(cleaned):
            name = match.group(0)
            key = name.casefold()
            if key in _REGISTERS or key in _KEYWORDS or key in symbols:
                continue
            symbols[key] = Symbol(name, "label" if is_branch else "data", None, 0, None)
    return len(encode_statement(statement, 0, symbols))
