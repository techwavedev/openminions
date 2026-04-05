import tempfile
import unittest
from pathlib import Path
import sys

# Add bin/ to path so we can import security_gate
sys.path.append(str(Path(__file__).resolve().parent.parent / "bin"))
from security_gate import scan_file_for_secrets, check_forbidden_files

class TestSecurityGate(unittest.TestCase):
    def test_secret_patterns(self):
        # Setup a dummy file that contains some mock secrets
        with tempfile.TemporaryDirectory() as td:
            dummy_file = Path(td) / "api.js"
            dummy_file.write_text("const API_KEY = 'sk-12345678901234567890abcdefABCDEF';\nconst aws_secret_access_key = '0123456789012345678901234567890123456789';", encoding="utf-8")
            
            findings = scan_file_for_secrets(dummy_file)
            
            self.assertTrue(any(f[1] == "OpenAI API key" for f in findings))
            self.assertTrue(any(f[1] == "AWS secret key" for f in findings))

    def test_forbidden_files(self):
        tracked = [".env", "src/index.js", ".openminions/state.json"]
        violations = check_forbidden_files(tracked)
        
        self.assertIn(".env", violations)
        self.assertIn(".openminions/state.json", violations)
        self.assertNotIn("src/index.js", violations)

if __name__ == '__main__':
    unittest.main()
