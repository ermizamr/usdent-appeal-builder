import unittest

from usdent.rules.sample_context import build_sample_context
from usdent.rules.validation import validate_context


class ValidationTests(unittest.TestCase):
    def test_validate_context(self) -> None:
        context = build_sample_context()
        issues = validate_context(context)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
