from c2b.transcription import clean_vtt


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
