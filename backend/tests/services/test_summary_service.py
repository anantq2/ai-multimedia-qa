"""tests/services/test_summary_service.py — Unit tests for summary_service.py."""
import pytest
from unittest.mock import MagicMock, patch


class TestSummarize:
    def test_summarize_returns_string(self):
        from app.services.summary_service import summarize

        mock_result = MagicMock()
        mock_result.content = "• Key point one.\n• Key point two."
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_result

        with patch("app.services.summary_service.SUMMARY_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            result = summarize("Some document content here.")

        assert result == "• Key point one.\n• Key point two."

    def test_summarize_truncates_to_12000_chars(self):
        from app.services.summary_service import summarize

        captured = {}
        mock_result = MagicMock()
        mock_result.content = "Summary"
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = lambda args: (captured.update(args) or mock_result)

        long_text = "A" * 20_000

        with patch("app.services.summary_service.SUMMARY_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            summarize(long_text)

        assert len(captured["text"]) == 12_000

    def test_summarize_short_text_not_truncated(self):
        from app.services.summary_service import summarize

        captured = {}
        mock_result = MagicMock()
        mock_result.content = "A summary."
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = lambda args: (captured.update(args) or mock_result)

        short_text = "Just a few words."

        with patch("app.services.summary_service.SUMMARY_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            summarize(short_text)

        assert captured["text"] == short_text

    def test_summarize_calls_llm_with_text(self):
        from app.services.summary_service import summarize

        mock_result = MagicMock()
        mock_result.content = "result"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_result

        with patch("app.services.summary_service.SUMMARY_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            summarize("My input")

        mock_chain.invoke.assert_called_once()
