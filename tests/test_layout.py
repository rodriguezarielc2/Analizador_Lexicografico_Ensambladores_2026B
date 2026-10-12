import unittest

from lexer import lex
from layout import evaluate_expression, layout
from parser import parse


def parse_source(source):
    return parse(lex(source).tokens)


class LayoutTests(unittest.TestCase):
    def test_assigns_sequential_addresses(self):
        program = parse_source("start: nop\nmov ax, 1\nafter: ret")
        result = layout(program, lambda statement: {"nop": 1, "mov": 3, "ret": 1}[statement.operation], origin=0x100)

        self.assertEqual(result.statement_addresses, [0x100, 0x101, 0x104])
        self.assertEqual(result.statement_sizes, [1, 3, 1])
        self.assertEqual(result.symbols["start"].address, 0x100)
        self.assertEqual(result.symbols["after"].address, 0x104)
        self.assertEqual(result.diagnostics, [])

    def test_each_supported_directive_has_layout_behavior(self):
        program = parse_source(
            "org 100h\n"
            "buf db 'AB', 0\n"
            "copies db 3 dup(0)\n"
            "pairs db 2 dup(1, 2)\n"
            "word_value dw 1234h\n"
            "wide dd ?\n"
            "here equ $\n"
            "limit equ 20\n"
            ".model small\n.stack 100h\n.data\n.code\n"
            "proc1 proc\nproc1 endp\nend"
        )
        result = layout(program, lambda statement: self.fail(f"unexpected size callback: {statement}"))

        self.assertEqual(result.statement_addresses[1:6], [0x100, 0x103, 0x106, 0x10A, 0x10C])
        self.assertEqual(result.statement_sizes[1:6], [3, 3, 4, 2, 4])
        self.assertEqual(result.symbols["buf"].kind, "data")
        self.assertEqual(result.symbols["word_value"].address, 0x10A)
        self.assertEqual(result.symbols["limit"].value, 20)
        self.assertEqual(result.symbols["here"].value, 0x110)
        self.assertEqual(result.symbols["proc1"].kind, "procedure")
        self.assertEqual(result.diagnostics, [])

    def test_resolves_forward_label_in_first_pass(self):
        program = parse_source("jmp target\ntarget: nop")
        result = layout(program, lambda statement: 2 if statement.operation == "jmp" else 1)

        self.assertEqual(result.symbols["target"].address, 2)
        self.assertEqual(result.diagnostics, [])

    def test_uses_instruction_size_callback_for_branch_addresses(self):
        program = parse_source("jz there\nnop\nthere: ret")
        sizes = {"jz": 2, "nop": 1, "ret": 1}
        result = layout(program, lambda statement: sizes[statement.operation])

        self.assertEqual(result.statement_addresses, [0, 2, 3])
        self.assertEqual(result.statement_sizes, [2, 1, 1])
        self.assertEqual(result.symbols["there"].address, 3)

    def test_rejects_undefined_symbol(self):
        result = layout(parse_source("jmp missing"), lambda statement: 2)

        self.assertTrue(any(d.code == "LAYOUT001" and d.line == 1 for d in result.diagnostics))

    def test_rejects_duplicate_symbol(self):
        result = layout(parse_source("item db 1\nitem dw 2"), lambda statement: 0)

        self.assertTrue(any(d.code == "LAYOUT002" and d.line == 2 for d in result.diagnostics))

    def test_detects_address_overflow(self):
        program = parse_source("org 0ffffh\nvalue dw 1")
        result = layout(program, lambda statement: 0)

        self.assertTrue(any(d.code == "LAYOUT003" for d in result.diagnostics))

    def test_data_symbol_expression_uses_its_address_and_width(self):
        result = layout(parse_source("org 100h\nvalue dw 1"), lambda statement: 0)
        symbol = result.symbols["value"]
        self.assertEqual((symbol.address, symbol.width), (0x100, 2))
        self.assertEqual(evaluate_expression("value", result.symbols), 0x100)

    def test_data_and_code_sections_have_independent_offsets(self):
        program = parse_source(".data\nvalue db 1\n.code\nstart: nop")
        result = layout(program, lambda statement: 1)
        self.assertEqual(result.statement_addresses, [0, 0, 0, 0])
        self.assertEqual(result.symbols["value"].segment, "data")
        self.assertEqual(result.symbols["start"].segment, "code")

    def test_named_segments_get_independent_offsets(self):
        program = parse_source("DATA SEGMENT\nvalue db 1\nDATA ENDS\nCODE SEGMENT\nstart: nop\nCODE ENDS")
        result = layout(program, lambda statement: 1)
        self.assertEqual(result.statement_addresses[1:5], [0, 1, 0, 0])
        self.assertEqual(result.symbols["value"].segment, "data")
        self.assertEqual(result.symbols["start"].segment, "code")


if __name__ == "__main__":
    unittest.main()
