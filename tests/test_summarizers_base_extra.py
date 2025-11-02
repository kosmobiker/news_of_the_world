import unittest
from summarizers.base import NewsSummarizer


class ConcreteSummarizer(NewsSummarizer):
    @property
    def model_name(self) -> str:
        return "concrete"

    def summarize_articles(self, articles):
        return ";".join(a.get("headline", "") for a in articles)


class TestSummarizerBaseExtra(unittest.TestCase):
    def test_concrete_summarizer(self):
        s = ConcreteSummarizer()
        out = s.summarize_articles([{"headline": "H1"}, {"headline": "H2"}])
        self.assertEqual(out, "H1;H2")
        self.assertEqual(s.model_name, "concrete")

    def test_abstract_methods_callable_and_instantiation(self):
        result = None
        result = None
        NewsSummarizer.summarize_articles(None, [])

        prop = NewsSummarizer.model_name
        prop.fget(None)

        with self.assertRaises(TypeError):
            NewsSummarizer()
