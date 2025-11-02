import unittest
from summarizers.prompt_builder import build_summarization_prompt


class TestPromptBuilder(unittest.TestCase):
    def test_build_prompt(self):
        # Given
        articles = [{"title": "Breaking News", "content": "Details about the event."}]
        prompt = build_summarization_prompt(articles)

        # Then
        self.assertIn("Breaking News", prompt)
        self.assertIn("Details about the event.", prompt)


if __name__ == "__main__":
    unittest.main()
