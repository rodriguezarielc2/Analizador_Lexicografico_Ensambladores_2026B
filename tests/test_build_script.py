import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class BuildScriptTests(unittest.TestCase):
    def test_run_script_points_to_main(self):
        script = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertIn("main.py", script)
        self.assertIn("python", script.lower())

    def test_build_script_reports_missing_pyinstaller(self):
        script = (ROOT / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("PyInstaller", script)
        self.assertIn("python -m pip install pyinstaller", script)
        self.assertIn("--onefile", script)

    def test_readme_documents_local_run_and_limits(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("python main.py", readme)
        self.assertIn("emu8086", readme)
        self.assertIn("no guarda", readme)
        self.assertIn("límite", readme)


if __name__ == "__main__":
    unittest.main()
