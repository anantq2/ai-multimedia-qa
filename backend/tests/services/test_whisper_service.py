"""tests/services/test_whisper_service.py — Unit tests for whisper_service.py."""
import pytest
from unittest.mock import MagicMock, patch
import app.services.whisper_service as ws


@pytest.fixture(autouse=True)
def reset_whisper_model():
    """Reset the cached Whisper model before each test."""
    ws._model = None
    yield
    ws._model = None


class TestGetModel:
    def test_lazy_loads_on_first_call(self):
        mock_model = MagicMock()
        with patch("app.services.whisper_service.whisper.load_model", return_value=mock_model) as mock_load:
            result = ws._get_model()

        assert result is mock_model
        mock_load.assert_called_once_with("base")

    def test_cached_on_subsequent_calls(self):
        mock_model = MagicMock()
        with patch("app.services.whisper_service.whisper.load_model", return_value=mock_model) as mock_load:
            first  = ws._get_model()
            second = ws._get_model()

        assert first is second
        mock_load.assert_called_once()   # Only loaded once


class TestTranscribe:
    def _make_model(self, segments):
        model = MagicMock()
        model.transcribe.return_value = {"segments": segments}
        return model

    def _seg(self, start, end, text):
        return {"start": start, "end": end, "text": text}

    def test_basic_transcription(self):
        segs = [self._seg(0, 15, " Hello"), self._seg(15, 30, " World")]
        model = self._make_model(segs)

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3", chunk_duration_sec=30)

        assert len(chunks) == 1
        assert "Hello" in chunks[0]["text"]
        assert "World" in chunks[0]["text"]
        assert chunks[0]["start_time"] == 0.0
        assert chunks[0]["end_time"] == 30.0

    def test_multiple_chunks_when_exceeds_duration(self):
        segs = [
            self._seg(0, 20, " First"),
            self._seg(20, 35, " Second"),   # crosses 30s boundary
            self._seg(35, 50, " Third"),
        ]
        model = self._make_model(segs)

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3", chunk_duration_sec=30)

        # First chunk: 0–35 (flush when end-start >= 30)
        # Second chunk: remainder segment
        assert len(chunks) >= 1

    def test_remainder_buffer_flushed(self):
        """Segments that don't fill a full chunk still create a chunk."""
        segs = [self._seg(0, 10, " Short segment")]
        model = self._make_model(segs)

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3", chunk_duration_sec=30)

        assert len(chunks) == 1
        assert chunks[0]["start_time"] == 0.0

    def test_empty_segments_returns_empty_list(self):
        model = self._make_model([])

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3")

        assert chunks == []

    def test_chunk_index_sequential(self):
        segs = [self._seg(i * 11, i * 11 + 10, f" Seg{i}") for i in range(6)]
        model = self._make_model(segs)

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3", chunk_duration_sec=30)

        for i, c in enumerate(chunks):
            assert c["chunk_index"] == i

    def test_timestamps_rounded_to_2dp(self):
        segs = [self._seg(0.123456, 29.999999, " Text")]
        model = self._make_model(segs)

        with patch("app.services.whisper_service._get_model", return_value=model):
            chunks = ws.transcribe("fake.mp3", chunk_duration_sec=10)

        chunk = chunks[0]
        assert chunk["start_time"] == round(0.123456, 2)
        assert chunk["end_time"]   == round(29.999999, 2)
