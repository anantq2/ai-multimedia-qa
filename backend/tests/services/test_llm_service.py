"""tests/services/test_llm_service.py — Unit tests for llm_service.py."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


CHUNKS = [
    {"text": "The sky is blue due to Rayleigh scattering."},
    {"text": "The ocean appears blue because it reflects the sky."},
]


class TestAnswer:
    def test_answer_returns_string(self):
        from app.services.llm_service import answer

        mock_result = MagicMock()
        mock_result.content = "The sky is blue."

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_result

        with patch("app.services.llm_service.QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            result = answer("Why is the sky blue?", CHUNKS)

        assert result == "The sky is blue."

    def test_answer_joins_chunks_with_separator(self):
        from app.services.llm_service import answer

        captured = {}
        mock_result = MagicMock()
        mock_result.content = "Combined answer"
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = lambda args: (captured.update(args) or mock_result)

        with patch("app.services.llm_service.QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            answer("question?", CHUNKS)

        context = captured.get("context", "")
        assert "---" in context
        assert "Rayleigh scattering" in context
        assert "reflects the sky" in context

    def test_answer_includes_question(self):
        from app.services.llm_service import answer

        captured = {}
        mock_result = MagicMock()
        mock_result.content = "Answer"
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = lambda args: (captured.update(args) or mock_result)

        with patch("app.services.llm_service.QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            answer("Why is the sky blue?", CHUNKS)

        assert captured["question"] == "Why is the sky blue?"


class TestAnswerStream:
    @pytest.mark.asyncio
    async def test_answer_stream_yields_content(self):
        from app.services.llm_service import answer_stream

        async def fake_astream(*args, **kwargs):
            yield MagicMock(content="Hello ")
            yield MagicMock(content="world!")

        mock_chain = MagicMock()
        mock_chain.astream = fake_astream

        with patch("app.services.llm_service.QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            tokens = []
            async for token in answer_stream("question?", CHUNKS):
                tokens.append(token)

        assert tokens == ["Hello ", "world!"]

    @pytest.mark.asyncio
    async def test_answer_stream_skips_empty_content(self):
        from app.services.llm_service import answer_stream

        async def fake_astream(*args, **kwargs):
            yield MagicMock(content="Real token")
            yield MagicMock(content="")           # should be skipped
            yield MagicMock(content=None)         # should be skipped (hasattr check)

        mock_chunk_none = MagicMock(spec=[])      # no 'content' attribute
        mk = MagicMock()
        mk.content = None

        async def fake_astream2(*args, **kwargs):
            yield MagicMock(content="Token1")
            m = MagicMock()
            del m.content                         # no content attribute
            yield m

        mock_chain = MagicMock()
        mock_chain.astream = fake_astream

        with patch("app.services.llm_service.QA_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            tokens = []
            async for token in answer_stream("q?", CHUNKS):
                tokens.append(token)

        # Empty string content should be filtered
        assert "" not in tokens
        assert "Real token" in tokens
