import unittest

from lexer import lex
from parser import parse


class ParserTests(unittest.TestCase):
    def parse_source(self, source):
        lexed = lex(source)
        return parse(lexed.tokens)

    def test_parses_label_instruction_and_operands(self):
        result = self.parse_source("start: mov ax, 1\ndone: int 21h")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(
            [(s.label, s.operation, s.operands) for s in result.statements],
            [("start", "mov", ["ax", "1"]), ("done", "int", ["21h"])],
        )

    def test_parses_uncolonized_data_symbol(self):
        result = self.parse_source("value db 5, 2")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual((result.statements[0].label, result.statements[0].operation), ("value", "db"))
        self.assertEqual(result.statements[0].operands, ["5", "2"])

    def test_keeps_commas_inside_dup_initializer(self):
        result = self.parse_source("values db 2 dup(1, 2)")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.statements[0].operands, ["2 dup(1, 2)"])

    def test_procedure_end_name_is_not_a_duplicate_definition(self):
        result = self.parse_source("work proc\nwork endp")
        self.assertFalse(any(d.code == "SEM001" for d in result.diagnostics))

    def test_accepts_rep_prefix_on_string_instruction(self):
        result = self.parse_source("rep movsb")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual((result.statements[0].operation, result.statements[0].operands), ("rep movsb", []))

    def test_accepts_ret_with_stack_adjustment(self):
        result = self.parse_source("ret 4")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.statements[0].operands, ["4"])

    def test_accepts_lock_prefix_on_instruction(self):
        result = self.parse_source("lock add byte ptr [bx], 1")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.statements[0].operation, "lock add")

    def test_accepts_emu8086_binf_control_directives(self):
        result = self.parse_source("#CS=0000#\n#MEM=0100:FFFE,FF#")
        self.assertEqual(result.diagnostics, [])

    def test_accepts_common_dotted_model_and_section_directives(self):
        result = self.parse_source(".model small\n.stack 100h\n.data\n.code\n.exit")
        self.assertEqual(result.diagnostics, [])

    def test_rejects_missing_operand(self):
        result = self.parse_source("mov ax,")
        self.assertTrue(any(d.phase == "syntax" and d.line == 1 for d in result.diagnostics))

    def test_rejects_unknown_mnemonic(self):
        result = self.parse_source("bogus ax")
        self.assertTrue(any(d.code == "PARSE001" and d.line == 1 for d in result.diagnostics))

    def test_unknown_mnemonic_reports_single_diagnostic(self):
        result = self.parse_source("bogus ax")
        self.assertEqual(len([d for d in result.diagnostics if d.code == "PARSE001"]), 1)

    def test_rejects_duplicate_label(self):
        result = self.parse_source("again: nop\nagain: ret")
        self.assertTrue(any(d.code == "SEM001" and d.line == 2 for d in result.diagnostics))

    def test_rejects_operand_width_mismatch(self):
        result = self.parse_source("mov ax, al")
        self.assertTrue(any(d.code == "SEM002" and d.phase == "semantic" for d in result.diagnostics))


if __name__ == "__main__":
    unittest.main()
