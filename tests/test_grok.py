import unittest
from unittest.mock import patch, MagicMock
from summarizers.grok import GrokSummarizer
import logging


# Silence noisy logger from summarizers.grok during tests
logging.getLogger("summarizers.grok").setLevel(logging.CRITICAL)


class TestGrok(unittest.TestCase):
    @patch("summarizers.grok.Client")
    def test_process_data(self, mock_client):
        # Given
        mock_chat = MagicMock()
        mock_chat.parse.return_value = (None, MagicMock(dict=lambda: "Processed Data"))
        mock_client.return_value.chat.create.return_value = mock_chat

        grok = GrokSummarizer(db=MagicMock())
        input_data = [{"title": "Sample Article", "content": "Sample Content"}]

        # When
        result = grok.summarize_articles(input_data)

        # Then
        self.assertEqual(result, "Processed Data")
        mock_client.return_value.chat.create.assert_called_once()

    @patch("summarizers.grok.Client")
    def test_empty_input(self, mock_client):
        # Given
        mock_chat = MagicMock()
        mock_chat.parse.side_effect = ValueError("No input provided")
        mock_client.return_value.chat.create.return_value = mock_chat

        grok = GrokSummarizer(db=MagicMock())
        input_data = []

        # When
        result = grok.summarize_articles(input_data)

        # Then
        self.assertEqual(
            result,
            {
                "text_summary": "",
                "detailed_summary": "Error processing response",
                "main_events": {},
                "key_themes": {},
                "impacted_regions": {},
                "timeline": {},
                "error": "Failed to get summary from Grok API: No input provided",
            },
        )
        mock_client.return_value.chat.create.assert_called_once()

    @patch("summarizers.grok.Client")
    def test_invalid_input_type(self, mock_client):
        # Given
        grok = GrokSummarizer(db=MagicMock())
        input_data = 12345  # Invalid input type

        # When
        with self.assertRaises(TypeError):
            grok.summarize_articles(input_data)

        # Then
        mock_client.return_value.chat.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
