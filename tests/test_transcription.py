from unittest.mock import MagicMock, patch

from c2b.transcription import clean_vtt, extract_youtube_id, fetch_youtube_transcript


def test_clean_vtt_basic():
    vtt = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
Olá pessoal, bem-vindos ao curso de arquitetura.

2
00:00:04.000 --> 00:00:07.000
Hoje vamos aprender sobre padrões de microsserviços.
"""
    result = clean_vtt(vtt)
    assert "Olá pessoal, bem-vindos ao curso de arquitetura." in result
    assert "Hoje vamos aprender sobre padrões de microsserviços." in result
    assert "00:00:01.000" not in result
    assert "WEBVTT" not in result


def test_clean_vtt_deduplicate_rolling_captions():
    vtt = """WEBVTT

1
00:01.000 --> 00:02.000
Engenharia de software

2
00:02.000 --> 00:03.000
Engenharia de software
moderna.
"""
    result = clean_vtt(vtt)
    # Deduplicates consecutive identical lines
    assert "Engenharia de software moderna." in result


def test_clean_vtt_empty():
    assert clean_vtt("") == ""
    assert clean_vtt("   ") == ""


def test_extract_youtube_id():
    assert extract_youtube_id("https://www.youtube.com/watch?v=4szRHy_CT7s") == "4szRHy_CT7s"
    assert extract_youtube_id("https://www.youtube.com/embed/4szRHy_CT7s?si=uPBP3EzbdQ0QetFi") == "4szRHy_CT7s"
    assert extract_youtube_id("https://youtu.be/4szRHy_CT7s") == "4szRHy_CT7s"
    assert extract_youtube_id("4szRHy_CT7s") == "4szRHy_CT7s"
    assert extract_youtube_id("https://example.com/video/123") is None
    assert extract_youtube_id("") is None
    assert extract_youtube_id(None) is None


def test_fetch_youtube_transcript_success():
    mock_data = [
        {"text": "Hello everyone.", "start": 0.0, "duration": 2.0},
        {"text": "Welcome to AI Fluency.", "start": 2.0, "duration": 3.0},
    ]

    mock_api = MagicMock()
    mock_api.get_transcript.return_value = mock_data

    with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api)}):
        result = fetch_youtube_transcript("https://www.youtube.com/watch?v=4szRHy_CT7s")
        assert "Hello everyone." in result
        assert "Welcome to AI Fluency." in result
        mock_api.get_transcript.assert_called_once_with("4szRHy_CT7s", languages=["pt", "pt-BR", "en"])


def test_fetch_youtube_transcript_fallback():
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [{"text": "Fallback transcript text.", "start": 0.0}]

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    mock_api = MagicMock()
    mock_api.get_transcript.side_effect = Exception("Direct fetch failed")
    mock_api.list_transcripts.return_value = mock_transcript_list

    with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api)}):
        result = fetch_youtube_transcript("4szRHy_CT7s")
        assert "Fallback transcript text." in result


def test_fetch_youtube_transcript_not_found():
    mock_api = MagicMock()
    mock_api.get_transcript.side_effect = Exception("Transcripts disabled")
    mock_api.list_transcripts.side_effect = Exception("No transcripts")

    with patch.dict("sys.modules", {"youtube_transcript_api": MagicMock(YouTubeTranscriptApi=mock_api)}):
        result = fetch_youtube_transcript("4szRHy_CT7s")
        assert result == ""


def test_fetch_youtube_transcript_no_id():
    assert fetch_youtube_transcript("") == ""
    assert fetch_youtube_transcript("https://not-youtube.com/abc") == ""
