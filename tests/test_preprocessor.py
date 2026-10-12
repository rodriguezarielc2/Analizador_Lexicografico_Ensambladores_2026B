import tempfile
import unittest
from pathlib import Path

from preprocessor import preprocess


class PreprocessorTests(unittest.TestCase):
    def test_expands_macro_at_call_site(self):
        source = "load MACRO reg, val\nmov reg, val\nENDM\nload ax, 5\n"
        result = preprocess(source)
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.source, "mov ax, 5")
        self.assertEqual(result.line_map, [4])

    def test_substitutes_macro_parameters_case_insensitively(self):
        source = "put MACRO dst, src\nmov dst, src\nENDM\nput bx, 7"
        result = preprocess(source)
        self.assertEqual(result.source, "mov bx, 7")

    def test_include_resolves_relative_to_main_file(self):
        with tempfile.TemporaryDirectory() as folder:
            include = Path(folder) / "constants.inc"
            include.write_text("value dw 5\n", encoding="utf-8")
            result = preprocess('include "constants.inc"\nmov ax, 1', Path(folder))
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.source, "value dw 5\nmov ax, 1")
        self.assertEqual(result.line_map, [1, 2])

    def test_missing_include_reports_call_line(self):
        with tempfile.TemporaryDirectory() as folder:
            result = preprocess('nop\ninclude "absent.inc"', Path(folder))
        self.assertTrue(any(d.code == "PP001" and d.line == 2 for d in result.diagnostics))

    def test_recursive_macro_reports_error(self):
        source = "again MACRO\nagain\nENDM\nagain"
        result = preprocess(source)
        self.assertTrue(any(d.code == "PP003" and d.line == 4 for d in result.diagnostics))

    def test_all_make_directives_are_recognized_without_creating_files(self):
        directives = "#make_com#\n#make_bin#\n#make_boot#\n#make_exe#"
        with tempfile.TemporaryDirectory() as folder:
            before = set(Path(folder).iterdir())
            result = preprocess(directives, Path(folder))
            after = set(Path(folder).iterdir())
        self.assertEqual(result.diagnostics, [])
        self.assertEqual(result.source, directives)
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
