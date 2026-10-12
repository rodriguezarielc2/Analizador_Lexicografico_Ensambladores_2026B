import json
import unittest
from pathlib import Path

from encoding import EncodingError, encode_statement
from instruction_set import instruction_size
from layout import Symbol
from lexer import lex
from parser import parse


FIXTURE = Path(__file__).parent / "fixtures" / "emu8086_supported_forms.json"


def statement_for(source):
    result = parse(lex(source).tokens)
    if result.diagnostics:
        raise AssertionError(result.diagnostics)
    if len(result.statements) != 1:
        raise AssertionError(f"expected one statement, got {result.statements!r}")
    return result.statements[0]


def symbols_from_case(case):
    return {
        item["name"].casefold(): Symbol(
            item["name"],
            item["kind"],
            item.get("value"),
            item.get("address"),
            item.get("width"),
        )
        for item in case.get("symbols", [])
    }


class EncodingTests(unittest.TestCase):
    def test_mov_register_immediate_is_little_endian(self):
        encoded = encode_statement(statement_for("mov ax, 1234h"), 0, {})
        self.assertEqual(encoded, bytes.fromhex("B8 34 12"))

    def test_mov_register_register_uses_modrm(self):
        encoded = encode_statement(statement_for("mov ax, bx"), 0, {})
        self.assertEqual(encoded, bytes.fromhex("8B C3"))

    def test_arithmetic_and_logic_families_encode(self):
        expected = {
            "add": "03 C3", "adc": "13 C3", "sub": "2B C3", "sbb": "1B C3",
            "and": "23 C3", "or": "0B C3", "xor": "33 C3", "cmp": "3B C3",
            "test": "85 D8",
        }
        for mnemonic, hex_bytes in expected.items():
            with self.subTest(mnemonic=mnemonic):
                left, right = ("ax", "bx") if mnemonic != "test" else ("ax", "bx")
                self.assertEqual(
                    encode_statement(statement_for(f"{mnemonic} {left}, {right}"), 0, {}),
                    bytes.fromhex(hex_bytes),
                )

    def test_stack_and_interrupt_instructions_encode(self):
        self.assertEqual(encode_statement(statement_for("push ax"), 0, {}), b"\x50")
        self.assertEqual(encode_statement(statement_for("pop bx"), 0, {}), b"\x5b")
        self.assertEqual(encode_statement(statement_for("int 21h"), 0, {}), bytes.fromhex("CD 21"))

    def test_conditional_and_unconditional_branch_displacements(self):
        symbols = {"target": Symbol("target", "label", None, 4)}
        self.assertEqual(encode_statement(statement_for("je target"), 0, symbols), bytes.fromhex("74 02"))
        self.assertEqual(encode_statement(statement_for("jmp short target"), 0, symbols), bytes.fromhex("EB 02"))

    def test_every_supported_form_has_a_golden_case(self):
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
        self.assertGreaterEqual(len(cases), 25)
        for case in cases:
            with self.subTest(source=case["source"]):
                result = parse(lex(case["source"]).tokens)
                self.assertEqual(result.diagnostics, [])
                self.assertEqual(len(result.statements), 1)
                encoded = encode_statement(result.statements[0], case["address"], symbols_from_case(case))
                self.assertEqual(encoded, bytes.fromhex(case["hex"]))
                self.assertEqual(instruction_size(result.statements[0]), len(encoded))

    def test_rejects_invalid_register_memory_pair(self):
        with self.assertRaises(EncodingError) as caught:
            encode_statement(statement_for("mov cs, ax"), 0, {})
        self.assertEqual(caught.exception.code, "ENC001")

    def test_rejects_out_of_range_short_branch(self):
        symbols = {"faraway": Symbol("faraway", "label", None, 200)}
        with self.assertRaises(EncodingError) as caught:
            encode_statement(statement_for("jmp short faraway"), 0, symbols)
        self.assertEqual(caught.exception.code, "ENC003")


if __name__ == "__main__":
    unittest.main()
