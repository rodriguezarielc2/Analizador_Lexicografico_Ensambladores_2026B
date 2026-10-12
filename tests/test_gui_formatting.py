import unittest

from assembler import assemble
from gui import render_result


class GuiFormattingTests(unittest.TestCase):
    def test_stage_one_rows_show_token_category_and_line(self):
        rows = render_result(assemble("mov ax, 1"))
        self.assertTrue(any(row[0] == "1" and row[1] == "mov" and row[2] == "mnemonic" for row in rows.token_rows))
        self.assertFalse(any(row[1] == "," for row in rows.token_rows))

    def test_stage_two_rows_show_error_line_and_message(self):
        rows = render_result(assemble("mov ax, al"))
        self.assertTrue(any(row[0] == "1" and row[1] == "semantic" and row[3] for row in rows.diagnostic_rows))

    def test_stage_three_rows_show_symbols_addresses_and_hex(self):
        result = assemble("value dw 1234h\n.code\nstart: mov ax, 1")
        rows = render_result(result)
        self.assertTrue(any(row[0] == "value" and row[3] == "0000" for row in rows.symbol_rows))
        self.assertTrue(any(row[2] == "0000" and row[3] == "34 12" for row in rows.machine_rows))
        self.assertTrue(any(row[3] == "B8 01 00" for row in rows.machine_rows))


if __name__ == "__main__":
    unittest.main()
