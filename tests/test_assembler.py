import unittest
import tempfile
from pathlib import Path

from assembler import assemble


class AssemblerTests(unittest.TestCase):
    def test_mov_and_int_produce_expected_machine_rows(self):
        result = assemble("mov ax, 1234h\nint 21h")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(
            [(row.address, row.data.hex(" ").upper()) for row in result.machine_rows],
            [(0, "B8 34 12"), (3, "CD 21")],
        )

    def test_label_and_short_jump_use_relative_address(self):
        result = assemble("start: jmp short done\nnop\ndone: ret")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(
            [(row.address, row.data.hex(" ").upper()) for row in result.machine_rows],
            [(0, "EB 01"), (2, "90"), (3, "C3")],
        )

    def test_valid_data_appears_in_symbol_table(self):
        result = assemble("values db 1, 'AB', 0\nword_value dw 1234h")
        self.assertEqual(result.diagnostics, [])
        symbols = {symbol.name: symbol for symbol in result.symbols}
        self.assertEqual((symbols["values"].address, symbols["values"].width), (0, 1))
        self.assertEqual(symbols["word_value"].address, 4)
        self.assertEqual(
            [(row.address, row.data.hex(" ").upper()) for row in result.machine_rows],
            [(0, "01 41 42 00"), (4, "34 12")],
        )

    def test_code_and_data_rows_show_segment_relative_addresses(self):
        result = assemble(".data\nvalue dw 1\n.code\nstart: mov ax, 1")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual([(row.segment, row.address) for row in result.machine_rows], [("data", 0), ("code", 0)])

    def test_relative_branch_to_another_segment_is_rejected(self):
        result = assemble(".data\nvalue db 1\n.code\njmp value")
        self.assertTrue(any(d.code == "ENC007" for d in result.diagnostics))
        self.assertEqual(result.machine_rows, [])

    def test_far_label_call_and_jump_are_not_encoded_as_near_transfers(self):
        for operation in ("call", "jmp"):
            with self.subTest(operation=operation):
                result = assemble(f"org 100h\n{operation} far target\ntarget: ret")
                self.assertTrue(any(d.code == "ENC002" and d.phase == "encoding" for d in result.diagnostics))
                self.assertEqual(result.machine_rows, [])

    def test_segment_override_on_register_operand_is_rejected(self):
        for source in ("mov ax, es:bx", "mov es:ax, bx"):
            with self.subTest(source=source):
                result = assemble(source)
                self.assertTrue(any(d.code == "ENC001" and d.phase == "encoding" for d in result.diagnostics))
                self.assertEqual(result.machine_rows, [])

    def test_far_pointer_segment_and_offset_must_fit_16_bits(self):
        for pointer in ("10000h:0000h", "0000h:10000h"):
            with self.subTest(pointer=pointer):
                result = assemble(f"call {pointer}")
                self.assertTrue(any(d.code == "ENC004" and d.phase == "encoding" for d in result.diagnostics))
                self.assertEqual(result.machine_rows, [])

        maximum = assemble("call 0ffffh:0ffffh")
        self.assertEqual(maximum.diagnostics, [])
        self.assertEqual(maximum.machine_rows[0].data, bytes.fromhex("9A FF FF FF FF"))

    def test_byte_port_forms_encode_and_invalid_port_register_is_rejected(self):
        result = assemble("in al, dx\nout dx, al")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual([row.data for row in result.machine_rows], [b"\xEC", b"\xEE"])

        invalid = assemble("in al, bx")
        self.assertTrue(invalid.diagnostics)
        self.assertEqual(invalid.machine_rows, [])

    def test_macro_expansion_keeps_the_call_site_line(self):
        source = "load MACRO reg, value\nmov reg, value\nENDM\nload ax, 1"
        result = assemble(source)
        self.assertEqual(result.diagnostics, [])
        self.assertEqual((result.machine_rows[0].line, result.machine_rows[0].data), (4, bytes.fromhex("B8 01 00")))

    def test_include_is_resolved_relative_to_the_source_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "values.inc").write_text("value db 7\n", encoding="utf-8")
            result = assemble('include "values.inc"\nmov al, value', Path(folder))
        self.assertEqual(result.diagnostics, [])
        self.assertEqual([row.data for row in result.machine_rows], [b"\x07", bytes.fromhex("A0 00 00")])

    def test_binf_controls_are_recognized_and_do_not_emit_machine_rows(self):
        result = assemble("#MAKE_BIN#\n#CS=0000#\n#MEM=0100:FFFE,FF#\nnop")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual([row.data for row in result.machine_rows], [b"\x90"])

    def test_unmodeled_pseudo_directive_blocks_machine_rows(self):
        result = assemble("nop\n.exit")
        self.assertTrue(any(d.code == "ENC002" and d.phase == "encoding" for d in result.diagnostics))
        self.assertEqual(result.machine_rows, [])

    def test_uninitialized_data_is_marked_without_claiming_bytes(self):
        result = assemble("reserve db 2 dup(?)")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.machine_rows[0].display_hex, "?? ??")
        self.assertEqual(result.machine_rows[0].known, (False, False))

    def test_lexical_error_keeps_tokens_but_blocks_machine_rows(self):
        result = assemble("mov ax, 0FGh\nnop")
        self.assertTrue(result.tokens)
        self.assertTrue(any(d.phase == "lexical" for d in result.diagnostics))
        self.assertEqual(result.machine_rows, [])

    def test_semantic_error_blocks_machine_rows(self):
        result = assemble("mov ax, al\nint 21h")
        self.assertTrue(any(d.phase == "semantic" for d in result.diagnostics))
        self.assertEqual(result.machine_rows, [])

    def test_unsupported_instruction_does_not_produce_partial_rows(self):
        result = assemble("nop\nmov cs, ax")
        self.assertTrue(any(d.phase == "encoding" and d.code == "ENC001" for d in result.diagnostics))
        self.assertEqual(result.machine_rows, [])


if __name__ == "__main__":
    unittest.main()
