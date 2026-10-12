import unittest

from lexer import lex


class LexerTests(unittest.TestCase):
    def test_classifies_registers_mnemonics_directives_and_numbers(self):
        result = lex("mov ax, 025H\nvalue db 10")
        self.assertEqual(result.diagnostics, [])
        categories = [(token.lexeme, token.category) for token in result.tokens]
        self.assertIn(("mov", "mnemonic"), categories)
        self.assertIn(("ax", "register"), categories)
        self.assertIn(("025H", "number"), categories)
        self.assertIn(("db", "directive"), categories)
        self.assertIn(("10", "number"), categories)
        self.assertIn((",", "separator"), categories)

    def test_classifies_all_data_width_directives(self):
        result = lex("items db 1\nwords dw 2\nvalues dd 3")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(
            [token.category for token in result.tokens if token.lexeme in {"db", "dw", "dd"}],
            ["directive"] * 3,
        )

    def test_recognizes_emu8086_binf_control_directives(self):
        result = lex("#CS=0000#\n#MEM=0100:FFFE,FF#")
        self.assertEqual(result.diagnostics, [])
        self.assertEqual([token.category for token in result.tokens], ["directive", "directive"])

    def test_accepts_decimal_hex_binary_character_and_string_literals(self):
        result = lex("db 10, 0FFh, 101b, 'A', \"text\"")
        self.assertEqual(result.diagnostics, [])
        numbers = [token.value for token in result.tokens if token.category == "number"]
        self.assertEqual(numbers, [10, 255, 5])
        self.assertIn(("'A'", "character"), [(t.lexeme, t.category) for t in result.tokens])
        self.assertIn(('"text"', "string"), [(t.lexeme, t.category) for t in result.tokens])

    def test_preserves_line_and_column(self):
        result = lex("\n  mov ax, 1")
        mov = next(token for token in result.tokens if token.lexeme == "mov")
        self.assertEqual((mov.line, mov.column), (2, 3))

    def test_line_map_keeps_original_and_local_lines(self):
        result = lex("mov ax, 1\nmov bx, 2", line_map=[10, 10])
        first, second = [token for token in result.tokens if token.category == "mnemonic"]
        self.assertEqual((first.line, first.local_line), (10, 1))
        self.assertEqual((second.line, second.local_line), (10, 2))

    def test_location_counter_is_not_an_identifier(self):
        result = lex("db $")
        location = next(token for token in result.tokens if token.lexeme == "$")
        self.assertEqual(location.category, "location")

    def test_semicolon_comment_is_classified_as_one_comment_token(self):
        result = lex("mov ax, 1 ; explanatory comment")
        comments = [token for token in result.tokens if token.category == "comment"]
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].lexeme, "; explanatory comment")
        self.assertEqual(comments[0].line, 1)

    def test_malformed_number_returns_lexical_diagnostic(self):
        result = lex("mov ax, 0FGh")
        self.assertTrue(any(d.phase == "lexical" and d.line == 1 for d in result.diagnostics))


if __name__ == "__main__":
    unittest.main()
